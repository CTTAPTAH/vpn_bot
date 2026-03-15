from datetime import datetime

from sqlalchemy import Integer, DateTime, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.db.base import Base

class AccessKey(Base):
    """
    ORM-модель ключа доступа.

    Описывает таблицу `access_keys` в базе данных.
    Это инфраструктурный слой.
    """
    __tablename__ = "access_keys"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
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

    start_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        nullable=False,
        comment="Дата получение подписки пользователем."
    )

    end_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        index=True,
        comment="Дата окончания подписки пользователя."
    )

    price_at_purchase: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Сумма, за которую приобрели подписку."
    )
