from dataclasses import dataclass, field
from datetime import datetime
from core.utils import utcnow
from domain.enums import PaymentStatus, PaymentType, PaymentProvider, PaymentAction, PaymentMethod

@dataclass
class Payment:
    """Доменная модель платежа.

    Это бизнес-сущность.
    Она не зависит от ORM и базы данных.
    """
    user_id: int
    plan_id: int
    price: int
    type: PaymentType
    action: PaymentAction
    provider: PaymentProvider
    provider_payment_id: str
    status: PaymentStatus = PaymentStatus.PENDING
    created_at: datetime = field(default_factory=utcnow)
    id: int | None = None
    key_id: int | None = None
    payment_method: PaymentMethod | None = None
    payment_url: str | None = None
    granted_at: datetime | None = None
    paid_at: datetime | None = None