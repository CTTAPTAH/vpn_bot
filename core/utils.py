"""
Вспомогательные функции для удобства программирования.
"""
from datetime import datetime, UTC, timedelta

SECONDS_IN_MONTH = 30 * 24 * 60 * 60
SECONDS_IN_DAY = 24 * 60 * 60

def utcnow_naive() -> datetime:
    """Текущее время UTC без tzinfo. Используется для PostgreSQL TIMESTAMP WITHOUT TIME ZONE."""
    return datetime.now(UTC).replace(tzinfo=None)

def add_seconds_to_now_naive(seconds: int) -> datetime:
    """Добавить секунды к текущему времени."""
    return utcnow_naive() + timedelta(seconds=seconds)

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