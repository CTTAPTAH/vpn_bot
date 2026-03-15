from dataclasses import dataclass, field
from datetime import datetime
from core.utils import utcnow_naive

@dataclass
class User:
    """Доменная модель пользователя.

    Это бизнес-сущность.
    Она не зависит от ORM и базы данных.
    """
    tg_id: int
    username: str | None
    id: int | None = None
    created_at: datetime = field(default_factory=utcnow_naive)
    is_blocked: bool = False