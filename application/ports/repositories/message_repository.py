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
    async def get_by_telegram_message_id(self, telegram_message_id) -> Message | None:
        ...

    @abstractmethod
    async def add(self, message: Message) -> None:
        ...

    @abstractmethod
    async def update(self, message: Message) -> None:
        ...