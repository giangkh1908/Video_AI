"""In-memory job repo (thread-safe). Swap for Postgres via same interface."""
import threading
from datetime import datetime, timezone

from app.core.models import ConceptId, Job, JobStatus

IDEMPOTENCY_TTL_SEC = 24 * 3600


class InMemoryJobRepo:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._jobs: dict[str, Job] = {}
        self._by_idem: dict[str, tuple[str, datetime]] = {}

    def _sweep_idem_locked(self, now: datetime) -> None:
        expired = [
            key
            for key, (_, ts) in self._by_idem.items()
            if (now - ts).total_seconds() > IDEMPOTENCY_TTL_SEC
        ]
        for key in expired:
            del self._by_idem[key]

    def save(self, job: Job) -> None:
        now = datetime.now(timezone.utc)
        with self._lock:
            # Store a copy: callers mutate the object they passed in, and must
            # not be able to change stored state behind the lock's back.
            self._jobs[job.job_id] = job.model_copy(deep=True)
            self._sweep_idem_locked(now)
            if job.idempotency_key:
                self._by_idem[job.idempotency_key] = (job.job_id, now)

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            job = self._jobs.get(job_id)
            # Copy out: the pipeline mutates fetched jobs, and live refs would
            # let readers observe half-written state outside the lock.
            return job.model_copy(deep=True) if job is not None else None

    def get_by_idempotency(self, key: str) -> Job | None:
        now = datetime.now(timezone.utc)
        with self._lock:
            entry = self._by_idem.get(key)
            if entry is None:
                return None
            job_id, ts = entry
            if (now - ts).total_seconds() > IDEMPOTENCY_TTL_SEC:
                del self._by_idem[key]
                return None
            job = self._jobs.get(job_id)
            return job.model_copy(deep=True) if job is not None else None

    def reserve_idempotency(self, key: str, job: Job) -> Job | None:
        """Check-and-reserve in one locked section: return the winner's copy
        when key is taken, else store job, index it, and return None.
        Concurrent creates with the same key cannot both win."""
        now = datetime.now(timezone.utc)
        with self._lock:
            self._sweep_idem_locked(now)
            entry = self._by_idem.get(key)
            if entry is not None:
                job_id, ts = entry
                if (now - ts).total_seconds() <= IDEMPOTENCY_TTL_SEC:
                    existing = self._jobs.get(job_id)
                    if existing is not None:
                        return existing.model_copy(deep=True)
            self._jobs[job.job_id] = job.model_copy(deep=True)
            self._by_idem[key] = (job.job_id, now)
            return None

    def reserve_concept(
        self, concept: ConceptId, job: Job, window_sec: float
    ) -> Job | None:
        """Check-and-reserve one non-terminal same-concept job atomically:
        return the freshest winner's copy when a live job is inside the
        window, else store this job and return None. Scan and insert share
        one locked section so concurrent creates cannot both win."""
        now = datetime.now(timezone.utc)
        with self._lock:
            winner: Job | None = None
            for existing in self._jobs.values():
                if existing.concept != concept:
                    continue
                if existing.status in (JobStatus.COMPLETED, JobStatus.FAILED):
                    continue
                if (now - existing.created_at).total_seconds() >= window_sec:
                    continue
                if winner is None or existing.created_at > winner.created_at:
                    winner = existing
            if winner is not None:
                return winner.model_copy(deep=True)
            self._jobs[job.job_id] = job.model_copy(deep=True)
            self._sweep_idem_locked(now)
            if job.idempotency_key:
                self._by_idem[job.idempotency_key] = (job.job_id, now)
            return None

    def try_acquire_retry(self, job_id: str, max_attempt: int) -> Job | None:
        """Claim one retry atomically: eligibility check, attempt bump,
        requeue, and per-attempt reset in one locked section. Returns a copy
        of the requeued job; None means nothing to claim (unknown id, wrong
        status, non-retryable, attempts spent). Only a non-None return may
        dispatch a pipeline."""
        now = datetime.now(timezone.utc)
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            if job.status != JobStatus.FAILED:
                return None
            if not (job.error and job.error.retryable):
                return None
            if job.attempt >= max_attempt:
                return None
            job.status = JobStatus.QUEUED
            job.progress = 0
            job.stage_detail = "queued"
            job.attempt += 1
            job.audio_degraded = False
            job.fallback_used = False
            job.error = None
            job.timings = {}
            job.artifact_path = None
            job.updated_at = now
            return job.model_copy(deep=True)

    def list(
        self,
        status: JobStatus | None = None,
        concept: ConceptId | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[int, list[Job]]:
        with self._lock:
            jobs = [j.model_copy(deep=True) for j in self._jobs.values()]
        if status is not None:
            jobs = [j for j in jobs if j.status == status]
        if concept is not None:
            jobs = [j for j in jobs if j.concept == concept]
        jobs.sort(key=lambda j: j.created_at, reverse=True)
        return len(jobs), jobs[offset : offset + limit]
