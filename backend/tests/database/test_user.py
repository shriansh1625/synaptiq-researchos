"""Tests for the User ORM model."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.base import Base
from app.database.models.user import User


@pytest.fixture
def engine():
    """Provide an in-memory SQLite engine for User model tests."""
    test_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(test_engine)
    yield test_engine
    Base.metadata.drop_all(test_engine)


def test_user_table_has_expected_columns() -> None:
    """User model should define id, email, username, and timestamp fields."""
    table = User.__table__

    assert "id" in table.c
    assert "email" in table.c
    assert "username" in table.c
    assert "created_at" in table.c
    assert "updated_at" in table.c


def test_user_email_and_username_are_unique() -> None:
    """Email and username columns should enforce uniqueness."""
    table = User.__table__

    assert table.c.email.unique is True
    assert table.c.username.unique is True


def test_user_persists_uuid_email_username_and_timestamps(engine) -> None:
    """A valid user should persist with UUID primary key and timestamps."""
    with Session(engine) as session:
        user = User(email="researcher@synaptiq.ai", username="researcher")
        session.add(user)
        session.commit()
        session.refresh(user)

        assert isinstance(user.id, uuid.UUID)
        assert user.email == "researcher@synaptiq.ai"
        assert user.username == "researcher"
        assert user.created_at is not None
        assert user.updated_at is not None

        result = session.scalar(select(User).where(User.id == user.id))
        assert result is not None
        assert result.username == "researcher"


def test_user_rejects_duplicate_email(engine) -> None:
    """Creating two users with the same email should fail."""
    with Session(engine) as session:
        session.add(User(email="dup@synaptiq.ai", username="user_one"))
        session.commit()

        session.add(User(email="dup@synaptiq.ai", username="user_two"))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()


def test_user_rejects_duplicate_username(engine) -> None:
    """Creating two users with the same username should fail."""
    with Session(engine) as session:
        session.add(User(email="one@synaptiq.ai", username="duplicate"))
        session.commit()

        session.add(User(email="two@synaptiq.ai", username="duplicate"))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
