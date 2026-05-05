"""SQLAlchemy ORM models — database layer only.

Keep business logic and response shapes in schemas.py.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class UserRole(str, enum.Enum):
    user = "user"
    creator = "creator"
    admin = "admin"


class SpaceVisibility(str, enum.Enum):
    public = "public"
    private = "private"


class SpaceStatus(str, enum.Enum):
    draft = "draft"
    published = "published"
    disabled = "disabled"


class JobStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class ArtifactType(str, enum.Enum):
    image = "image"
    audio = "audio"
    video = "video"
    text = "text"
    file = "file"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"), nullable=False, default=UserRole.user
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    spaces: Mapped[list["Space"]] = relationship("Space", back_populates="owner")
    jobs: Mapped[list["Job"]] = relationship("Job", back_populates="user")
    artifacts: Mapped[list["Artifact"]] = relationship("Artifact", back_populates="user")


class Space(Base):
    __tablename__ = "spaces"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    task_type: Mapped[str] = mapped_column(String(60), nullable=False)
    input_types: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    output_types: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    container_image: Mapped[str | None] = mapped_column(String(255))
    resource_requirements: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    ui_config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    runner_config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    visibility: Mapped[SpaceVisibility] = mapped_column(
        Enum(SpaceVisibility, name="space_visibility"),
        nullable=False,
        default=SpaceVisibility.public,
    )
    status: Mapped[SpaceStatus] = mapped_column(
        Enum(SpaceStatus, name="space_status"),
        nullable=False,
        default=SpaceStatus.draft,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    owner: Mapped["User"] = relationship("User", back_populates="spaces")
    jobs: Mapped[list["Job"]] = relationship("Job", back_populates="space")


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    space_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("spaces.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status"),
        nullable=False,
        default=JobStatus.queued,
        index=True,
    )
    input_payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    queue_position: Mapped[int | None] = mapped_column(Integer)
    progress_percent: Mapped[int | None] = mapped_column(Integer)
    progress_message: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(60))
    error_message: Mapped[str | None] = mapped_column(Text)

    space: Mapped["Space"] = relationship("Space", back_populates="jobs")
    user: Mapped["User | None"] = relationship("User", back_populates="jobs")
    artifacts: Mapped[list["Artifact"]] = relationship("Artifact", back_populates="job")


class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    artifact_type: Mapped[ArtifactType] = mapped_column(
        Enum(ArtifactType, name="artifact_type"), nullable=False
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    preview_supported: Mapped[bool] = mapped_column(nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    job: Mapped["Job"] = relationship("Job", back_populates="artifacts")
    user: Mapped["User | None"] = relationship("User", back_populates="artifacts")
