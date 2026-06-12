"""Tests for the ResearchSession ORM model."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.base import Base
from app.database.models.research_session import ResearchSession, ResearchSessionStatus
from app.database.models.user import User


@pytest.fixture
def engine():
    """Provide an in-memory SQLite engine for ResearchSession model tests."""
    test_engine = create_engine("sqlite:///:memory:")

    @event.listens_for(test_engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(test_engine)
    yield test_engine
    Base.metadata.drop_all(test_engine)


def test_research_session_table_has_expected_columns() -> None:
    """ResearchSession should define all required fields."""
    table = ResearchSession.__table__
    column_names = set(table.c.keys())

    assert {
        "id",
        "user_id",
        "query",
        "status",
        "created_at",
        "updated_at",
    }.issubset(column_names)


def test_research_session_user_id_foreign_key() -> None:
    """user_id should reference users.id."""
    table = ResearchSession.__table__
    foreign_keys = {fk.target_fullname for fk in table.c.user_id.foreign_keys}

    assert "users.id" in foreign_keys


def test_research_session_persists_with_user_relationship(engine) -> None:
    """ResearchSession should persist and relate to its owning user."""
    with Session(engine) as session:
        user = User(email="researcher@synaptiq.ai", username="researcher")
        session.add(user)
        session.commit()
        session.refresh(user)

        research_session = ResearchSession(
            user_id=user.id,
            query="Does intermittent fasting improve insulin sensitivity?",
            status=ResearchSessionStatus.RUNNING,
        )
        session.add(research_session)
        session.commit()
        session.refresh(research_session)

        assert isinstance(research_session.id, uuid.UUID)
        assert research_session.user_id == user.id
        assert research_session.query.startswith("Does intermittent fasting")
        assert research_session.status == ResearchSessionStatus.RUNNING
        assert research_session.created_at is not None
        assert research_session.updated_at is not None

        loaded = session.scalar(
            select(ResearchSession).where(ResearchSession.id == research_session.id)
        )
        assert loaded is not None
        assert loaded.user.id == user.id
        assert loaded.user.email == "researcher@synaptiq.ai"


def test_research_session_defaults_status_to_pending(engine) -> None:
    """New research sessions should default to pending status."""
    with Session(engine) as session:
        user = User(email="pending@synaptiq.ai", username="pending_user")
        session.add(user)
        session.commit()

        research_session = ResearchSession(
            user_id=user.id,
            query="What are the latest LLM retrieval benchmarks?",
        )
        session.add(research_session)
        session.commit()
        session.refresh(research_session)

        assert research_session.status == ResearchSessionStatus.PENDING


def test_research_session_rejects_invalid_user_id(engine) -> None:
    """ResearchSession should require a valid user_id foreign key."""
    with Session(engine) as session:
        session.add(
            ResearchSession(
                user_id=uuid.uuid4(),
                query="Invalid user reference",
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
