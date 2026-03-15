"""
XUI Integration Exceptions

Исключения, специфичные для интеграции с XUI API.

Эти ошибки используются внутри infrastructure слоя.
Gateway может преобразовывать их в портовые ошибки
(application layer).
"""

class XuiError(Exception):
    """Базовая ошибка интеграции с XUI."""
    pass


class XuiConnectionError(XuiError):
    """Не удалось установить соединение с XUI."""
    pass


class XuiTimeoutError(XuiError):
    """Таймаут запроса к XUI API."""
    pass


class XuiAuthenticationError(XuiError):
    """Ошибка авторизации (неверный логин/куки/токен)."""
    pass


class XuiRequestError(XuiError):
    """XUI вернул HTTP ошибку (4xx / 5xx)."""

    def __init__(self, status_code: int, message: str | None = None):
        self.status_code = status_code
        super().__init__(message or f"XUI request failed with status {status_code}")


class XuiInvalidResponseError(XuiError):
    """XUI вернул неожиданный или некорректный ответ."""
    pass


class XuiClientNotFoundError(XuiError):
    """Клиент с указанным email не найден в XUI."""
    pass


class XuiClientAlreadyExistsError(XuiError):
    """Попытка создать клиента, который уже существует."""
    pass