"""
Enum-классы слоя представления (бота).

Содержат пользовательские действия и режимы интерфейса.
Не относятся к бизнес-логике и не должны использоваться в domain-слое.
"""

from enum import StrEnum

# Бот
class Action(StrEnum):
    """
    Действия бота.
    Например: действие "BACK" - вернуться назад (на прошлое состояние)
    """
    BACK = "back"
    GO_BACK_TO_MENU = "go_back_to_menu"
    CANCEL_PAYMENT = "cancel_payment"
    DELETE_KEY = "delete_key"