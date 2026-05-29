"""Backend-логика для закрытия обращения."""
from dataclasses import dataclass
from enum import StrEnum

from application.use_cases.base_use_case import BaseUseCase
from application.ports.unit_of_work import AbstractUnitOfWork
from domain.enums import TicketStatus
from core.utils import utcnow

class CloseTicketResultErrorType(StrEnum):
    """Тип ошибки."""
    TICKET_NOT_FOUND = "TICKET_NOT_FOUND"

@dataclass(slots=True)
class CloseTicketResult:
    success: bool
    tg_id: int | None = None
    error: CloseTicketResultErrorType | None = None

class CloseTicket(BaseUseCase):
    def __init__(self, uow: AbstractUnitOfWork):
        self._uow = uow

    async def execute(self, thread_id: int) -> CloseTicketResult:
        async with self._uow as uow:
            ticket = await uow.tickets.get_by_thread_id(thread_id)
            if ticket is None:
                return CloseTicketResult(success=False, error=CloseTicketResultErrorType.TICKET_NOT_FOUND)

            ticket.status = TicketStatus.CLOSED
            ticket.closed_at = utcnow()
            await uow.tickets.update(ticket)

            user = await uow.users.get_by_id(ticket.user_id)
            return CloseTicketResult(success=True, tg_id=user.tg_id)