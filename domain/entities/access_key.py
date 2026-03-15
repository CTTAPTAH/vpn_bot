from dataclasses import dataclass, field
from datetime import datetime
from core.utils import utcnow_naive

@dataclass
class AccessKey:
    """Доменная модель ключа доступа.

    Это бизнес-сущность.
    Она не зависит от ORM и базы данных.
    """
    user_id: int
    plan_id: int
    end_at: datetime
    price_at_purchase: int
    id: int | None = None
    start_at: datetime = field(default_factory=utcnow_naive)