from abc import ABC, abstractmethod

from domain.entities.access_key import AccessKey

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
    async def list_by_sub(self, sub_id: int) -> list[AccessKey]:
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