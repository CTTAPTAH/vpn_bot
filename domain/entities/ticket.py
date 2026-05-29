from datetime import datetime
from dataclasses import dataclass, field
from domain.enums import TicketStatus
from core.utils import utcnow

@dataclass
class Ticket:
    """Доменная модель обращения в поддержку.

    Это бизнес-сущность.
    Она не зависит от ORM и базы данных.
    """
    user_id: int
    thread_id: int
    title: str
    status: TicketStatus
    id: int | None = None
    created_at: datetime = field(default_factory=utcnow)
    closed_at: datetime | None = None