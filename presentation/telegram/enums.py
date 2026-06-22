"""
Enum-классы слоя представления (бота).

Содержат пользовательские действия и режимы интерфейса.
Не относятся к бизнес-логике и не должны использоваться в domain-слое.
"""

from enum import StrEnum

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

class Platform(StrEnum):
    IPHONE = "iphone"
    ANDROID = "android"
    HUAWEI = "huawei"
    APPLE_TV = "apple_tv"
    ANDROID_TV = "android_tv"
    COMPUTER = "computer"