"""
Контейнер зависимостей приложения.

Здесь создаются инфраструктурные зависимости (например VPN gateway).
Это место, где связываются интерфейсы application
и их инфраструктурные реализации.
"""
from application.ports.unit_of_work import AbstractUnitOfWork
from infrastructure.xui.api_client import XuiApiClient
from infrastructure.xui.http_client import XuiHttpClient
from infrastructure.xui.gateway import XuiVpnGateway
from infrastructure.db.database import get_uow as infrastructure_get_uow
import core.config as config


# Singleton Gateway
vpn_gateway: XuiVpnGateway | None = None
xui_http_client: XuiHttpClient | None = None

async def init_vpn_gateway() -> XuiVpnGateway:
    global vpn_gateway, xui_http_client
    if vpn_gateway is None:
        xui_http_client = XuiHttpClient(base_url=config.XUI_BASE_URL, timeout=config.TIMEOUT)
        await xui_http_client.start()
        xui_client = XuiApiClient(
            http_client=xui_http_client,
            username=config.XUI_USERNAME,
            password=config.XUI_PASSWORD,
            host=config.VPN_HOST
        )
        vpn_gateway = XuiVpnGateway(xui_client=xui_client, inbound_name=config.INBOUND_NAME)
    return vpn_gateway

async def close_vpn_gateway():
    global vpn_gateway, xui_http_client
    if xui_http_client:
        await xui_http_client.close()
        xui_http_client = None
    vpn_gateway = None

def get_vpn_gateway() -> XuiVpnGateway:
    """Возвращаем инициализированный объект gateway."""
    if vpn_gateway is None:
        raise RuntimeError("VPN gateway ещё не инициализирован. Сначала вызовите init_vpn_gateway()")
    return vpn_gateway

# Unit of work
def build_uow() -> AbstractUnitOfWork:
    """Создаёт новый UoW с новой сессией."""
    return infrastructure_get_uow()