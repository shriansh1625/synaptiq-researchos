"""User ORM model."""

from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDMixin


class User(UUIDMixin, TimestampMixin, Base):
    """Application user account."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(320),
        unique=True,
        nullable=False,
        index=True,
    )
    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )
