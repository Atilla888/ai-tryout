from datetime import datetime
from sqlalchemy import ForeignKey, UniqueConstraint, Uuid, Integer, Boolean, String, DateTime, func
from app.db.base import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
import uuid
from typing import Any

class User(Base):
    """App user, created on first login. subject_id + idp is the unique key."""
    __tablename__="users"
    __table_args__=(UniqueConstraint("idp", "subject_id"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), unique=True, default=uuid.uuid4)
    subject_id: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    idp: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    role: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    spaces: Mapped[list["Space"]] = relationship(back_populates="owner")
    jobs: Mapped[list["Job"]] = relationship(back_populates="user")


class Space(Base):
    """Runnable AI space with a form and runner config. Slug is unique per owner."""
    __tablename__ = "spaces"
    __table_args__ = (UniqueConstraint("owner_id", "slug"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), unique=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), nullable=False)
    task_type: Mapped[str] = mapped_column(String(100), nullable=False)
    input_types: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    output_types: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    container_image: Mapped[str] = mapped_column(String(1000), nullable=False)
    ui_config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    runner_config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    visibility: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(100), nullable=False)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    owner: Mapped["User"] = relationship(back_populates="spaces")
    jobs: Mapped[list["Job"]] = relationship(back_populates="space")

class Job(Base):
    """One submitted inference run. Status moves through the orchestrator state machine."""
    __tablename__ = "jobs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), unique=True, default=uuid.uuid4)
    status: Mapped[str] = mapped_column(String(100), nullable=False, default="QUEUED")
    queue_position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    progress_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    progress_message: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    input_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    space_id: Mapped[int] = mapped_column(ForeignKey("spaces.id"), nullable=False)
    space: Mapped["Space"] = relationship(back_populates="jobs")
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    user: Mapped["User"] = relationship(back_populates="jobs")
    artifacts: Mapped[list["Artifact"]] = relationship(back_populates="job")


class Artifact(Base):
    """File metadata for a job. Bytes live on disk at storage_path."""
    __tablename__ = "artifacts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), unique=True, default=uuid.uuid4)
    artifact_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_name: Mapped[str] = mapped_column(String(100), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    preview_supported: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), nullable=False)

    job: Mapped["Job"] = relationship(back_populates="artifacts")