from datetime import datetime

from sqlalchemy import Integer, DateTime, func, ForeignKey, CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.db.base import Base

class Subscription(Base):
    """
    ORM-модель подписки.

    Описывает таблицу `subscriptions` в базе данных.
    Это инфраструктурный слой.
    """
    __tablename__ = "subscriptions"
    __table_args__ = (
        CheckConstraint("end_at >= start_at", name="ck_subscriptions_end_after_start"),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
        comment="id пользователя, у которого есть эта подписка."
    )

    plan_id: Mapped[int] = mapped_column(
        ForeignKey("plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="id тарифа, на который подписался пользователь."
    )

    sub_token: Mapped[str] = mapped_column(
        String(32),
        unique=True,
        nullable=False,
        index=True,
        comment="Уникальный токен для subscription URL."
    )

    start_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Дата получение подписки пользователем."
    )

    end_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="Дата окончания подписки пользователя."
    )