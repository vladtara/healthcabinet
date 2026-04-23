"""Processing module dependency injection."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db as _core_get_db


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """DB session dependency — delegates to core get_db."""
    async for session in _core_get_db():
        yield session
