from datetime import datetime

from sqlalchemy import Integer, DateTime, func, ForeignKey, Enum, Text, Index
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.db.base import Base
from domain.enums import MessageSenderType

class Message(Base):
    """
    ORM-модель сообщения в поддержку.

    Описывает таблицу `messages` в базе данных.
    Это инфраструктурный слой.
    """
    __tablename__ = "messages"
    __table_args__ = (
        Index("ix_messages_ticket_created", "ticket_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        comment="Уникальный идентификатор сообщения в поддержку (PK)."
    )

    ticket_id: Mapped[int] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="id обращения в поддержку."
    )

    sender_type: Mapped[MessageSenderType] = mapped_column(
        Enum(MessageSenderType, native_enum=False),
        nullable=False,
        comment="Отправитель сообщения: SUPPORT, USER."
    )

    text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Сообщение отправителя."
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
        comment="Время создания сообщения."
    )