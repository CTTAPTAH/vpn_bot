from abc import ABC, abstractmethod
from domain.entities.audit_log import AuditLog

class AbstractAuditLogRepository(ABC):
    """
    Контракт репозитория аудит логирования.

    Application слой работает только с этим интерфейсом.
    """
    @abstractmethod
    async def add(self, audit_log: AuditLog) -> None:
        ...