"""
Функции для навигации между экранами бота.
Содержит универсальные методы перехода на экран (go_to) и возврата назад (go_back),
которые управляют state_manager и вызывают соответствующие функции отображения из screens.py.
"""
from aiogram import types
from aiogram.filters.callback_data import CallbackData

from presentation.telegram.states.manager import state_manager
from presentation.telegram.states.states import Screen
from presentation.telegram.screens.screens import screens

async def go_to(callback_query: types.CallbackQuery, screen: Screen,
                *, data: CallbackData = None, reset: bool = False) -> None:
    """Перейти к определённому состоянию."""
    await callback_query.answer()
    user_id = callback_query.from_user.id

    async with state_manager.locks[user_id]:
        if reset:
            state_manager.reset_state(user_id)

        handler = screens.get(screen)
        if not handler:
            # Можно в будущем логировать
            return

        # Если передаём данные, то запускаем handler, которому нужны данные. Иначе обычный handler
        try:
            if data is not None:
                await handler(callback_query, data)
            else:
                await handler(callback_query)

            state_manager.push_state(user_id, screen, data)
        except Exception:
            # лог
            raise

async def go_back(callback_query: types.CallbackQuery) -> None:
    """Вернуться к прошлому состоянию."""
    await callback_query.answer()
    user_id = callback_query.from_user.id

    async with state_manager.locks[user_id]:
        state_manager.pop_state(user_id)
        prev = state_manager.get_state(user_id)

        if not prev:
            state_manager.push_state(user_id, Screen.MAIN)
            await screens[Screen.MAIN](callback_query)
            return

        if prev.data is not None:
            await screens[prev.screen](callback_query, prev.data)
        else:
            await screens[prev.screen](callback_query)

async def go_back_to(callback_query: types.CallbackQuery, target_screen: Screen,
                     *, answer=None) -> None:
    """Вернуться назад на указанное состояние."""
    user_id = callback_query.from_user.id

    async with state_manager.locks[user_id]:
        await callback_query.answer(answer or "")

        while True:
            state = state_manager.get_state(user_id)

            if not state:
                # стек пуст - возвращаем на главное меню
                await screens[Screen.MAIN](callback_query)
                return

            if state.screen == target_screen:
                # нашли цель
                break

            state_manager.pop_state(user_id)

        if state.data is not None:
            await screens[state.screen](callback_query, state.data)
        else:
            await screens[state.screen](callback_query)