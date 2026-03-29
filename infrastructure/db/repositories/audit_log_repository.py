from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.audit_log import AuditLog as DomainAuditLog
from application.ports.repositories.audit_log_repository import AbstractAuditLogRepository
from infrastructure.db.models.audit_log import AuditLog as ORMAuditLog

def to_orm(domain: DomainAuditLog) -> ORMAuditLog:
    return ORMAuditLog(
        level=domain.level,
        event_type=domain.event_type,
        message=domain.message,
        created_at=domain.created_at
    )

class SQLAlchemyAuditLogRepository(AbstractAuditLogRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    # Добавление данных
    async def add(self, audit_log: DomainAuditLog) -> None:
        orm_audit = to_orm(audit_log)
        self._session.add(orm_audit)
        await self._session.flush()

        audit_log.id = orm_audit.id # синхронизируем id