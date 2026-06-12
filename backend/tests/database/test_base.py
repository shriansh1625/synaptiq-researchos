"""Tests for SQLAlchemy base and mixins."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from app.database.base import Base, TimestampMixin, UUIDMixin


class _SampleModel(UUIDMixin, TimestampMixin, Base):
    """Minimal model used only for mixin verification in tests."""

    __tablename__ = "sample_model_test"

    name: Mapped[str] = mapped_column(String(50), nullable=False)


@pytest.fixture
def engine():
    """Provide an in-memory SQLite engine for mixin tests."""
    test_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(test_engine)
    yield test_engine
    Base.metadata.drop_all(test_engine)


def test_base_is_sqlalchemy_declarative_base() -> None:
    """Base should be a SQLAlchemy 2.0 declarative base."""
    assert issubclass(Base, DeclarativeBase)


def test_uuid_mixin_defines_uuid_primary_key() -> None:
    """UUIDMixin should expose a UUID primary key column named id."""
    table = _SampleModel.__table__
    id_column = table.c.id

    assert id_column.primary_key is True
    assert id_column.nullable is False


def test_timestamp_mixin_defines_created_and_updated_at() -> None:
    """TimestampMixin should expose timezone-aware timestamp columns."""
    table = _SampleModel.__table__

    assert "created_at" in table.c
    assert "updated_at" in table.c
    assert table.c.created_at.nullable is False
    assert table.c.updated_at.nullable is False


def test_mixins_persist_uuid_and_timestamps(engine) -> None:
    """A model using both mixins should persist UUID and timestamp fields."""
    with Session(engine) as session:
        instance = _SampleModel(name="synaptiq")
        session.add(instance)
        session.commit()
        session.refresh(instance)

        assert isinstance(instance.id, uuid.UUID)
        assert instance.created_at is not None
        assert instance.updated_at is not None

        result = session.scalar(select(_SampleModel).where(_SampleModel.id == instance.id))
        assert result is not None
        assert result.name == "synaptiq"
