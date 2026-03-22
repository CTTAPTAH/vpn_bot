"""
Вспомогательные функции для удобства программирования.
"""
from datetime import datetime, UTC, timedelta
from uuid import uuid4

SECONDS_IN_MONTH = 30 * 24 * 60 * 60
SECONDS_IN_DAY = 24 * 60 * 60

def utcnow() -> datetime:
    """Текущее время UTC."""
    return datetime.now(UTC)

def add_seconds_to_now(seconds: int) -> datetime:
    """Добавить секунды к текущему времени."""
    return utcnow() + timedelta(seconds=seconds)

def months_from_seconds(seconds: int) -> int:
    """Перевод секунд в месяца"""
    return max(1, seconds // SECONDS_IN_MONTH)

def days_from_seconds(seconds: int) -> int:
    """Перевод секунд в дни"""
    return max(1, seconds // SECONDS_IN_DAY)

def datetime_to_ms(dt: datetime) -> int:
    """Переводит время типа datetime в мс."""
    return int(dt.timestamp() * 1000)

def ms_to_datetime(ms: int) -> datetime:
    """Переводит мс в datetime."""
    return datetime.fromtimestamp(ms / 1000)

def new_uuid() -> str:
    """Генерирует uuid."""
    return str(uuid4())