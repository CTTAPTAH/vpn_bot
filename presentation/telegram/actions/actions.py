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

from app.container import build_uow
from application.use_cases.accept_user_agreement import AcceptUserAgreementUseCase

async def agreement_with_policy(callback_query: types.CallbackQuery) -> None:
    use_case = AcceptUserAgreementUseCase(build_uow())
    await use_case.execute(callback_query.from_user.id, callback_query.from_user.username)