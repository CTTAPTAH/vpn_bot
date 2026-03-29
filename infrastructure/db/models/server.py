from datetime import datetime

from sqlalchemy import Integer, DateTime, Boolean, text, func, String, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.db.base import Base

class Server(Base):
    """
    ORM-модель сервера.

    Описывает таблицу `servers` в базе данных.
    Это инфраструктурный слой.
    """
    __tablename__ = "servers"
    __table_args__ = (
        CheckConstraint("max_clients > 0", name="ck_servers_price_positive"),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    name: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        unique=True,
        comment="Название сервера."
    )

    panel_url: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Ссылка на панель сервера."
    )

    panel_username: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Логин от панели сервера."
    )

    panel_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Пароль от панели сервера."
    )

    host: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="host панели сервера."
    )

    inbound_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="id inbound, в котором хранятся ключи."
    )

    inbound_name: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Название inbound, в котором хранятся ключи. Не является источником истины."
    )

    default_key_name: Mapped[str] = mapped_column(
        String(50),
        nullable=True,
        comment="Название ключа по умолчанию."
    )

    max_clients: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Лимит на количество ключей на сервере."
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        server_default=text("true"),
        nullable=False,
        index=True,
        comment="Активен ли сервер."
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
        comment="Время создания сервера в базе данных."
    )