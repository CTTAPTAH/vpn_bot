"""
Настройка подключения к базе данных.

Создаёт:
- async engine (соединение с PostgreSQL)
- фабрику асинхронных сессий
- фабрику Unit of Work
"""

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from core.config import DATABASE_URL
from infrastructure.db.unit_of_work import SQLAlchemyUnitOfWork

# Engine
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
)

# Фабрика сессий
session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine,
    expire_on_commit=False,
)

# Фабрика UoW
def get_uow() -> SQLAlchemyUnitOfWork:
    return SQLAlchemyUnitOfWork(session_factory)

async def close_engine():
    """При остановке бота корректно закрываем пул соединений."""
    await engine.dispose()