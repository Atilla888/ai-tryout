from app.schemas.jobs import JobStatus


class JobTransitionError(ValueError):
    """Someone tried to move a job to a status we do not allow."""
    pass


# Allowed moves from each status. Empty set means the job is done.
_ALLOWED: dict[JobStatus, set[JobStatus]] = {
    JobStatus.QUEUED: {JobStatus.STARTING, JobStatus.CANCELLED},
    JobStatus.STARTING: {JobStatus.RUNNING, JobStatus.FAILED, JobStatus.CANCELLED, JobStatus.CANCELLING},
    JobStatus.RUNNING: {JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLING},
    JobStatus.CANCELLING: {JobStatus.CANCELLED},
    JobStatus.SUCCEEDED: set(),
    JobStatus.FAILED: set(),
    JobStatus.CANCELLED: set(),
    JobStatus.EXPIRED: set(),
}


def ensure_transition(current: str, new: JobStatus) -> None:
    """Raise JobTransitionError if this status change is not allowed."""
    try:
        current_status = JobStatus(current)
    except ValueError as exc:
        raise JobTransitionError(f"Unknown current status: {current}") from exc

    if new not in _ALLOWED.get(current_status, set()):
        raise JobTransitionError(f"Cannot transition from {current_status.value} to {new.value}")
