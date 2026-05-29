"""Базовый класс use case, который реализует методы, используемые во всех use_case."""
from application.ports.unit_of_work import AbstractUnitOfWork
from domain.enums import AuditLevel, AuditEventType
from domain.entities.audit_log import AuditLog

class BaseUseCase:
    async def _audit(self, uow: AbstractUnitOfWork, level: AuditLevel, event: AuditEventType, message: str):
        await uow.audits.add(
            AuditLog(
                level=level,
                event_type=event,
                message=message
            )
        )