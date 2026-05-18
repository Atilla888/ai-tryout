from app.schemas.jobs import JobStatus


class JobTransitionError(ValueError):
    pass


_ALLOWED: dict[JobStatus, set[JobStatus]] = {
    JobStatus.QUEUED: {JobStatus.RUNNING, JobStatus.CANCELLED},
    JobStatus.RUNNING: {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED},
    JobStatus.COMPLETED: set(),
    JobStatus.FAILED: set(),
    JobStatus.CANCELLED: set(),
}


def ensure_transition(current: str, new: JobStatus) -> None:
    try:
        current_status = JobStatus(current)
    except ValueError as exc:
        raise JobTransitionError(f"Unknown current status: {current}") from exc

    if new not in _ALLOWED.get(current_status, set()):
        raise JobTransitionError(
            f"Cannot transition from {current_status.value} to {new.value}"
        )
