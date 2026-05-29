"""
Контейнер зависимостей приложения.

Здесь создаются инфраструктурные зависимости (например VPN gateway).
Это место, где связываются интерфейсы application
и их инфраструктурные реализации.
"""
from application.ports.unit_of_work import AbstractUnitOfWork
from application.ports.vpn.gateway_factory import AbstractVpnGatewayFactory
import core.config as config
from infrastructure.db.database import get_uow as infrastructure_get_uow
from infrastructure.xui.gateway_factory import XuiVpnGatewayFactory
from infrastructure.payments.platega.client import PlategaClient
from infrastructure.http.http_client import HttpClient

# VPN gateway factory
gateway_factory = XuiVpnGatewayFactory()
def get_vpn_gateway_factory() -> AbstractVpnGatewayFactory:
    """Возвращает фабрику gateway vpn."""
    return gateway_factory

# Platega client
platega_client: PlategaClient | None = None
async def get_platega_client() -> PlategaClient:
    global platega_client

    if platega_client is None:
        http = HttpClient(config.PLATEGA_BASE_URL, config.HTTP_TIMEOUT)
        client = PlategaClient(http)
        await client.start()
        platega_client = client

    return platega_client

async def close_platega_client():
    global platega_client
    if platega_client is not None:
        await platega_client.close()

# Unit of work
def build_uow() -> AbstractUnitOfWork:
    """Создаёт новый UoW с новой сессией."""
    return infrastructure_get_uow()