"""
В файле хранятся enum классы.
"""
from enum import StrEnum, IntEnum

# Тариф
class PlanType(StrEnum):
    PAID = "PAID"
    TRIAL = "TRIAL"
    VIP = "VIP"

# Платежи
class PaymentStatus(StrEnum):
    """Статус платежа."""
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED "
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

class PaymentMethod(IntEnum):
    """Номер способа оплаты."""
    SBPQR = 2
    ERIP = 3
    CARD_ACQUIRING = 11
    INTERNATIONAL_PAYMENT = 12
    CRYPTOCURRENCY = 13

class PaymentProvider(StrEnum):
    """Провайдер платежа"""
    PLATEGA = "PLATEGA"
    INTERNAL = "INTERNAL"

# Аудит логирование
class AuditLevel(StrEnum):
    """Аудит бота."""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"

# Обращение в поддержку
class TicketStatus(StrEnum):
    """Статус обращения пользователя в БД."""
    OPEN = "OPEN"
    CLOSED = "CLOSED"

# Сообщение в поддержку
class MessageSenderType(StrEnum):
    """Отправитель сообщения."""
    SUPPORT = "SUPPORT"
    USER = "USER"

class AuditEventType(StrEnum):
    """Тип действия, который записывается в аудит."""
    # Платёж
    PAYMENT_CREATED = "PAYMENT_CREATED"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    PAYMENT_CANCELLED = "PAYMENT_CANCELLED"
    PAYMENT_COMPLETED = "PAYMENT_COMPLETED"
    PAYMENT_NOT_FOUND = "PAYMENT_NOT_FOUND"
    PAYMENT_UI_NOT_FOUND = "PAYMENT_UI_NOT_FOUND"
    PAYMENT_NOT_OWNED_BY_USER = "PAYMENT_NOT_OWNED_BY_USER"
    EMPTY_PAYMENT_LINK = "EMPTY_PAYMENT_LINK"

    # Выдача доступа
    ACCESS_GRANTED = "ACCESS_GRANTED"
    ACCESS_REVOKED = "ACCESS_REVOKED"
    VPN_KEY_CREATED = "VPN_KEY_CREATED"
    VPN_KEY_UPDATED = "VPN_KEY_UPDATED"
    VPN_KEY_FETCHED = "VPN_KEY_FETCHED"
    VPN_KEY_DELETED = "VPN_KEY_DELETED"
    TRIAL_ALREADY_GRANTED = "TRIAL_ALREADY_GRANTED"
    TRIAL_GRANTED = "TRIAL_GRANTED"
    NO_AVAILABLE_SERVERS = "NO_AVAILABLE_SERVERS"
    SERVER_NOT_FOUND = "SERVER_NOT_FOUND"
    IS_PROCESSING = "IS_PROCESSING"

    # Поддержка
    USER_NOT_FOUND = "USER_NOT_FOUND"
    MESSAGE_NOT_FOUND = "MESSAGE_NOT_FOUND"
    TICKET_NOT_FOUND = "TICKET_NOT_FOUND"

    # Подписка
    SUB_NOT_FOUND_IN_DB = "SUB_NOT_FOUND_IN_DB"

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