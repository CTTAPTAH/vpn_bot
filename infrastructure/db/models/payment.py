from datetime import datetime

from sqlalchemy import Integer, String, DateTime, ForeignKey, Enum, UniqueConstraint, text, Index, func
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.db.base import Base
from domain.enums import PaymentStatus, PaymentType, PaymentProvider, PaymentAction

class Payment(Base):
    """
    ORM-модель платежа.

    Описывает таблицу `payments` в базе данных.
    Это инфраструктурный слой.
    """
    __tablename__ = "payments"

    __table_args__ = (
        UniqueConstraint(
            "provider",
            "provider_payment_id",
            name="uq_provider_payment_id"
        ),
        Index(
            "uq_user_trial_once",
            "user_id",
            unique=True,
            postgresql_where=text("type = 'TRIAL'")
        )
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Пользователь, совершивший платеж"
    )

    plan_id: Mapped[int] = mapped_column(
        ForeignKey("plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Тариф, за который был произведён платеж"
    )

    key_id: Mapped[int | None] = mapped_column(
        ForeignKey("access_keys.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Связь с подпиской/ключом, который был выдан по этому платежу"
    )

    price: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Сумма платежа"
    )

    type: Mapped[PaymentType] = mapped_column(
        Enum(PaymentType, native_enum=False),
        nullable=False,
        index=True,
        comment="Тип платежа (покупка, пробный период)"
    )

    action: Mapped[PaymentAction] = mapped_column(
        Enum(PaymentAction, native_enum=False),
        nullable=False,
        index=True,
        comment="Тип действия над ключом: создание, продление"
    )

    provider: Mapped[PaymentProvider] = mapped_column(
        Enum(PaymentProvider, native_enum=False),
        nullable=False,
        comment="Платёжный провайдер (например, YooMoney, Qiwi, Telegram)"
    )

    provider_payment_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="ID платежа у провайдера"
    )

    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, native_enum=False),
        nullable=False,
        index=True,
        default=PaymentStatus.PENDING,
        comment="Статус платежа: pending, completed, failed"
    )

    granted_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        comment="Время выдачи доступа пользователю. Null, если доступ ещё не выдан"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
        index=True,
        comment="Время создания записи платежа"
    )

    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        comment="Время подтверждённого платежа"
    )