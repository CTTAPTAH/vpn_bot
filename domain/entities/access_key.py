from dataclasses import dataclass, field
from datetime import datetime
from core.utils import utcnow

@dataclass
class AccessKey:
    """Доменная модель ключа доступа.

    Это бизнес-сущность.
    Она не зависит от ORM и базы данных.
    """
    user_id: int
    plan_id: int
    end_at: datetime
    id: int | None = None
    start_at: datetime = field(default_factory=utcnow)
    vless_link: str | None = None