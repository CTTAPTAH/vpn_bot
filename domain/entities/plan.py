from dataclasses import dataclass
from domain.enums import PlanType

@dataclass
class Plan:
    """Доменная модель тарифа.

    Это бизнес-сущность.
    Она не зависит от ORM и базы данных.
    """
    name: str
    duration_seconds: int
    price: int
    id: int | None = None
    base_price: int | None = None
    plan_type: PlanType = PlanType.PAID
    is_active: bool = True