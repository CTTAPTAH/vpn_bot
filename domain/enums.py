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
    PAYMENT_FAILED = "PAYMENT_FAILED"
    PAYMENT_CANCELLED = "PAYMENT_CANCELLED"
    PAYMENT_NOT_FOUND = "PAYMENT_NOT_FOUND"
    ACCESS_GRANTED = "ACCESS_GRANTED"
    ACCESS_REVOKED = "ACCESS_REVOKED"
    XUI_ADD = "XUI_ADD"
    XUI_UPDATE = "XUI_UPDATE"
    XUI_GET = "XUI_GET"
    XUI_DELETE = "XUI_DELETE"
    KEY_CANCELLED = "KEY_CANCELLED"
    KEY_NOT_FOUND_IN_DB = "KEY_NOT_FOUND_IN_DB"
    KEY_NOT_FOUND_IN_VPN = "KEY_NOT_FOUND_IN_VPN"
    KEY_NOT_OWNED_BY_USER = "KEY_NOT_OWNED_BY_USER"
    KEY_LIMIT = "KEY_LIMIT"
    VPN_ERROR = "VPN_ERROR"
    PAYING_OTHER = "PAYING_OTHER"
    ADMIN_ACTION = "ADMIN_ACTION"
    SYSTEM_ERROR = "SYSTEM_ERROR"