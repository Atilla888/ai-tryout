# apps/backend-api/models/user.py

import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from .base import Base, utcnow


class UserRole(str, enum.Enum):
    user    = "user"
    creator = "creator"
    admin   = "admin"


class User(Base):
    __tablename__ = "users"

    id:           Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    display_name: Mapped[str]       = mapped_column(String(120), nullable=False)
    email:        Mapped[str]       = mapped_column(String(255), nullable=False, unique=True, index=True)
    role:         Mapped[UserRole]  = mapped_column(SAEnum(UserRole), nullable=False, default=UserRole.user)
    created_at:   Mapped[datetime]  = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    # Relationships (back-populated from other models)
    spaces:    Mapped[list["Space"]]    = relationship("Space",    back_populates="owner")
    jobs:      Mapped[list["Job"]]      = relationship("Job",      back_populates="user")
    artifacts: Mapped[list["Artifact"]] = relationship("Artifact", back_populates="user")
