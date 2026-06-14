"""Unit tests for the job lifecycle state machine.

These tests exercise the pure transition logic in
``app.services.job_transitions`` in isolation. No database or other
external dependency is required.
"""

import pytest

from app.schemas.jobs import JobStatus
from app.services.job_transitions import JobTransitionError, ensure_transition


# Specification of the allowed state machine, independent of the
# implementation's internal `_ALLOWED` table. Any drift between this
# table and the implementation should fail the tests below.
EXPECTED_TRANSITIONS: dict[JobStatus, set[JobStatus]] = {
    JobStatus.QUEUED: {JobStatus.STARTING, JobStatus.CANCELLED},
    JobStatus.STARTING: {
        JobStatus.RUNNING,
        JobStatus.FAILED,
        JobStatus.CANCELLED,
        JobStatus.CANCELLING,
    },
    JobStatus.RUNNING: {JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLING},
    JobStatus.CANCELLING: {JobStatus.CANCELLED},
    JobStatus.SUCCEEDED: set(),
    JobStatus.FAILED: set(),
    JobStatus.CANCELLED: set(),
    JobStatus.EXPIRED: set(),
}

VALID_TRANSITIONS = [
    (current, target)
    for current, targets in EXPECTED_TRANSITIONS.items()
    for target in targets
]

INVALID_TRANSITIONS = [
    (current, target)
    for current in JobStatus
    for target in JobStatus
    if target not in EXPECTED_TRANSITIONS[current]
]

TERMINAL_STATUSES = [
    JobStatus.SUCCEEDED,
    JobStatus.FAILED,
    JobStatus.CANCELLED,
    JobStatus.EXPIRED,
]


@pytest.mark.parametrize("current,target", VALID_TRANSITIONS)
def test_valid_transition_is_allowed(current, target):
    assert ensure_transition(current.value, target) is None


@pytest.mark.parametrize("current,target", INVALID_TRANSITIONS)
def test_invalid_transition_raises(current, target):
    with pytest.raises(JobTransitionError) as exc_info:
        ensure_transition(current.value, target)
    message = str(exc_info.value)
    assert current.value in message
    assert target.value in message


@pytest.mark.parametrize("status", JobStatus)
def test_self_transition_is_rejected(status):
    if status in EXPECTED_TRANSITIONS[status]:
        pytest.fail(f"{status} allows a self-transition; update the test if intentional")
    with pytest.raises(JobTransitionError):
        ensure_transition(status.value, status)


@pytest.mark.parametrize("status", TERMINAL_STATUSES)
def test_terminal_statuses_have_no_outgoing_transitions(status):
    assert EXPECTED_TRANSITIONS[status] == set()
    for target in JobStatus:
        with pytest.raises(JobTransitionError):
            ensure_transition(status.value, target)


@pytest.mark.parametrize("target", JobStatus)
def test_nothing_transitions_directly_to_expired(target):
    if target is not JobStatus.EXPIRED:
        pytest.skip("only checking EXPIRED as a target")
    for current in JobStatus:
        with pytest.raises(JobTransitionError):
            ensure_transition(current.value, JobStatus.EXPIRED)


def test_happy_path_lifecycle_queued_to_succeeded():
    ensure_transition(JobStatus.QUEUED.value, JobStatus.STARTING)
    ensure_transition(JobStatus.STARTING.value, JobStatus.RUNNING)
    ensure_transition(JobStatus.RUNNING.value, JobStatus.SUCCEEDED)


def test_cancellation_lifecycle_from_running():
    ensure_transition(JobStatus.QUEUED.value, JobStatus.STARTING)
    ensure_transition(JobStatus.STARTING.value, JobStatus.RUNNING)
    ensure_transition(JobStatus.RUNNING.value, JobStatus.CANCELLING)
    ensure_transition(JobStatus.CANCELLING.value, JobStatus.CANCELLED)


def test_immediate_cancellation_from_queued():
    ensure_transition(JobStatus.QUEUED.value, JobStatus.CANCELLED)


def test_failure_during_starting():
    ensure_transition(JobStatus.STARTING.value, JobStatus.FAILED)


def test_unknown_current_status_raises_job_transition_error():
    with pytest.raises(JobTransitionError, match="Unknown current status: BOGUS"):
        ensure_transition("BOGUS", JobStatus.QUEUED)


def test_unknown_current_status_preserves_original_error_as_cause():
    with pytest.raises(JobTransitionError) as exc_info:
        ensure_transition("BOGUS", JobStatus.QUEUED)
    assert isinstance(exc_info.value.__cause__, ValueError)
