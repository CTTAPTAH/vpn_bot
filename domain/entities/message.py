from datetime import datetime
from dataclasses import dataclass, field
from domain.enums import MessageSenderType
from core.utils import utcnow

@dataclass
class Message:
    """Доменная модель сообщения в поддержку.

    Это бизнес-сущность.
    Она не зависит от ORM и базы данных.
    """
    ticket_id: int
    sender_type: MessageSenderType
    text: str
    telegram_message_id: int
    id: int | None = None
    created_at: datetime = field(default_factory=utcnow)