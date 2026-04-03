"""
AbstractUnitOfWork

Абстракция (контракт) для паттерна Unit of Work.

Определяет:
- какие репозитории доступны
- какие методы управления транзакцией существуют

Application-слой должен зависеть только от этой абстракции,
а не от конкретной реализации (например, SQLAlchemy).

Реализация находится в infrastructure.
"""

from abc import ABC, abstractmethod
from application.ports.repositories.access_key_repository import AbstractAccessKeyRepository
from application.ports.repositories.audit_log_repository import AbstractAuditLogRepository
from application.ports.repositories.message_repository import AbstractMessageRepository
from application.ports.repositories.payment_repository import AbstractPaymentRepository
from application.ports.repositories.plan_repository import AbstractPlanRepository
from application.ports.repositories.server_repository import AbstractServerRepository
from application.ports.repositories.ticket_repository import AbstractTicketRepository
from application.ports.repositories.user_repository import AbstractUserRepository

class AbstractUnitOfWork(ABC):
    """
    Абстрактный Unit of Work.

    Определяет контракт для управления транзакцией
    и доступа к репозиториям.
    """

    # Репозитории (будут определены в реализации)
    users: AbstractUserRepository
    plans: AbstractPlanRepository
    keys: AbstractAccessKeyRepository
    payments: AbstractPaymentRepository
    servers: AbstractServerRepository
    audits: AbstractAuditLogRepository
    tickets: AbstractTicketRepository
    messages: AbstractMessageRepository

    @abstractmethod
    async def __aenter__(self)  -> "AbstractUnitOfWork":
        """Вход в контекст транзакции. Должен возвращать self."""
        return self

    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Выход из контекста транзакции. Конкретная логика реализуется в infrastructure."""
        pass

    @abstractmethod
    async def commit(self):
        """Фиксация изменений в БД."""
        raise NotImplementedError

    @abstractmethod
    async def rollback(self):
        """Откат транзакции."""
        raise NotImplementedError