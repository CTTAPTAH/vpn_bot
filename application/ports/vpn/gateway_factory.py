"""
Контракт фабрики для создания VPN Gateway на основе конфигурации сервера.

Используется в application-слое для получения gateway без знания
конкретной реализации (например XUI).
"""
from abc import ABC, abstractmethod
from domain.entities.server import Server
from application.ports.vpn.gateway import AbstractVpnGateway

class AbstractVpnGatewayFactory(ABC):
    @abstractmethod
    async def get_gateway(self, server: Server) -> AbstractVpnGateway:
        ...

    @abstractmethod
    async def close(self) -> None:
        ...