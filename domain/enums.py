"""
В файле хранятся enum классы.
"""
from enum import StrEnum

# Тариф
class PlanType(StrEnum):
    PAID = "PAID"
    TRIAL = "TRIAL"
    VIP = "VIP"

# Платежи
class PaymentStatus(StrEnum):
    """Статус платежа."""
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    PROCESSING = "PROCESSING"

class PaymentType(StrEnum):
    """Тип платежа."""
    PURCHASE = "PURCHASE"
    TRIAL = "TRIAL"

class PaymentAction(StrEnum):
    """Тип действия над ключом."""
    CREATE = "CREATE"
    RENEW = "RENEW"

class PaymentProvider(StrEnum):
    """Провайдер платежа"""
    YOUMONEY = "YOUMONEY"
    INTERNAL = "INTERNAL"

# Аудит логирование
class AuditLevel(StrEnum):
    """Аудит бота."""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"

class AuditEventType(StrEnum):
    """Тип действия, который записывается в аудит."""
    # Платёж
    PAYMENT_CREATED = "PAYMENT_CREATED"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    PAYMENT_CANCELLED = "PAYMENT_CANCELLED"
    PAYMENT_COMPLETED = "PAYMENT_COMPLETED"
    PAYMENT_NOT_FOUND = "PAYMENT_NOT_FOUND"
    PAYMENT_NOT_OWNED_BY_USER = "PAYMENT_NOT_OWNED_BY_USER"

    # Выдача доступа
    ACCESS_GRANTED = "ACCESS_GRANTED"
    ACCESS_REVOKED = "ACCESS_REVOKED"
    VPN_KEY_CREATED = "VPN_KEY_CREATED"
    VPN_KEY_UPDATED = "VPN_KEY_UPDATED"
    VPN_KEY_FETCHED = "VPN_KEY_FETCHED"
    VPN_KEY_DELETED = "VPN_KEY_DELETED"
    TRIAL_ALREADY_GRANTED = "TRIAL_ALREADY_GRANTED"
    TRIAL_GRANTED = "TRIAL_GRANTED"

    # Ключ
    KEY_CANCELLED = "KEY_CANCELLED"
    KEY_NOT_FOUND_IN_DB = "KEY_NOT_FOUND_IN_DB"
    KEY_NOT_FOUND_IN_VPN = "KEY_NOT_FOUND_IN_VPN"
    KEY_NOT_OWNED_BY_USER = "KEY_NOT_OWNED_BY_USER"
    KEY_LIMIT = "KEY_LIMIT"

    # Тариф
    PLAN_NOT_FOUND = "PLAN_NOT_FOUND"

    # Общие
    PAYING_OTHER = "PAYING_OTHER"
    ADMIN_ACTION = "ADMIN_ACTION"
    DB_ERROR = "DB_ERROR"
    VPN_ERROR = "VPN_ERROR"
    PAYMENT_PROVIDER_ERROR = "PAYMENT_PROVIDER_ERROR"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"
    SYSTEM_ERROR = "SYSTEM_ERROR"