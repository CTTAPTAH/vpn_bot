from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.audit_log import AuditLog as DomainAuditLog
from application.ports.repositories.audit_log_repository import AbstractAuditLogRepository
from infrastructure.db.models.audit_log import AuditLog as ORMAuditLog

class SQLAlchemyAuditLogRepository(AbstractAuditLogRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    # Добавление данных
    async def add(self, audit_log: DomainAuditLog) -> None:
        orm_audit = ORMAuditLog(
            level=audit_log.level,
            event_type=audit_log.event_type,
            message=audit_log.message,
            created_at=audit_log.created_at
        )
        self._session.add(orm_audit)
        await self._session.flush()

        audit_log.id = orm_audit.id # синхронизируем id