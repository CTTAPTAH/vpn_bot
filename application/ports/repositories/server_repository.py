from abc import ABC, abstractmethod

from domain.entities.server import Server

class AbstractServerRepository(ABC):
    """
    Контракт репозитория сервера.

    Application слой работает только с этим интерфейсом.
    """
    @abstractmethod
    async def get_by_id(self, server_id: int) -> Server | None:
        ...

    @abstractmethod
    async def get_active_servers(self) -> list[Server]:
        ...

    @abstractmethod
    async def get_by_ids(self, server_ids: list[int]) -> list[Server]:
        ...

    @abstractmethod
    async def add(self, server: Server) -> None:
        ...

    @abstractmethod
    async def update(self, server: Server) -> None:
        ...