# apps/backend-api/models/space.py

import uuid
from datetime import datetime

from sqlalchemy import String, Text, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from .base import Base, utcnow


class SpaceVisibility(str, enum.Enum):
    public  = "public"
    private = "private"


class SpaceStatus(str, enum.Enum):
    active   = "active"
    inactive = "inactive"
    archived = "archived"


class Space(Base):
    __tablename__ = "spaces"

    id:                   Mapped[uuid.UUID]        = mapped_column(primary_key=True, default=uuid.uuid4)
    name:                 Mapped[str]              = mapped_column(String(120), nullable=False)
    slug:                 Mapped[str]              = mapped_column(String(120), nullable=False, unique=True, index=True)
    description:          Mapped[str | None]       = mapped_column(Text, nullable=True)
    task_type:            Mapped[str]              = mapped_column(String(80), nullable=False, index=True)
    input_types:          Mapped[dict]             = mapped_column(JSONB, nullable=False, default=list)
    output_types:         Mapped[dict]             = mapped_column(JSONB, nullable=False, default=list)
    owner_id:             Mapped[uuid.UUID]        = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    container_image:      Mapped[str]              = mapped_column(String(255), nullable=False)
    resource_requirements:Mapped[dict]             = mapped_column(JSONB, nullable=False, default=dict)
    ui_config:            Mapped[dict]             = mapped_column(JSONB, nullable=False, default=dict)
    runner_config:        Mapped[dict]             = mapped_column(JSONB, nullable=False, default=dict)
    visibility:           Mapped[SpaceVisibility]  = mapped_column(SAEnum(SpaceVisibility), nullable=False, default=SpaceVisibility.public)
    status:               Mapped[SpaceStatus]      = mapped_column(SAEnum(SpaceStatus), nullable=False, default=SpaceStatus.active, index=True)
    created_at:           Mapped[datetime]         = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at:           Mapped[datetime]         = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    # Relationships
    owner: Mapped["User"]      = relationship("User", back_populates="spaces")
    jobs:  Mapped[list["Job"]] = relationship("Job",  back_populates="space")
