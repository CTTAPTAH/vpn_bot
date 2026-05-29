from dataclasses import dataclass

@dataclass
class PaymentUiState:
    """
    Связь платежа с Telegram UI (сообщение пользователя),
    используемая для обновления интерфейса после webhook.

    Это бизнес-сущность.
    Она не зависит от ORM и базы данных.
    """
    payment_id: int
    tg_user_id: int
    tg_chat_id: int
    tg_message_id: int
    id: int | None = None