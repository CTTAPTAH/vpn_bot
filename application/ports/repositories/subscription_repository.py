from abc import ABC, abstractmethod

from domain.entities.subscription import Subscription

class AbstractSubscriptionRepository(ABC):
    """
    Контракт репозитория подписки.

    Application слой работает только с этим интерфейсом.
    """
    @abstractmethod
    async def get_by_id(self, sub_id: int) -> Subscription | None:
        ...

    @abstractmethod
    async def get_for_update(self, sub_id: int) -> Subscription | None:
        ...

    @abstractmethod
    async def get_by_user_id(self, user_id: int) -> Subscription | None:
        ...

    @abstractmethod
    async def get_by_token(self, token: str) -> Subscription | None:
        ...

    @abstractmethod
    async def add(self, sub: Subscription) -> None:
        ...

    @abstractmethod
    async def update(self, sub: Subscription) -> None:
        ...