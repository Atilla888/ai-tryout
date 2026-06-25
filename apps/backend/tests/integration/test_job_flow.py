"""
tests/integration/test_job_flow.py

Integration tests — Job Submission and Progress Flow
Acceptance Criteria:
  AC-1  create → queued → update progress → verify → succeed → artifacts
  AC-2  create → cancel while queued → verify cancelled
  AC-3  missing/wrong job ID → 404 on every endpoint

Identifier reference:
  Public endpoints (/jobs/..., /spaces/...) address jobs by their UUID public_id.
  Internal endpoints (/internal/jobs/...) address jobs by their integer id.
  So tests use ``queued_job.public_id`` vs ``queued_job.id`` accordingly.
"""

import pytest

pytestmark = pytest.mark.asyncio

NONEXISTENT_PUBLIC_ID = "00000000-0000-0000-0000-000000000000"
NONEXISTENT_INTERNAL_ID = 999999999
SERVICE_HEADERS = {"X-Service-Token": "test-internal-token"}


# ===========================================================================
# AC-1 — Full happy-path job flow
# ===========================================================================
class TestJobHappyPath:
    """
    Seed a QUEUED job → verify status → update progress →
    verify progress → mark succeeded → verify artifacts list
    """

    async def test_get_queued_job_status(self, client, queued_job):
        """GET /jobs/{id} must return status=QUEUED right after seeding."""
        response = await client.get(f"/jobs/{queued_job.public_id}")
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["id"] == str(queued_job.public_id)
        assert body["status"] == "QUEUED"

    async def test_start_job_changes_status_to_starting(self, client, queued_job):
        """PATCH /internal/jobs/{id}/start must change status to STARTING."""
        response = await client.patch(
            f"/internal/jobs/{queued_job.id}/start",
            headers=SERVICE_HEADERS,
        )
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "STARTING"

    async def test_update_progress_returns_200(self, client, queued_job):
        """PATCH /internal/jobs/{id}/progress must return 200."""
        # start → progress moves the job into RUNNING state
        await client.patch(f"/internal/jobs/{queued_job.id}/start", headers=SERVICE_HEADERS)
        response = await client.patch(
            f"/internal/jobs/{queued_job.id}/progress",
            json={"progress_percent": 42, "message": "Processing..."},
            headers=SERVICE_HEADERS,
        )
        assert response.status_code == 200, response.text

    async def test_get_job_reflects_updated_progress(self, client, queued_job):
        """After a progress update, GET /jobs/{id} must reflect the new value."""
        await client.patch(f"/internal/jobs/{queued_job.id}/start", headers=SERVICE_HEADERS)
        await client.patch(
            f"/internal/jobs/{queued_job.id}/progress",
            json={"progress_percent": 75, "message": "Almost done"},
            headers=SERVICE_HEADERS,
        )
        response = await client.get(f"/jobs/{queued_job.public_id}")
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["progress_percent"] == 75

    async def _advance_to_running(self, client, internal_job_id):
        """Helper: QUEUED → STARTING → RUNNING (via first progress update)."""
        await client.patch(f"/internal/jobs/{internal_job_id}/start", headers=SERVICE_HEADERS)
        await client.patch(
            f"/internal/jobs/{internal_job_id}/progress",
            json={"progress_percent": 1, "message": "started"},
            headers=SERVICE_HEADERS,
        )

    async def test_mark_succeeded_changes_status(self, client, queued_job):
        """PATCH /internal/jobs/{id}/succeed must change status to SUCCEEDED."""
        await self._advance_to_running(client, queued_job.id)
        response = await client.patch(
            f"/internal/jobs/{queued_job.id}/succeed",
            headers=SERVICE_HEADERS,
        )
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "SUCCEEDED"

    async def test_artifacts_list_after_upload(self, client, queued_job, tmp_path):
        """
        After uploading an artifact via POST /internal/jobs/{id}/artifacts,
        GET /jobs/{id}/artifacts must return a non-empty list.
        """
        await self._advance_to_running(client, queued_job.id)
        await client.patch(f"/internal/jobs/{queued_job.id}/succeed", headers=SERVICE_HEADERS)

        # Upload a small test file as the artifact
        dummy_file = tmp_path / "result.jpg"
        dummy_file.write_bytes(b"\xff\xd8\xff" + b"\x00" * 10)  # minimal JPEG header

        with open(dummy_file, "rb") as f:
            upload_response = await client.post(
                f"/internal/jobs/{queued_job.id}/artifacts",
                data={"artifact_type": "image", "preview_supported": "false"},
                files={"file": ("result.jpg", f, "image/jpeg")},
                headers=SERVICE_HEADERS,
            )
        assert upload_response.status_code == 201, upload_response.text

        # Verify artifacts list (public endpoint, addressed by public_id)
        list_response = await client.get(f"/jobs/{queued_job.public_id}/artifacts")
        assert list_response.status_code == 200, list_response.text
        artifacts = list_response.json()
        assert isinstance(artifacts, list)
        assert len(artifacts) > 0
        # Verify the uploaded file appears — check available keys from the response
        artifact = artifacts[0]
        assert any("result.jpg" in str(v) for v in artifact.values()), (
            f"Expected 'result.jpg' somewhere in artifact fields, got: {artifact}"
        )


