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
    BACK = "BACK"
    GO_BACK_TO_MENU = "GO_BACK_TO_MENU"
    AGREE = "AGREE"
    CANCEL_PAYMENT = "CANCEL_PAYMENT"
    DELETE_KEY = "DELETE_KEY"