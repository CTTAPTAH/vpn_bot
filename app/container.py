"""
Контейнер зависимостей приложения.

Здесь создаются инфраструктурные зависимости (например VPN gateway).
Это место, где связываются интерфейсы application
и их инфраструктурные реализации.
"""
import asyncio
import logging

from application.ports.unit_of_work import AbstractUnitOfWork
from infrastructure.xui.api_client import XuiApiClient
from infrastructure.xui.http_client import XuiHttpClient
from infrastructure.xui.gateway import XuiVpnGateway
from infrastructure.db.database import get_uow as infrastructure_get_uow
import core.config as config

logger = logging.getLogger(__name__)

# Singleton Gateway
vpn_gateway: XuiVpnGateway | None = None
xui_http_client: XuiHttpClient | None = None
_init_lock = asyncio.Lock() # Для безопасной инициализации

async def init_vpn_gateway() -> XuiVpnGateway:
    """Инициализация VPN Gateway (singleton). Защищено lock для конкурентной безопасности."""
    global vpn_gateway, xui_http_client

    if vpn_gateway is not None:
        return vpn_gateway

    async with _init_lock:
        logger.info("Инициализация XUI HTTP client...")
        xui_http_client = XuiHttpClient(base_url=config.XUI_BASE_URL, timeout=config.HTTP_TIMEOUT)
        await xui_http_client.start()

        logger.info("Инициализация XUI API client...")
        xui_client = XuiApiClient(
            http_client=xui_http_client,
            username=config.XUI_USERNAME,
            password=config.XUI_PASSWORD,
            host=config.VPN_HOST
        )

        logger.info("Создание VPN Gateway...")
        vpn_gateway = XuiVpnGateway(xui_client=xui_client, inbound_name=config.INBOUND_NAME)
        logger.info("VPN Gateway успешно инициализирован.")
    return vpn_gateway

async def close_vpn_gateway():
    """Закрывает VPN Gateway и HTTP client."""
    global vpn_gateway, xui_http_client

    if xui_http_client:
        try:
            logger.info("Закрытие XUI HTTP client...")
            await xui_http_client.close()
        except Exception as e:
            logger.error("Ошибка при закрытии XUI HTTP client: %s", e)
        finally:
            xui_http_client = None

    vpn_gateway = None
    logger.info("VPN Gateway закрыт.")

def get_vpn_gateway() -> XuiVpnGateway:
    """Возвращаем инициализированный объект gateway."""
    if vpn_gateway is None:
        raise RuntimeError("VPN gateway ещё не инициализирован. Сначала вызовите init_vpn_gateway()")
    return vpn_gateway

# Unit of work
def build_uow() -> AbstractUnitOfWork:
    """Создаёт новый UoW с новой сессией."""
    return infrastructure_get_uow()