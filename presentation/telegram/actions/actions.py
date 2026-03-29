"""
Действия пользователя для Telegram-слоя презентации.

Функции этого модуля выполняют конкретные операции (use case) и
возвращают текст уведомления для пользователя (alerts).

Действия не управляют навигацией и не рисуют экраны.
Они только выполняют задачу и возвращают результат,
который потом используется хендлерами или навигацией.

Типичный поток:
handler -> action -> navigation -> screen
"""
from aiogram import types

from app.container import build_uow, get_vpn_gateway_factory
from application.use_cases.cancel_payment import CancelPaymentUseCase
from application.use_cases.delete_key import DeleteKeyUseCase
import presentation.telegram.callbacks.callbacks as callbacks
import presentation.telegram.texts.alerts as alerts

async def cancel_payment(callback_query: types.CallbackQuery, callback_data: callbacks.CancelPaymentCallback) -> str:
    """Отменяет платёж и возвращает answer."""
    use_case = CancelPaymentUseCase(build_uow())
    result = await use_case.execute(callback_query.from_user.id,callback_query.from_user.username)

    if result.success:
        return alerts.PAYMENT_CANCELED
    else:
        return alerts.ERROR

async def delete_key(callback_query: types.CallbackQuery, callback_data: callbacks.DeleteKeyCallback) -> str:
    """Удаляет ключ и возвращает answer."""
    use_case = DeleteKeyUseCase(build_uow(), get_vpn_gateway_factory())
    result = await use_case.execute(callback_query.from_user.id, callback_data.key_id)

    if result.success:
        return alerts.KEY_DELETED
    else:
        return alerts.ERROR