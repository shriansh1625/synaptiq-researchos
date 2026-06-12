"""Repository for research session lifecycle."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.research_session import ResearchSession, ResearchSessionStatus
from app.database.models.user import User


class ResearchSessionRepository:
    """CRUD operations for research sessions."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create_demo_user(self) -> User:
        stmt = select(User).where(User.username == "demo")
        user = await self._session.scalar(stmt)
        if user is not None:
            return user
        user = User(email="demo@synaptiq.ai", username="demo")
        self._session.add(user)
        await self._session.flush()
        return user

    async def create(self, *, user_id: uuid.UUID, query: str) -> ResearchSession:
        research_session = ResearchSession(
            user_id=user_id,
            query=query,
            status=ResearchSessionStatus.PENDING,
        )
        self._session.add(research_session)
        await self._session.flush()
        return research_session

    async def get_by_id(self, session_id: uuid.UUID) -> ResearchSession | None:
        return await self._session.get(ResearchSession, session_id)

    async def update_status(
        self,
        session_id: uuid.UUID,
        status: ResearchSessionStatus,
    ) -> ResearchSession | None:
        research_session = await self.get_by_id(session_id)
        if research_session is None:
            return None
        research_session.status = status
        await self._session.flush()
        return research_session
