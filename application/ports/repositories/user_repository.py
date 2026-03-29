from abc import ABC, abstractmethod
from domain.entities.user import User

class AbstractUserRepository(ABC):
    """
    Контракт репозитория пользователей.

    Application слой работает только с этим интерфейсом.
    """

    @abstractmethod
    async def get_by_id(self, user_id: int) -> User | None:
        ...

    @abstractmethod
    async def get_by_id_for_update(self, user_id: int) -> User | None:
        ...

    @abstractmethod
    async def get_by_tg_id(self, tg_id: int) -> User | None:
        ...

    @abstractmethod
    async def get_or_create(self, tg_id: int, username: str | None) -> User:
        ...

    @abstractmethod
    async def add(self, user: User) -> None:
        ...

    @abstractmethod
    async def update(self, user: User) -> None:
        ...