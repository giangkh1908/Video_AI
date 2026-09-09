"""State machine — allowed transitions only. See docs/04 §4.2."""
from datetime import datetime, timezone

from app.core.models import Job, JobStatus

ALLOWED_TRANSITIONS: dict[JobStatus, set[JobStatus]] = {
    JobStatus.QUEUED: {JobStatus.SCRIPTING, JobStatus.FAILED},
    JobStatus.SCRIPTING: {JobStatus.NARRATING, JobStatus.FAILED},
    JobStatus.NARRATING: {JobStatus.RENDERING, JobStatus.FAILED},
    JobStatus.RENDERING: {JobStatus.COMPOSITING, JobStatus.FAILED},
    JobStatus.COMPOSITING: {JobStatus.VALIDATING, JobStatus.FAILED},
    JobStatus.VALIDATING: {JobStatus.COMPLETED, JobStatus.FAILED},
    JobStatus.FAILED: {JobStatus.QUEUED},  # via retry, attempt<3
    JobStatus.COMPLETED: set(),
}

ALLOWED = ALLOWED_TRANSITIONS

PROGRESS: dict[JobStatus, int] = {
    JobStatus.QUEUED: 0,
    JobStatus.SCRIPTING: 20,
    JobStatus.NARRATING: 40,
    JobStatus.RENDERING: 75,
    JobStatus.COMPOSITING: 90,
    # 95, not 100: 100 is reserved for COMPLETED so polling never reads
    # "done" while /file still 409s on the validating job.
    JobStatus.VALIDATING: 95,
    JobStatus.COMPLETED: 100,
    JobStatus.FAILED: 0,  # unused: transition() keeps last progress on failure
}


def can_transition(fr: JobStatus, to: JobStatus) -> bool:
    return to in ALLOWED_TRANSITIONS[fr]


def transition(job: Job, to: JobStatus) -> Job:
    """Move job to `to`. Illegal edge → ValueError (never surfaces to client)."""
    if not can_transition(job.status, to):
        raise ValueError(f"illegal transition {job.status.value} -> {to.value}")
    job.status = to
    if to is not JobStatus.FAILED:
        job.progress = PROGRESS[to]
    job.updated_at = datetime.now(timezone.utc)
    return job
