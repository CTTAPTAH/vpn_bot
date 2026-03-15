"""
VPN Gateway Port

Этот модуль определяет порт (интерфейс) взаимодействия с внешней VPN-системой (например, XUI).

Application слой зависит только от этого интерфейса.
Infrastructure реализует его конкретной интеграцией (XUI API).

Важно:
- здесь нет бизнес-логики
- здесь нет ORM
- здесь только контракт
- реализация может быть заменена без изменения use cases
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

@dataclass
class VpnKey:
    """DTO, описывающий состояние ключа в VPN-системе."""
    email: str
    expires_at: datetime | None
    is_active: bool

class VpnGateway(ABC):
    """
    Порт взаимодействия с VPN-системой.

    Application слой работает только через этот интерфейс.
    Реализация (например, XuiVpnGateway) находится в infrastructure.

    Gateway должен быть "тупым":
    - не содержит бизнес-логики
    - не решает, продлевать или создавать заново
    - просто выполняет команды
    """
    @abstractmethod
    async def create_key(self, email: str, expires_at: datetime | None) -> VpnKey:
        ...

    @abstractmethod
    async def update_expiry(self, email: str, new_expires_at: datetime) -> None:
        ...

    @abstractmethod
    async def disable_key(self, email: str) -> None:
        ...

    @abstractmethod
    async def enable_key(self, email: str) -> None:
        ...

    @abstractmethod
    async def delete_key(self, email: str) -> None:
        ...

    @abstractmethod
    async def is_client_exists(self, email: str) -> bool:
        ...

    @abstractmethod
    async def get_key(self, email: str) -> VpnKey | None:
        ...

    @abstractmethod
    async def get_link(self, email: str) -> str:
        ...