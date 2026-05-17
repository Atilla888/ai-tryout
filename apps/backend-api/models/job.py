# apps/backend-api/models/job.py

import uuid
from datetime import datetime

from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from .base import Base, utcnow


class JobStatus(str, enum.Enum):
    queued     = "queued"
    running    = "running"
    succeeded  = "succeeded"
    failed     = "failed"
    cancelled  = "cancelled"


class Job(Base):
    __tablename__ = "jobs"

    id:               Mapped[uuid.UUID]      = mapped_column(primary_key=True, default=uuid.uuid4)
    space_id:         Mapped[uuid.UUID]      = mapped_column(ForeignKey("spaces.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id:          Mapped[uuid.UUID]      = mapped_column(ForeignKey("users.id",  ondelete="SET NULL"), nullable=True,  index=True)
    status:           Mapped[JobStatus]      = mapped_column(SAEnum(JobStatus), nullable=False, default=JobStatus.queued, index=True)
    input_payload:    Mapped[dict]           = mapped_column(JSONB, nullable=False, default=dict)
    queue_position:   Mapped[int | None]     = mapped_column(Integer, nullable=True)
    progress_percent: Mapped[int | None]     = mapped_column(Integer, nullable=True)
    progress_message: Mapped[str | None]     = mapped_column(Text, nullable=True)
    created_at:       Mapped[datetime]       = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    started_at:       Mapped[datetime | None]= mapped_column(DateTime(timezone=True), nullable=True)
    finished_at:      Mapped[datetime | None]= mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at:     Mapped[datetime | None]= mapped_column(DateTime(timezone=True), nullable=True)
    expires_at:       Mapped[datetime | None]= mapped_column(DateTime(timezone=True), nullable=True, index=True)
    error_code:       Mapped[str | None]     = mapped_column(String(80), nullable=True)
    error_message:    Mapped[str | None]     = mapped_column(Text, nullable=True)

    # Relationships
    space:     Mapped["Space"]          = relationship("Space",    back_populates="jobs")
    user:      Mapped["User"]           = relationship("User",     back_populates="jobs")
    artifacts: Mapped[list["Artifact"]] = relationship("Artifact", back_populates="job")
