from sqlalchemy import Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.db.base import Base

class PaymentUiState(Base):
    """
    Связь платежа с Telegram UI (сообщение пользователя),
    используемая для обновления интерфейса после webhook.

    Описывает таблицу `payment_ui_state` в базе данных.

    Это инфраструктурный слой.
    """
    __tablename__ = "payment_ui_state"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    payment_id: Mapped[int] = mapped_column(
        ForeignKey("payments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        unique=True,
        comment="Ссылка на платеж, для которого сохраняется Telegram UI-сообщение."
    )

    tg_user_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Telegram id пользователя."
    )

    tg_chat_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="ID чата пользователя в Telegram, где было отправлено сообщение с оплатой."
    )

    tg_message_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="ID сообщения в Telegram, которое должно быть обновлено после изменения статуса платежа."
    )