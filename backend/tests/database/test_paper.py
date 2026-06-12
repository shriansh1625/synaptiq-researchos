"""Tests for the Paper ORM model."""

from __future__ import annotations

import uuid
from datetime import date

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.database.base import Base
from app.database.models.paper import EmbeddingStatus, Paper


@pytest.fixture
def engine():
    """Provide an in-memory SQLite engine for Paper model tests."""
    test_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(test_engine)
    yield test_engine
    Base.metadata.drop_all(test_engine)


def test_paper_table_has_expected_columns() -> None:
    """Paper model should define all required fields."""
    table = Paper.__table__
    column_names = set(table.c.keys())

    assert {
        "id",
        "title",
        "abstract",
        "authors",
        "publication_date",
        "source",
        "url",
        "doi",
        "embedding_status",
        "created_at",
        "updated_at",
    }.issubset(column_names)


def test_paper_has_indexes_on_title_and_doi() -> None:
    """Title and DOI columns should be indexed."""
    table = Paper.__table__

    assert table.c.title.index is True
    assert table.c.doi.index is True


def test_paper_persists_fields_and_timestamps(engine) -> None:
    """A valid paper should persist all fields with UUID and timestamps."""
    with Session(engine) as session:
        paper = Paper(
            title="Intermittent Fasting and Insulin Sensitivity",
            abstract="A review of metabolic outcomes under time-restricted eating.",
            authors=["A. Rao", "K. Lin"],
            publication_date=date(2024, 3, 15),
            source="semantic_scholar",
            url="https://example.com/paper/1",
            doi="10.1000/synaptiq.2024.001",
            embedding_status=EmbeddingStatus.PENDING,
        )
        session.add(paper)
        session.commit()
        session.refresh(paper)

        assert isinstance(paper.id, uuid.UUID)
        assert paper.title.startswith("Intermittent Fasting")
        assert paper.authors == ["A. Rao", "K. Lin"]
        assert paper.publication_date == date(2024, 3, 15)
        assert paper.source == "semantic_scholar"
        assert paper.url == "https://example.com/paper/1"
        assert paper.doi == "10.1000/synaptiq.2024.001"
        assert paper.embedding_status == EmbeddingStatus.PENDING
        assert paper.created_at is not None
        assert paper.updated_at is not None

        result = session.scalar(select(Paper).where(Paper.id == paper.id))
        assert result is not None
        assert result.doi == "10.1000/synaptiq.2024.001"


def test_paper_defaults_embedding_status_to_pending(engine) -> None:
    """New papers should default embedding_status to pending."""
    with Session(engine) as session:
        paper = Paper(
            title="Default Embedding Status",
            abstract="Abstract text.",
            authors=["Author"],
            source="arxiv",
        )
        session.add(paper)
        session.commit()
        session.refresh(paper)

        assert paper.embedding_status == EmbeddingStatus.PENDING
