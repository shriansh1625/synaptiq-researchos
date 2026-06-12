"""Executive report ORM model."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, JSON, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, UUIDMixin

if TYPE_CHECKING:
    from app.database.models.research_session import ResearchSession


class ExecutiveReport(UUIDMixin, Base):
    """Executive research brief generated for a research session."""

    __tablename__ = "executive_reports"

    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("research_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    recommendations: Mapped[list[Any]] = mapped_column(
        JSON,
        nullable=False,
    )
    citations: Mapped[list[Any]] = mapped_column(
        JSON,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    research_session: Mapped[ResearchSession] = relationship()
