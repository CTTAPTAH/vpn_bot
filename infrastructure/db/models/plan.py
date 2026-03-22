from sqlalchemy import String, Integer, Boolean, text, Enum, CheckConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.db.base import Base
from domain.enums import PlanType

class Plan(Base):
    """
    ORM-модель тарифа.

    Описывает таблицу `plans` в базе данных.
    Это инфраструктурный слой.
    """
    __tablename__ = "plans"
    __table_args__ = (
        CheckConstraint("duration_seconds >= 0", name="ck_plan_duration_non_negative"),
        CheckConstraint("price >= 0", name="ck_plan_price_non_negative"),
        CheckConstraint("base_price IS NULL OR base_price >= price", name="ck_plan_base_price_valid"),
        Index(
            "uq_plan_trial_once",
            "plan_type",
            unique=True,
            postgresql_where=text("plan_type = 'TRIAL'")
        ),
        Index(
            "uq_plan_vip_once",
            "plan_type",
            unique=True,
            postgresql_where=text("plan_type = 'VIP'")
        )
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        comment="Название тарифа."
    )

    duration_seconds: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Длительность тарифа в секундах."
    )

    price: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Итоговая цена в рублях."
    )

    base_price: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Цена без скидки в рублях."
    )

    plan_type: Mapped[PlanType] = mapped_column(
        Enum(PlanType, native_enum=False),
        nullable=False,
        default=PlanType.PAID,
        index=True,
        comment="Тип тарифа: PAID, TRIAL, VIP."
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        server_default=text("true"),
        nullable=False,
        index=True,
        comment="Активен ли тариф."
    )
