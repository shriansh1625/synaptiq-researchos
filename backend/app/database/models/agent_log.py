"""Agent execution log ORM model."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, UUIDMixin

if TYPE_CHECKING:
    from app.database.models.research_session import ResearchSession


class AgentLog(UUIDMixin, Base):
    """Immutable audit log entry for agent pipeline execution."""

    __tablename__ = "agent_logs"

    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("research_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agent_name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    input_data: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
    )
    output_data: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
    )
    latency: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    confidence_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    research_session: Mapped[ResearchSession] = relationship()
