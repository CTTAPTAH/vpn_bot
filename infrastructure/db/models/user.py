from datetime import datetime

from sqlalchemy import String, Integer, DateTime, Boolean, BigInteger, func, text
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.db.base import Base

class User(Base):
    """
    ORM-модель пользователя.

    Описывает таблицу `users` в базе данных.
    Это инфраструктурный слой.
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        comment="Уникальный идентификатор пользователя (PK)."
    )

    tg_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        nullable=False,
        index=True,
        comment="Telegram ID пользователя (уникальный)."
    )

    username: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Username пользователя в Telegram (может отсутствовать)."
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        nullable=False,
        comment="Дата и время (UTC) регистрации пользователя."
    )

    is_blocked: Mapped[bool] = mapped_column(
        Boolean,
        server_default=text("false"),
        nullable=False,
        index=True,
        comment="Флаг блокировки пользователя."
    )