"""Tests for the AgentLog ORM model."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.base import Base
from app.database.models.agent_log import AgentLog
from app.database.models.research_session import ResearchSession
from app.database.models.user import User


@pytest.fixture
def engine():
    """Provide an in-memory SQLite engine with foreign keys enabled."""
    test_engine = create_engine("sqlite:///:memory:")

    @event.listens_for(test_engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(test_engine)
    yield test_engine
    Base.metadata.drop_all(test_engine)


@pytest.fixture
def research_session(engine) -> ResearchSession:
    """Create a user and research session for agent log tests."""
    with Session(engine) as session:
        user = User(email="ops@synaptiq.ai", username="ops")
        session.add(user)
        session.commit()
        session.refresh(user)

        research_session = ResearchSession(
            user_id=user.id,
            query="Analyze contradictions in fasting literature.",
        )
        session.add(research_session)
        session.commit()
        session.refresh(research_session)

    return research_session


def test_agent_log_table_has_expected_columns() -> None:
    """AgentLog should define all required fields."""
    table = AgentLog.__table__
    column_names = set(table.c.keys())

    assert {
        "id",
        "session_id",
        "agent_name",
        "input_data",
        "output_data",
        "latency",
        "confidence_score",
        "status",
        "timestamp",
    }.issubset(column_names)


def test_agent_log_has_indexes_on_agent_name_and_timestamp() -> None:
    """agent_name and timestamp columns should be indexed."""
    table = AgentLog.__table__

    assert table.c.agent_name.index is True
    assert table.c.timestamp.index is True


def test_agent_log_persists_with_research_session_relationship(
    engine,
    research_session: ResearchSession,
) -> None:
    """AgentLog should persist all fields and relate to its research session."""
    with Session(engine) as session:
        log = AgentLog(
            session_id=research_session.id,
            agent_name="verification",
            input_data={"claims_count": 12},
            output_data={"verified_count": 10, "unsupported_ratio": 0.08},
            latency=842,
            confidence_score=0.87,
            status="success",
        )
        session.add(log)
        session.commit()
        session.refresh(log)

        assert isinstance(log.id, uuid.UUID)
        assert log.session_id == research_session.id
        assert log.agent_name == "verification"
        assert log.input_data["claims_count"] == 12
        assert log.output_data["verified_count"] == 10
        assert log.latency == 842
        assert log.confidence_score == 0.87
        assert log.status == "success"
        assert log.timestamp is not None

        loaded = session.scalar(select(AgentLog).where(AgentLog.id == log.id))
        assert loaded is not None
        assert loaded.research_session.id == research_session.id


def test_agent_log_rejects_invalid_session_id(engine) -> None:
    """AgentLog should require a valid session_id foreign key."""
    with Session(engine) as session:
        session.add(
            AgentLog(
                session_id=uuid.uuid4(),
                agent_name="discovery",
                input_data={},
                output_data={},
                latency=100,
                confidence_score=None,
                status="error",
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
