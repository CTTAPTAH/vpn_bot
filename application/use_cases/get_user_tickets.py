"""Backend-логика для получения последних n обращений."""
from dataclasses import dataclass
from datetime import datetime

from application.use_cases.base_use_case import BaseUseCase
from application.ports.unit_of_work import AbstractUnitOfWork
from domain.enums import TicketStatus
import core.config as config

@dataclass(slots=True)
class TicketPreview:
    ticket_id: int
    status: TicketStatus
    preview_text: str
    created_at: datetime

@dataclass(slots=True)
class GetUserTicketsResult:
    tickets: list[TicketPreview]

class GetUserTickets(BaseUseCase):
    def __init__(self, uow: AbstractUnitOfWork):
        self._uow = uow

    async def execute(self, tg_id: int, username: str) -> GetUserTicketsResult:
        async with self._uow as uow:
            user = await uow.users.get_or_create(tg_id, username)
            domain_tickets = await uow.tickets.get_latest(user.id, config.TICKET_DISPLAY_LIMIT)

            preview_tickets = [TicketPreview(
                ticket_id=ticket.id,
                status=ticket.status,
                preview_text=ticket.title,
                created_at=ticket.created_at
            ) for ticket in domain_tickets]

            return GetUserTicketsResult(tickets=preview_tickets)