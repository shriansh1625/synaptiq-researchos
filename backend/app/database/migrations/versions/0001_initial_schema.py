"""Initial database schema.

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-09

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create core SynaptiQ ResearchOS tables."""
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("username"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=False)
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=False)

    op.create_table(
        "papers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("abstract", sa.Text(), nullable=False),
        sa.Column("authors", sa.JSON(), nullable=False),
        sa.Column("publication_date", sa.Date(), nullable=True),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=True),
        sa.Column("doi", sa.String(length=255), nullable=True),
        sa.Column(
            "embedding_status",
            sa.String(length=20),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_papers_doi"), "papers", ["doi"], unique=False)
    op.create_index(op.f("ix_papers_title"), "papers", ["title"], unique=False)

    op.create_table(
        "research_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_research_sessions_user_id"),
        "research_sessions",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "executive_reports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("recommendations", sa.JSON(), nullable=False),
        sa.Column("citations", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["session_id"], ["research_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_executive_reports_session_id"),
        "executive_reports",
        ["session_id"],
        unique=False,
    )

    op.create_table(
        "agent_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("agent_name", sa.String(length=50), nullable=False),
        sa.Column("input_data", sa.JSON(), nullable=False),
        sa.Column("output_data", sa.JSON(), nullable=False),
        sa.Column("latency", sa.Integer(), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["session_id"], ["research_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_agent_logs_agent_name"), "agent_logs", ["agent_name"], unique=False)
    op.create_index(
        op.f("ix_agent_logs_session_id"),
        "agent_logs",
        ["session_id"],
        unique=False,
    )
    op.create_index(op.f("ix_agent_logs_timestamp"), "agent_logs", ["timestamp"], unique=False)


def downgrade() -> None:
    """Drop core SynaptiQ ResearchOS tables."""
    op.drop_index(op.f("ix_agent_logs_timestamp"), table_name="agent_logs")
    op.drop_index(op.f("ix_agent_logs_session_id"), table_name="agent_logs")
    op.drop_index(op.f("ix_agent_logs_agent_name"), table_name="agent_logs")
    op.drop_table("agent_logs")

    op.drop_index(op.f("ix_executive_reports_session_id"), table_name="executive_reports")
    op.drop_table("executive_reports")

    op.drop_index(op.f("ix_research_sessions_user_id"), table_name="research_sessions")
    op.drop_table("research_sessions")

    op.drop_index(op.f("ix_papers_title"), table_name="papers")
    op.drop_index(op.f("ix_papers_doi"), table_name="papers")
    op.drop_table("papers")

    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
