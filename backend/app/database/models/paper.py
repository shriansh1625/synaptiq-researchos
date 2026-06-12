"""Paper ORM model."""

from __future__ import annotations

from datetime import date
from enum import StrEnum

from sqlalchemy import JSON, Date, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDMixin


class EmbeddingStatus(StrEnum):
    """Embedding pipeline status for a paper."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Paper(UUIDMixin, TimestampMixin, Base):
    """Research paper metadata stored in the system."""

    __tablename__ = "papers"

    title: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        index=True,
    )
    abstract: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    authors: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
    )
    publication_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )
    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    url: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
    )
    doi: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    embedding_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=EmbeddingStatus.PENDING,
        server_default=EmbeddingStatus.PENDING,
    )
