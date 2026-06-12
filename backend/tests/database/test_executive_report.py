"""Tests for the ExecutiveReport ORM model."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.base import Base
from app.database.models.executive_report import ExecutiveReport
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
    """Create a user and research session for report tests."""
    with Session(engine) as session:
        user = User(email="analyst@synaptiq.ai", username="analyst")
        session.add(user)
        session.commit()
        session.refresh(user)

        research_session = ResearchSession(
            user_id=user.id,
            query="Does intermittent fasting improve insulin sensitivity?",
        )
        session.add(research_session)
        session.commit()
        session.refresh(research_session)

    return research_session


def test_executive_report_table_has_expected_columns() -> None:
    """ExecutiveReport should define all required fields."""
    table = ExecutiveReport.__table__
    column_names = set(table.c.keys())

    assert {
        "id",
        "session_id",
        "summary",
        "recommendations",
        "citations",
        "created_at",
    }.issubset(column_names)
    assert "updated_at" not in column_names


def test_executive_report_session_id_foreign_key() -> None:
    """session_id should reference research_sessions.id."""
    table = ExecutiveReport.__table__
    foreign_keys = {fk.target_fullname for fk in table.c.session_id.foreign_keys}

    assert "research_sessions.id" in foreign_keys


def test_executive_report_persists_with_research_session_relationship(
    engine,
    research_session: ResearchSession,
) -> None:
    """ExecutiveReport should persist and relate to its research session."""
    recommendations = [
        {"text": "Run an RCT in adults over 65.", "citations": ["gap_01"]},
    ]
    citations = [
        {"claim_id": "clm_0001", "paper_id": "ss:rao21", "span_ids": ["sp_12"]},
    ]

    with Session(engine) as session:
        report = ExecutiveReport(
            session_id=research_session.id,
            summary="Evidence on intermittent fasting and insulin sensitivity is mixed.",
            recommendations=recommendations,
            citations=citations,
        )
        session.add(report)
        session.commit()
        session.refresh(report)

        assert isinstance(report.id, uuid.UUID)
        assert report.session_id == research_session.id
        assert report.summary.startswith("Evidence on intermittent fasting")
        assert report.recommendations == recommendations
        assert report.citations == citations
        assert report.created_at is not None

        loaded = session.scalar(select(ExecutiveReport).where(ExecutiveReport.id == report.id))
        assert loaded is not None
        assert loaded.research_session.id == research_session.id
        assert loaded.research_session.query.startswith("Does intermittent fasting")


def test_executive_report_rejects_invalid_session_id(engine) -> None:
    """ExecutiveReport should require a valid session_id foreign key."""
    with Session(engine) as session:
        session.add(
            ExecutiveReport(
                session_id=uuid.uuid4(),
                summary="Summary without a valid session.",
                recommendations=[],
                citations=[],
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
