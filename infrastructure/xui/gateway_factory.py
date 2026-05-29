import asyncio

from application.ports.vpn.gateway_factory import AbstractVpnGatewayFactory
from application.ports.vpn.gateway import AbstractVpnGateway
from domain.entities.server import Server
import core.config as config
from infrastructure.http.http_client import HttpClient
from infrastructure.xui.gateway import XuiVpnGateway
from infrastructure.xui.api_client import XuiApiClient

class XuiVpnGatewayFactory(AbstractVpnGatewayFactory):
    """
    Реализация фабрики VPN Gateway для XUI.
    Создаёт gateway для конкретного сервера и переиспользует HTTP-клиенты
    для оптимизации сетевых соединений.
    """
    def __init__(self):
        self._lock = asyncio.Lock()
        self._clients: dict[int, HttpClient] = {}

    async def get_gateway(self, server: Server) -> AbstractVpnGateway:
        async with self._lock:
            if server.id is None:
                raise ValueError("Server must have id")

            if server.id not in self._clients:
                client = HttpClient(base_url=server.panel_url, timeout=config.HTTP_TIMEOUT)
                await client.start()
                self._clients[server.id] = client

            http_client = self._clients[server.id]
            xui_client = XuiApiClient(
                http_client=http_client,
                username=server.panel_username,
                password=server.panel_password,
                host=server.host
            )

        return XuiVpnGateway(xui_client=xui_client, inbound_id=server.inbound_id)

    async def close(self) -> None:
        """Закрыть все соединения."""
        for client in self._clients.values():
            await client.close()

        self._clients.clear()