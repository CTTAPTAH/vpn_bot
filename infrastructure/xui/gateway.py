"""
Infrastructure реализация VpnGateway через XUI API.

Этот класс:
- адаптирует XuiApiClient к интерфейсу VpnGateway
- маппит инфраструктурные модели в DTO (VpnKey)
- не содержит бизнес-логики
- не принимает решений (создавать / продлевать / удалять)

Application слой ничего не знает про XUI.
"""

from datetime import datetime

from application.ports.vpn_gateway import VpnGateway, VpnKey
from infrastructure.xui.api_client import XuiApiClient
from infrastructure.xui.models import Client as XuiClient
from core.utils import datetime_to_ms, ms_to_datetime

class XuiVpnGateway(VpnGateway):
    """
    Адаптер XUI API к VpnGateway.

    Этот класс:
    - Преобразует XUI-модель в VpnKey
    - Изолирует Application слой от особенностей XUI
    """
    def __init__(self, xui_client: XuiApiClient, inbound_name: str) -> None:
        self._xui = xui_client
        self._inbound_name = inbound_name

    async def create_key(self, email: str, expires_at: datetime | None) -> VpnKey:
        """Создаёт ключ в XUI."""
        expiry_ms = datetime_to_ms(expires_at)

        await self._xui.add_client(
            inbound_name=self._inbound_name,
            email=email,
            expiry_time=expiry_ms,
            enable=True
        )

        return await self.get_key(email)

    async def update_expiry(self, email: str, new_expires_at: datetime) -> None:
        """Обновляет дату истечения ключа."""
        expiry_ms = datetime_to_ms(new_expires_at)

        await self._xui.update_client(
            email=email,
            inbound_name=self._inbound_name,
            expiry_time=expiry_ms
        )

    async def disable_key(self, email: str) -> None:
        """Деактивирует ключ (не удаляет)."""
        await self._xui.update_client(
            email=email,
            inbound_name=self._inbound_name,
            enabled=False
        )

    async def enable_key(self, email: str) -> None:
        """Активирует ключ (не удаляет)."""
        await self._xui.update_client(
            email=email,
            inbound_name=self._inbound_name,
            enabled=True
        )

    async def delete_key(self, email: str) -> None:
        """Полностью удаляет ключ из XUI."""
        await self._xui.delete_client(
            email=email,
            inbound_name=self._inbound_name
        )

    async def is_client_exists(self, email: str) -> bool:
        """Проверяет, есть ли клиент в inbound'е."""
        return await self._xui.is_client_exists(email, self._inbound_name)

    async def get_key(self, email: str) -> VpnKey | None:
        """Возвращает состояние ключа."""
        client = await self._xui.find_client(
            email=email,
            inbound_name=self._inbound_name
        )

        if client is None:
            return None

        return self._map_to_dto(client)

    async def get_link(self, email: str) -> str:
        """Возвращает VLESS ссылку для клиента."""
        return await self._xui.get_client_link(
            email=email,
            inbound_name=self._inbound_name
        )

    # Приватный метод
    def _map_to_dto(self, client: XuiClient) -> VpnKey:
        """Преобразует XUI-модель клиента в DTO VpnKey."""
        expires_at = ms_to_datetime(client.expiry_time)

        return VpnKey(
            email=client.email,
            expires_at=expires_at,
            is_active=client.enabled,
        )