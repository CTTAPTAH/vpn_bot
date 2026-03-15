from dataclasses import dataclass, field
from datetime import datetime
from core.utils import utcnow_naive
from domain.enums import AuditLevel, AuditEventType

@dataclass
class AuditLog:
    """Доменная модель аудит логирования.

    Это бизнес-сущность.
    Она не зависит от ORM и базы данных.
    """
    level: AuditLevel
    event_type: AuditEventType
    message: str
    created_at: datetime = field(default_factory=utcnow_naive)
    id: int | None = None
    context: dict | None = None