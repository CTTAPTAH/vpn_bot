"""
Http Integration Exceptions

Исключения, специфичные для интеграции с Http API.

Эти ошибки используются внутри infrastructure слоя.
Gateway может преобразовывать их в портовые ошибки
(application layer).
"""

class HttpError(Exception):
    """Базовая ошибка интеграции с Http."""
    pass


class HttpConnectionError(HttpError):
    """Не удалось установить соединение с Http."""
    pass


class HttpTimeoutError(HttpError):
    """Таймаут запроса к Http API."""
    pass