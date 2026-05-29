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
    EXTEND_TRIAL = "extend_trial"
    
    # Мои ключи
    MY_KEYS = "my_keys"
    SELECTED_KEY = "selected_key"
    
    # ===== Инструкции =====
    INSTRUCTION = "instruction"

    # APPLE
    APPLE = "apple"
    PROBLEMS_APPLE = "problems_apple"
    NO_CONNECTION_APPLE = "no_connection_apple"
    SECOND_METHOD_APPLE = "second_method_apple"
    
    # ANDROID
    ANDROID = "android"
    PROBLEMS_ANDROID = "problems_android"
    NO_CONNECTION_ANDROID = "no_connection_android"
    SECOND_METHOD_ANDROID = "second_method_android"
    
    # WINDOWS
    WINDOWS = "windows"
    PC_APPS = "pc_apps"
    
    # TV
    TV = "tv"
    ANDROID_TV = "android_tv"
    APPLE_TV = "apple_tv"
    
    # HUAWEI
    HUAWEI = "huawei"
    SECOND_METHOD_HUAWEI = "second_method_huawei"