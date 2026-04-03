from abc import ABC, abstractmethod
from domain.entities.ticket import Ticket

class AbstractTicketRepository(ABC):
    """
    Контракт репозитория обращения в поддержку.

    Application слой работает только с этим интерфейсом.
    """

    @abstractmethod
    async def get_by_id(self, ticket_id: int) -> Ticket | None:
        ...

    @abstractmethod
    async def get_open_by_user_id(self, user_id: int) -> Ticket | None:
        ...

    @abstractmethod
    async def add(self, ticket: Ticket) -> None:
        ...

    @abstractmethod
    async def update(self, ticket: Ticket) -> None:
        ...