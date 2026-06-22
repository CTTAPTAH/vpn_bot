"""
Навигационные состояния (экраны) бота.

Каждое значение Screen:
- используется как callback_data
- определяет текущий экран
- используется для выбора UI (text + keyboard)

Screen — единый источник правды для навигации.
"""

from enum import StrEnum

class Screen(StrEnum):
    # ===== Система =====
    KEY_LIMIT_REACHED = "key_limit_reached"

    # ===== Главное меню =====
    MAIN = "main"

    # Тарифы, покупка
    PLANS = "plans"
    PURCHASE_PENDING = "purchase_pending"
    PURCHASE_SUCCESS = "purchase_success"
    PURCHASE_CANCELED = "purchase_canceled"

    # Пробный период
    TRIAL = "trial"
    
    # Мои ключи
    MY_SUB = "my_sub"
    
    # ===== Инструкции =====
    INSTRUCTION = "instruction"

    # Телефон
    PHONE = "phone"
    # Iphone
    IPHONE = "iphone"
    PROBLEM_IPHONE = "problem_iphone"
    # Android
    ANDROID = "android"
    PROBLEM_ANDROID = "problem_android"
    # Huawei
    HUAWEI = "huawei"
    PROBLEM_HUAWEI = "problem_huawei"

    # ПК
    COMPUTER = "computer"
    PROBLEM_COMPUTER = "problem_computer"

    # Телевизор
    TV = "tv"
    # Apple TV
    APPLE_TV = "apple_tv"
    PROBLEM_APPLE_TV = "problem_apple_tv"
    # Android TV
    ANDROID_TV = "android_tv"
    PROBLEM_ANDROID_TV = "problem_android_tv"
