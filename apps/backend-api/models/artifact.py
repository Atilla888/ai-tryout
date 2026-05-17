# apps/backend-api/models/artifact.py

import uuid
from datetime import datetime

from sqlalchemy import String, BigInteger, Boolean, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from .base import Base, utcnow


class ArtifactType(str, enum.Enum):
    image  = "image"
    video  = "video"
    model3d = "model3d"
    text   = "text"
    other  = "other"


class Artifact(Base):
    __tablename__ = "artifacts"

    id:                Mapped[uuid.UUID]       = mapped_column(primary_key=True, default=uuid.uuid4)
    job_id:            Mapped[uuid.UUID]       = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id:           Mapped[uuid.UUID]       = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    artifact_type:     Mapped[ArtifactType]    = mapped_column(SAEnum(ArtifactType), nullable=False, index=True)
    file_name:         Mapped[str]             = mapped_column(String(255), nullable=False)
    content_type:      Mapped[str]             = mapped_column(String(120), nullable=False)  # MIME type
    size_bytes:        Mapped[int | None]      = mapped_column(BigInteger, nullable=True)
    storage_path:      Mapped[str]             = mapped_column(String(512), nullable=False)  # MinIO object key
    preview_supported: Mapped[bool]            = mapped_column(Boolean, nullable=False, default=False)
    created_at:        Mapped[datetime]        = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    expires_at:        Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    # Relationships
    job:  Mapped["Job"]  = relationship("Job",  back_populates="artifacts")
    user: Mapped["User"] = relationship("User", back_populates="artifacts")
