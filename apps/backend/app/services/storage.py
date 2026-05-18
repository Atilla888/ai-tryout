from pathlib import Path
from uuid import UUID

from fastapi import UploadFile

from app.config import settings


def storage_root() -> Path:
    root = Path(settings.artifact_storage_root)
    root.mkdir(parents=True, exist_ok=True)
    return root.resolve()


def resolve_storage_path(relative_path: str) -> Path:
    """Resolve a DB-relative path under ARTIFACT_STORAGE_ROOT; block traversal."""
    root = storage_root()
    full = (root / relative_path).resolve()
    if not str(full).startswith(str(root)):
        raise ValueError("Invalid storage path")
    return full


async def save_job_file(
    job_id: UUID,
    file: UploadFile,
    *,
    subdir: str,
) -> tuple[str, int, str]:
    """Write file under jobs/<job_id>/<subdir>/; return relative storage_path."""
    safe_name = Path(file.filename or "upload").name or "upload"
    relative = Path("jobs") / str(job_id) / subdir / safe_name
    absolute = storage_root() / relative
    absolute.parent.mkdir(parents=True, exist_ok=True)

    content = await file.read()
    absolute.write_bytes(content)

    return relative.as_posix(), len(content), safe_name


async def save_job_input_file(job_id: UUID, file: UploadFile) -> tuple[str, int, str]:
    return await save_job_file(job_id, file, subdir="input")


async def save_job_output_file(job_id: UUID, file: UploadFile) -> tuple[str, int, str]:
    return await save_job_file(job_id, file, subdir="output")
