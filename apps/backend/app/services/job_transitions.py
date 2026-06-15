from app.schemas.jobs import JobStatus


class JobTransitionError(ValueError):
    """Raised when an attempted job status transition is not allowed by the state machine."""
    pass


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
    """Checks that transitioning from current to new is valid. Raises JobTransitionError
    if the transition is not listed in _ALLOWED, preventing illegal state changes."""
    try:
        current_status = JobStatus(current)
    except ValueError as exc:
        raise JobTransitionError(f"Unknown current status: {current}") from exc

    if new not in _ALLOWED.get(current_status, set()):
        raise JobTransitionError(f"Cannot transition from {current_status.value} to {new.value}")
