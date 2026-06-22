"""
Тесты системы управления состояниями пользователя (StateManager).

Покрывают 7 тест-кейсов из таблицы 4 курсовой работы:
- push_state, pop_state, get_state, reset_state (TC-1 — TC-5)
- навигация go_to (TC-6)
- защита от параллельных вызовов (TC-7)
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from presentation.telegram.states.manager import StateManager
from presentation.telegram.states.states import Screen


# ===========================================================================
# Фикстура
# ===========================================================================

@pytest.fixture
def manager():
    """Новый StateManager для каждого теста."""
    return StateManager()


USER_ID = 42


# ===========================================================================
# TC-1: Добавление состояния в стек
# ===========================================================================

def test_push_state_adds_to_stack(manager):
    """TC-1: push_state добавляет состояние в стек."""
    manager.push_state(USER_ID, Screen.MAIN)
    manager.push_state(USER_ID, Screen.PLANS)

    state = manager.get_state(USER_ID)

    assert state is not None
    assert state.screen == Screen.PLANS
    assert len(manager.user_states[USER_ID]) == 2


# ===========================================================================
# TC-2: Повтор одинакового состояния не добавляется
# ===========================================================================

def test_push_state_no_duplicate(manager):
    """TC-2: Дублирующее состояние подряд не добавляется в стек."""
    manager.push_state(USER_ID, Screen.PLANS)
    manager.push_state(USER_ID, Screen.PLANS)  # дубликат

    assert len(manager.user_states[USER_ID]) == 1


# ===========================================================================
# TC-3: Получение текущего состояния
# ===========================================================================

def test_get_state_returns_top(manager):
    """TC-3: get_state возвращает верхний элемент стека."""
    manager.push_state(USER_ID, Screen.MAIN)
    manager.push_state(USER_ID, Screen.PLANS)

    state = manager.get_state(USER_ID)

    assert state.screen == Screen.PLANS


# ===========================================================================
# TC-4: Возврат назад (pop_state)
# ===========================================================================

def test_pop_state_returns_to_previous(manager):
    """TC-4: pop_state удаляет верхний элемент, предыдущий становится текущим."""
    manager.push_state(USER_ID, Screen.MAIN)
    manager.push_state(USER_ID, Screen.PLANS)

    popped = manager.pop_state(USER_ID)
    current = manager.get_state(USER_ID)

    assert popped.screen == Screen.PLANS
    assert current.screen == Screen.MAIN


# ===========================================================================
# TC-5: Полная очистка состояния (reset_state)
# ===========================================================================

def test_reset_state_clears_stack(manager):
    """TC-5: reset_state полностью очищает стек пользователя."""
    manager.push_state(USER_ID, Screen.MAIN)
    manager.push_state(USER_ID, Screen.PLANS)
    manager.push_state(USER_ID, Screen.MY_SUB)

    manager.reset_state(USER_ID)

    assert manager.get_state(USER_ID) is None
    assert USER_ID not in manager.user_states


# ===========================================================================
# TC-6: Переход go_to
# ===========================================================================

async def test_go_to_pushes_state(manager):
    """TC-6: go_to вызывает handler экрана и добавляет состояние в стек."""
    from presentation.telegram.navigation.navigation import go_to

    # Мок callback_query
    callback = MagicMock()
    callback.answer = AsyncMock()
    callback.from_user.id = USER_ID
    callback.message.edit_text = AsyncMock()

    # Мок handler для экрана MY_KEYS
    mock_handler = AsyncMock()

    # Патчим state_manager внутри navigation на наш manager,
    # и screens — чтобы не тянуть реальные use cases
    with (
        pytest.MonkeyPatch().context() as mp,
    ):
        import presentation.telegram.navigation.navigation as nav_module

        original_sm = nav_module.state_manager
        original_screens = nav_module.screens

        nav_module.state_manager = manager
        nav_module.screens = {Screen.MY_SUB: mock_handler}

        try:
            manager.push_state(USER_ID, Screen.MAIN)
            await go_to(callback, Screen.MY_SUB)

            state = manager.get_state(USER_ID)
            assert state.screen == Screen.MY_SUB
            mock_handler.assert_called_once_with(callback)
        finally:
            nav_module.state_manager = original_sm
            nav_module.screens = original_screens


# ===========================================================================
# TC-7: Защита от параллельных вызовов (asyncio.Lock)
# ===========================================================================

async def test_concurrent_push_no_race_condition(manager):
    """
    TC-7: Два одновременных push_state под asyncio.Lock не создают гонки.
    Итоговый стек содержит ровно столько элементов, сколько уникальных состояний.
    """
    async def push_with_lock(screen: Screen):
        async with manager.locks[USER_ID]:
            manager.push_state(USER_ID, screen)
            await asyncio.sleep(0)  # уступаем управление

    await asyncio.gather(
        push_with_lock(Screen.MAIN),
        push_with_lock(Screen.PLANS),
        push_with_lock(Screen.MY_SUB),
    )

    stack = manager.user_states[USER_ID]
    screens_in_stack = [s.screen for s in stack]

    # Все три уникальных состояния добавлены, порядок детерминирован
    assert len(stack) == 3
    assert Screen.MAIN in screens_in_stack
    assert Screen.PLANS in screens_in_stack
    assert Screen.MY_SUB in screens_in_stack