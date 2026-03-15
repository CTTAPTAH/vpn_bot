"""
Async HTTP client for XUI integration.

Этот модуль:
- инкапсулирует работу с httpx
- управляет сессией
- нормализует сетевые ошибки
- проверяет HTTP-статусы

Не содержит бизнес-логики XUI.
"""

from typing import Any

import httpx

from infrastructure.xui.exceptions import (
    XuiConnectionError,
    XuiTimeoutError,
    XuiRequestError,
)

class XuiHttpClient:
    """
    Низкоуровневый HTTP-клиент для работы с XUI API.

    Отвечает только за транспортный уровень.
    """

    def __init__(self, base_url: str, timeout: float = 10) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def start(self):
        """Инициализация клиента."""
        if self._client is None:
            self._client = httpx.AsyncClient(base_url=self._base_url, timeout=self._timeout, verify=False)

    async def close(self):
        """Закрытие клиента."""
        if self._client:
            await self._client.aclose()
            self._client = None

    # Вспомогательные методы
    def _ensure_client(self) -> httpx.AsyncClient:
        if not self._client:
            raise RuntimeError("HTTP client is not initialized")
        return self._client

    # Публичные методы
    async def get(self, url: str, *, params: dict[str, Any] | None = None) -> httpx.Response:
        client = self._ensure_client()

        try:
            response = await client.get(url, params=params)
        except httpx.TimeoutException as exc:
            raise XuiTimeoutError("Request timeout") from exc
        except httpx.ConnectError as exc:
            raise XuiConnectionError("Connection failed") from exc

        return response

    async def post(
            self,
            url: str,
            *,
            json: dict[str, Any] | None = None,
            data: dict[str, Any] | None = None
    ) -> httpx.Response:
        client = self._ensure_client()

        try:
            response = await client.post(url, json=json, data=data)
        except httpx.TimeoutException as exc:
            raise XuiTimeoutError("Request timeout") from exc
        except httpx.ConnectError as exc:
            raise XuiConnectionError("Connection failed") from exc

        return response