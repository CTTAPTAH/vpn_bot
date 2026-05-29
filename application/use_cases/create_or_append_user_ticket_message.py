"""Backend-логика для создания или добавления сообщения в обращение."""
from dataclasses import dataclass
from enum import StrEnum
from sqlalchemy.exc import IntegrityError

from application.use_cases.base_use_case import BaseUseCase
from application.ports.unit_of_work import AbstractUnitOfWork
from domain.entities.ticket import Ticket
from domain.entities.message import Message
from domain.enums import AuditLevel, AuditEventType, TicketStatus, MessageSenderType
import core.config as config

class CreateOrAppendUserTicketMessageErrorType(StrEnum):
    """Тип ошибки во время отправки сообщения."""
    TICKET_NOT_FOUND = "TICKET_NOT_FOUND"

@dataclass(slots=True)
class CreateOrAppendUserTicketMessageResult:
    success: bool
    thread_id: int | None = None
    error: CreateOrAppendUserTicketMessageErrorType | None = None

class CreateOrAppendUserTicketMessage(BaseUseCase):
    """Сценарий создания или добавления сообщения в обращение."""
    def __init__(self, uow: AbstractUnitOfWork):
        self._uow = uow

    async def execute(self, tg_id: int, username: str, text: str,
                      thread_id: int) -> CreateOrAppendUserTicketMessageResult:
        async with self._uow as uow:
            user = await uow.users.get_or_create(tg_id, username)
            ticket = await uow.tickets.get_open_by_user_id(user.id)

            if ticket is None:
                try:
                    ticket = Ticket(
                        user_id=user.id,
                        thread_id=thread_id,
                        title=text[:config.TICKET_TITLE_LENGTH],
                        status=TicketStatus.OPEN
                    )
                    await uow.tickets.add(ticket)
                except IntegrityError:
                    ticket = await uow.tickets.get_open_by_user_id(user.id)
                    if ticket is None:
                        await self._audit(
                            uow,
                            AuditLevel.ERROR,
                            AuditEventType.TICKET_NOT_FOUND,
                            f"[CreateOrAppendUserTicketMessage][execute]\n"
                            f"Открытый тикет не найден в БД. Также не получилось создать тикет и найти его же.\n"
                            f"tg_id={tg_id}, user_id={user.id}."
                        )
                        return CreateOrAppendUserTicketMessageResult(
                            success=False,
                            error=CreateOrAppendUserTicketMessageErrorType.TICKET_NOT_FOUND
                        )

            message = Message(
                ticket_id=ticket.id,
                sender_type=MessageSenderType.USER,
                text=text
            )
            await uow.messages.add(message)

            return CreateOrAppendUserTicketMessageResult(success=True)