"""
Управление навигационными состояниями пользователя.

Использует стек экранов для каждого пользователя,
что позволяет реализовать универсальную кнопку "Назад"
без жёсткой привязки к конкретным хендлерам.

push_state(user_id, state) – добавить состояние
pop_state(user_id) – удалить последнее состояние
get_state(user_id) – получить текущее состояние

user_states = {} # id пользователя: стек состояния экрана
"""
from dataclasses import dataclass
from typing import Any
import asyncio
from collections import defaultdict

from presentation.telegram.states.states import Screen

@dataclass
class NavState:
    """Информация о состоянии."""
    screen: Screen
    data: Any | None = None

class StateManager:
    """Менеджер состояний. Состояния хранятся в списке, а логика работы реализована как стек."""
    def __init__(self):
        self.user_states: defaultdict[int, list[NavState]] = defaultdict(list)
        # Защита от параллельного выполнения handler'ов
        self.locks: defaultdict[int, asyncio.Lock] = defaultdict(asyncio.Lock)

    def push_state(self, user_id: int, screen: Screen, data: Any | None = None):
        stack = self.user_states[user_id]
        # Защита от повторения подряд состояний в стеке
        if stack:
            last = stack[-1]
            if last.screen == screen and last.data == data:
                # Можно логировать
                return

        stack.append(NavState(screen, data))

    def pop_state(self, user_id: int) -> NavState | None:
        stack = self.user_states.get(user_id, [])
        if stack:
            return stack.pop()
        return None

    def get_state(self, user_id: int) -> NavState | None:
        stack = self.user_states.get(user_id, [])
        return stack[-1] if stack else None

    def reset_state(self, user_id: int):
        self.user_states.pop(user_id, None)

state_manager = StateManager()