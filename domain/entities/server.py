from dataclasses import dataclass, field
from datetime import datetime
from core.utils import utcnow

@dataclass
class Server:
    """Доменная модель ключа доступа.

    Это бизнес-сущность.
    Она не зависит от ORM и базы данных.
    """
    name: str
    panel_url: str
    panel_username: str
    panel_password: str
    host: str
    inbound_id: int
    default_key_name: str
    id: int | None = None
    inbound_name: str | None = None
    is_active: bool = True
    created_at: datetime = field(default_factory=utcnow)