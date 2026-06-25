import shutil
from pathlib import Path
from uuid import UUID

from fastapi import UploadFile

from app.core.config import settings


def storage_root() -> Path:
    """Root folder for uploaded files; created on first use."""
    root = Path(settings.artifact_storage_root)
    root.mkdir(parents=True, exist_ok=True)
    return root.resolve()


def resolve_storage_path(relative_path: str) -> Path:
    """Turn a stored relative path into an absolute one, and block path traversal."""
    root = storage_root()
    full = (root / relative_path).resolve()
    # resolve() collapses '..' segments; the prefix check then rejects any path
    # that escapes the storage root, preventing directory traversal attacks.
    if not str(full).startswith(str(root)):
        raise ValueError("Invalid storage path")
    return full


async def save_job_file(
    job_id: UUID,
    file: UploadFile,
    *,
    subdir: str,
) -> tuple[str, int, str]:
    """Write under jobs/<job_id>/<subdir>/ and return path, size, and filename."""
    safe_name = Path(file.filename or "upload").name or "upload"
    relative = Path("jobs") / str(job_id) / subdir / safe_name
    absolute = storage_root() / relative
    absolute.parent.mkdir(parents=True, exist_ok=True)

    content = await file.read()
    absolute.write_bytes(content)

    return relative.as_posix(), len(content), safe_name


def delete_storage_file(relative_path: str) -> bool:
    """Remove a single stored file. Returns True if a file was deleted."""
    try:
        full = resolve_storage_path(relative_path)
    except ValueError:
        return False
    if full.is_file():
        full.unlink()
        return True
    return False


def delete_job_storage(job_id: UUID | int) -> None:
    """Remove the whole jobs/<job_id>/ directory (inputs and outputs) from disk.

    Used by the expiration cleanup so expired artifact files don't linger (D3).
    Best-effort: a missing directory is fine.
    """
    job_dir = (storage_root() / "jobs" / str(job_id)).resolve()
    root = storage_root()
    if not str(job_dir).startswith(str(root)):
        return
    if job_dir.is_dir():
        shutil.rmtree(job_dir, ignore_errors=True)


async def save_job_input_file(job_id: UUID, file: UploadFile) -> tuple[str, int, str]:
    return await save_job_file(job_id, file, subdir="input")


async def save_job_output_file(job_id: UUID, file: UploadFile) -> tuple[str, int, str]:
    return await save_job_file(job_id, file, subdir="output")
