from datetime import datetime

from sqlalchemy import String, Integer, DateTime, func, Enum
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.db.base import Base
from domain.enums import AuditLevel, AuditEventType

class AuditLog(Base):
    """
    ORM-модель пользователя.

    Описывает таблицу `audit_logs` в базе данных.
    Это инфраструктурный слой.
    """
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    level: Mapped[AuditLevel] = mapped_column(
        Enum(AuditLevel, native_enum=False),
        nullable=False,
        index=True,
        comment="Уровень лога: INFO, WARNING, ERROR."
    )

    event_type: Mapped[AuditEventType] = mapped_column(
        Enum(AuditEventType, native_enum=False),
        nullable=False,
        index=True,
        comment="Тип бизнес-события (PAYMENT_COMPLETED, ACCESS_GRANTED и т.д.)."
    )

    message: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Основное сообщение лога."
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
        comment="Дата и время создания лога."
    )
