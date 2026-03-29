from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from domain.entities.access_key import AccessKey

@dataclass
class AccessKeyView:
    """
    Информация, которая нужна для отображения пользователю.
    Например, в обычной абстрактной модели нет plan_name,
    а его нужно знать для отображения.
    """
    id: int
    plan_name: str
    end_at: datetime
    vless_link: str

@dataclass
class ServerKeysLoad:
    """Количество ключей на каждом сервере и лимит по ключам на сервере."""
    server_id: int
    keys_count: int
    max_clients: int

class AbstractAccessKeyRepository(ABC):
    """
    Контракт репозитория ключа доступа.

    Application слой работает только с этим интерфейсом.
    """
    @abstractmethod
    async def get_by_id(self, access_key_id: int) -> AccessKey | None:
        ...

    @abstractmethod
    async def get_for_update(self, key_id: int) -> AccessKey | None:
        ...

    @abstractmethod
    async def get_view_by_id(self, access_key_id: int) -> AccessKeyView | None:
        ...

    @abstractmethod
    async def list_by_user(self, user_id: int) -> list[AccessKey]:
        ...

    @abstractmethod
    async def list_view_by_user(self, user_id: int) -> list[AccessKeyView]:
        ...

    @abstractmethod
    async def count_all_keys(self, user_id: int) -> int:
        ...

    @abstractmethod
    async def count_active_keys(self, user_id: int, now: datetime) -> int:
        ...

    @abstractmethod
    async def get_servers_keys_load(self, server_ids: list[int]) -> list[ServerKeysLoad]:
        ...

    @abstractmethod
    async def add(self, access_key: AccessKey) -> None:
        ...

    @abstractmethod
    async def update(self, access_key: AccessKey) -> None:
        ...

    @abstractmethod
    async def delete(self, access_key_id: int) -> None:
        ...