from collections.abc import AsyncGenerator
from importlib import import_module

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.ENVIRONMENT == "development",
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


def import_orm_models() -> None:
    """Import ORM model modules so Base.metadata contains every mapped table."""
    for module_name in (
        "app.admin.models",
        "app.ai.models",
        "app.auth.models",
        "app.billing.models",
        "app.documents.models",
        "app.health_data.models",
        "app.users.models",
    ):
        import_module(module_name)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
