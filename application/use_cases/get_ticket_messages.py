"""Backend-логика для получения последних n сообщений в обращении."""
from dataclasses import dataclass
from datetime import datetime

from application.use_cases.base_use_case import BaseUseCase
from application.ports.unit_of_work import AbstractUnitOfWork
from domain.enums import TicketStatus, MessageSenderType
import core.config as config

@dataclass(slots=True)
class MessagePreview:
    sender: MessageSenderType
    message: str

@dataclass(slots=True)
class GetTicketMessagesResult:
    created_at: datetime
    status: TicketStatus
    messages: list[MessagePreview]

class GetTicketMessages(BaseUseCase):
    def __init__(self, uow: AbstractUnitOfWork):
        self._uow = uow

    async def execute(self, ticket_id: int) -> GetTicketMessagesResult:
        async with self._uow as uow:
            ticket = await uow.tickets.get_by_id(ticket_id)
            messages = await uow.messages.get_all_by_ticket_id(ticket_id, config.MESSAGE_DISPLAY_LIMIT)
            messages = list(reversed(messages))

            return GetTicketMessagesResult(
                created_at=ticket.created_at,
                status=ticket.status,
                messages=[MessagePreview(
                    sender=message.sender_type,
                    message=message.text
                ) for message in messages]
            )