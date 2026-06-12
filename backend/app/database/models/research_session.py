"""Research session ORM model."""

from __future__ import annotations

import uuid
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.database.models.user import User


class ResearchSessionStatus(StrEnum):
    """Lifecycle status for a research session."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ResearchSession(UUIDMixin, TimestampMixin, Base):
    """A user-owned research query session."""

    __tablename__ = "research_sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    query: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=ResearchSessionStatus.PENDING,
        server_default=ResearchSessionStatus.PENDING,
    )

    user: Mapped[User] = relationship()
