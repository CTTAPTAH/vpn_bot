"""
SQLAlchemyUnitOfWork

Реализация паттерна Unit of Work для работы с БД через SQLAlchemy.

Отвечает за:
- создание и закрытие сессии
- управление транзакцией (commit / rollback)
- предоставление репозиториев в рамках одной транзакции

Используется в application-слое через абстракцию UoW.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker

from application.ports.unit_of_work import AbstractUnitOfWork
from infrastructure.db.repositories.access_key_repository import SQLAlchemyAccessKeyRepository
from infrastructure.db.repositories.audit_log_repository import SQLAlchemyAuditLogRepository
from infrastructure.db.repositories.payment_repository import SQLAlchemyPaymentRepository
from infrastructure.db.repositories.plan_repository import SQLAlchemyPlanRepository
from infrastructure.db.repositories.user_repository import SQLAlchemyUserRepository

from application.ports.repositories.access_key_repository import AbstractAccessKeyRepository
from application.ports.repositories.audit_log_repository import AbstractAuditLogRepository
from application.ports.repositories.payment_repository import AbstractPaymentRepository
from application.ports.repositories.plan_repository import AbstractPlanRepository
from application.ports.repositories.user_repository import AbstractUserRepository

class SQLAlchemyUnitOfWork(AbstractUnitOfWork):
    """Конкретная реализация Unit of Work для SQLAlchemy."""
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory
        self.session: AsyncSession | None = None

        # Репозитории (будут созданы при входе в контекст)
        self.users: AbstractUserRepository | None = None
        self.plans: AbstractPlanRepository | None = None
        self.keys: AbstractAccessKeyRepository | None = None
        self.payments: AbstractPaymentRepository | None = None
        self.audits: AbstractAuditLogRepository | None = None

    async def __aenter__(self):
        self.session = self._session_factory()

        # Создаём репозитории один раз на транзакцию
        self.users = SQLAlchemyUserRepository(self.session)
        self.plans = SQLAlchemyPlanRepository(self.session)
        self.keys = SQLAlchemyAccessKeyRepository(self.session)
        self.payments = SQLAlchemyPaymentRepository(self.session)
        self.audits = SQLAlchemyAuditLogRepository(self.session)

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type:
                await self.rollback()
            else:
                await self.commit()
        finally:
            if self.session is not None:
                await self.session.close()

    async def commit(self):
        """Фиксирует изменения в БД."""
        if self.session is None:
            raise RuntimeError("Session is not initialized")
        await self.session.commit()

    async def rollback(self):
        """Откатывает транзакцию."""
        if self.session is None:
            raise RuntimeError("Session is not initialized")
        await self.session.rollback()