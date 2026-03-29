"""
Контейнер зависимостей приложения.

Здесь создаются инфраструктурные зависимости (например VPN gateway).
Это место, где связываются интерфейсы application
и их инфраструктурные реализации.
"""
from application.ports.unit_of_work import AbstractUnitOfWork
from application.ports.vpn.gateway_factory import AbstractVpnGatewayFactory
from infrastructure.db.database import get_uow as infrastructure_get_uow
from infrastructure.xui.gateway_factory import XuiVpnGatewayFactory

gateway_factory = XuiVpnGatewayFactory()
def get_vpn_gateway_factory() -> AbstractVpnGatewayFactory:
    """Возвращает фабрику gateway vpn."""
    return gateway_factory

# Unit of work
def build_uow() -> AbstractUnitOfWork:
    """Создаёт новый UoW с новой сессией."""
    return infrastructure_get_uow()