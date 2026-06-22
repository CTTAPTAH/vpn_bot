from dataclasses import dataclass, field
from datetime import datetime
from core.utils import utcnow, generate_sub_token

@dataclass
class Subscription:
    """Доменная модель подписки.

    Это бизнес-сущность.
    Она не зависит от ORM и базы данных.
    """
    user_id: int
    plan_id: int
    end_at: datetime
    id: int | None = None
    sub_token: str = field(default_factory=generate_sub_token)
    start_at: datetime = field(default_factory=utcnow)