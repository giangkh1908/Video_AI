"""Job orchestrator: create/get/list/retry, idempotency, dedup, dispatch."""
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

from fastapi import BackgroundTasks

from app.core.config import settings
from app.core.models import ConceptId, Job, JobStatus
from app.core.state_machine import can_transition
from app.store.local_artifacts import LocalArtifactStore
from app.store.memory_repo import InMemoryJobRepo

MAX_ATTEMPT = 3
DEDUP_WINDOW_SEC = 60
DEFAULT_VOICE = "en-US-AriaNeural"
TERMINAL = {JobStatus.COMPLETED, JobStatus.FAILED}

repo = InMemoryJobRepo()
artifact_store = LocalArtifactStore()
_executor = ThreadPoolExecutor(
    max_workers=settings.max_workers, thread_name_prefix="growtrics-pipe"
)
RENDER_SEMAPHORE = threading.Semaphore(2)
_voices: dict[str, str] = {}


class JobNotFound(Exception):
    def __init__(self, job_id: str) -> None:
        super().__init__(job_id)
        self.job_id = job_id


class UnsupportedConcept(Exception):
    def __init__(self, concept: str) -> None:
        super().__init__(concept)
        self.concept = concept
        self.hint = [c.value for c in ConceptId]


class RetryNotAllowed(Exception):
    def __init__(self, job_id: str, reason: str) -> None:
        super().__init__(reason)
        self.job_id = job_id
        self.reason = reason


def _submit(job_id: str) -> None:
    from app.services.pipeline import run_pipeline

    _executor.submit(run_pipeline, job_id)


def voice_for(job_id: str) -> str:
    return _voices.get(job_id, DEFAULT_VOICE)


def create_job(
    concept: str,
    voice: str | None = None,
    idempotency_key: str | None = None,
    background: BackgroundTasks | None = None,
) -> Job:
    try:
        concept_id = ConceptId(concept)
    except ValueError:
        raise UnsupportedConcept(str(concept))
    job = Job(
        job_id="v_" + uuid.uuid4().hex[:8],
        concept=concept_id,
        status=JobStatus.QUEUED,
        progress=0,
        stage_detail="queued",
        attempt=1,
        idempotency_key=idempotency_key,
    )
    if idempotency_key:
        # Atomic check-and-reserve: concurrent POSTs with the same key
        # serialize inside the repo; exactly one stores and dispatches,
        # the rest reuse the winner without launching a second pipeline.
        existing = repo.reserve_idempotency(idempotency_key, job)
        if existing is not None:
            return existing
    else:
        # Same atomicity as the key path: scan + insert serialize inside
        # the repo, so exactly one concurrent create stores and dispatches
        # while losers reuse the winner.
        winner = repo.reserve_concept(concept_id, job, DEDUP_WINDOW_SEC)
        if winner is not None:
            return winner
    _voices[job.job_id] = voice or DEFAULT_VOICE
    if background is not None:
        background.add_task(_submit, job.job_id)
    else:
        _submit(job.job_id)
    return job


def get_job(job_id: str) -> Job | None:
    return repo.get(job_id)


def list_jobs(
    status: JobStatus | None = None,
    concept: ConceptId | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[int, list[Job]]:
    limit = max(1, min(int(limit), 100))
    offset = max(0, int(offset))
    return repo.list(status=status, concept=concept, limit=limit, offset=offset)


def retry_job(job_id: str, background: BackgroundTasks | None = None) -> Job:
    # Single atomic claim: only the winner flips failed->queued and resets
    # per-attempt state; losers fall through to the error mapping below and
    # never dispatch a second pipeline.
    job = repo.try_acquire_retry(job_id, MAX_ATTEMPT)
    if job is None:
        current = repo.get(job_id)
        if current is None:
            raise JobNotFound(job_id)
        if current.status != JobStatus.FAILED:
            raise RetryNotAllowed(job_id, "only failed jobs can be retried")
        if not (current.error and current.error.retryable):
            raise RetryNotAllowed(job_id, "error is not retryable")
        if current.attempt >= MAX_ATTEMPT:
            raise RetryNotAllowed(job_id, "max attempts reached")
        if not can_transition(JobStatus.FAILED, JobStatus.QUEUED):
            raise RetryNotAllowed(job_id, "transition not allowed")
        raise RetryNotAllowed(job_id, "retry already in progress")
    if background is not None:
        background.add_task(_submit, job.job_id)
    else:
        _submit(job.job_id)
    return job
