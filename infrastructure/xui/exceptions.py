"""
Xui Integration Exceptions

Исключения, специфичные для интеграции с Xui API.

Эти ошибки используются внутри infrastructure слоя.
Gateway может преобразовывать их в портовые ошибки
(application layer).
"""

class XuiError(Exception):
    """Базовая ошибка интеграции с Http."""
    pass

class XuiAuthenticationError(XuiError):
    """Ошибка авторизации (неверный логин/куки/токен)."""
    pass


class XuiRequestError(XuiError):
    """Xui вернул Xui ошибку (4xx / 5xx)."""

    def __init__(self, status_code: int, message: str | None = None):
        self.status_code = status_code
        super().__init__(message or f"Xui request failed with status {status_code}")


class XuiInvalidResponseError(XuiError):
    """Xui вернул неожиданный или некорректный ответ."""
    pass


class XuiClientNotFoundError(XuiError):
    """Клиент с указанным email не найден в Xui."""
    pass


class XuiClientAlreadyExistsError(XuiError):
    """Попытка создать клиента, который уже существует."""
    pass