# ===========================================================================
# AC-2 — Cancel flow
# ===========================================================================
class TestJobCancelFlow:
    """Seed a QUEUED job → cancel → verify status is CANCELLED"""

    async def test_cancel_queued_job_returns_200(self, client, queued_job):
        """POST /jobs/{id}/cancel on a queued job must return 200."""
        response = await client.post(f"/jobs/{queued_job.public_id}/cancel")
        assert response.status_code == 200, response.text

    async def test_cancelled_job_status_is_cancelled(self, client, queued_job):
        """After cancellation, GET /jobs/{id} must return status=CANCELLED."""
        await client.post(f"/jobs/{queued_job.public_id}/cancel")
        response = await client.get(f"/jobs/{queued_job.public_id}")
        assert response.status_code == 200
        assert response.json()["status"] == "CANCELLED"

    async def test_cancelled_job_not_in_queued_list(self, client, queued_job):
        """
        After cancellation the job must not appear when listing QUEUED jobs
        (US-07 AC-2: 'no longer appears as active to the user').
        """
        await client.post(f"/jobs/{queued_job.public_id}/cancel")
        response = await client.get("/internal/jobs?status=QUEUED", headers=SERVICE_HEADERS)
        assert response.status_code == 200
        queued_ids = [j["id"] for j in response.json()]
        assert queued_job.id not in queued_ids

    async def test_cancel_already_cancelled_is_idempotent(self, client, queued_job):
        """Double-cancelling must never return a 5xx error."""
        await client.post(f"/jobs/{queued_job.public_id}/cancel")
        second = await client.post(f"/jobs/{queued_job.public_id}/cancel")
        assert second.status_code in (200, 409), (
            f"Unexpected {second.status_code} on double-cancel"
        )


# ===========================================================================
# AC-3 — 404 for missing / wrong job IDs
# ===========================================================================
class TestJobNotFound:
    """All endpoints must return 404 for a non-existent job ID."""

    async def test_get_nonexistent_job(self, client):
        r = await client.get(f"/jobs/{NONEXISTENT_PUBLIC_ID}")
        assert r.status_code == 404, r.text

    async def test_cancel_nonexistent_job(self, client):
        r = await client.post(f"/jobs/{NONEXISTENT_PUBLIC_ID}/cancel")
        assert r.status_code == 404, r.text

    async def test_progress_nonexistent_job(self, client):
        r = await client.patch(
            f"/internal/jobs/{NONEXISTENT_INTERNAL_ID}/progress",
            json={"progress_percent": 50, "message": "test"},
            headers=SERVICE_HEADERS,
        )
        assert r.status_code == 404, r.text

    async def test_succeed_nonexistent_job(self, client):
        r = await client.patch(
            f"/internal/jobs/{NONEXISTENT_INTERNAL_ID}/succeed",
            headers=SERVICE_HEADERS,
        )
        assert r.status_code == 404, r.text

    async def test_artifacts_nonexistent_job(self, client):
        r = await client.get(f"/jobs/{NONEXISTENT_PUBLIC_ID}/artifacts")
        assert r.status_code == 404, r.text

    async def test_malformed_job_id_never_500(self, client):
        """A completely invalid (non-UUID) ID must return 404 or 422, never 500."""
        r = await client.get("/jobs/not-a-valid-uuid")
        assert r.status_code in (404, 422), (
            f"Expected 404 or 422 for malformed ID, got {r.status_code}"
        )
