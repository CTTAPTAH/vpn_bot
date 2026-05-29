from abc import ABC, abstractmethod
from domain.entities.message import Message

class AbstractMessageRepository(ABC):
    """
    Контракт репозитория сообщения в поддержку.

    Application слой работает только с этим интерфейсом.
    """

    @abstractmethod
    async def get_by_id(self, message_id: int) -> Message | None:
        ...

    @abstractmethod
    async def get_all_by_ticket_id(self, ticket_id, limit: int) -> list[Message]:
        ...

    @abstractmethod
    async def add(self, message: Message) -> None:
        ...

    @abstractmethod
    async def update(self, message: Message) -> None:
        ...