from datetime import datetime

from sqlalchemy import Integer, DateTime, func, ForeignKey, Enum, Index, text, Text
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.db.base import Base
from domain.enums import TicketStatus

class Ticket(Base):
    """
    ORM-модель обращения в поддержку.

    Описывает таблицу `tickets` в базе данных.
    Это инфраструктурный слой.
    """
    __tablename__ = "tickets"

    __table_args__ = (
        Index(
            "uq_ticket_user_single_open",
            "user_id",
            unique=True,
            postgresql_where=text("status = 'OPEN'")
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        comment="Уникальный идентификатор обращения в поддержку (PK)."
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="id пользователя, который отправил это обращение."
    )

    thread_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
        unique=True,
        comment="id топика в группе админов."
    )

    title: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Первые символы первого сообщения. Используется как превью в списке обращений."
    )

    status: Mapped[TicketStatus] = mapped_column(
        Enum(TicketStatus, native_enum=False),
        nullable=False,
        comment="Статус обращения: открыт, закрыт"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
        comment="Время создания обращения."
    )

    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Время закрытия обращения."
    )