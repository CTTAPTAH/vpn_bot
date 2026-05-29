"""Backend-логика для отправки сообщения админа пользователю."""
from dataclasses import dataclass
from enum import StrEnum

from application.use_cases.base_use_case import BaseUseCase
from application.ports.unit_of_work import AbstractUnitOfWork
from domain.entities.message import Message
from domain.enums import AuditLevel, AuditEventType, MessageSenderType

class AdminReplyToTicketErrorType(StrEnum):
    """Тип ошибки во время отправки сообщения админа пользователю."""
    MESSAGE_NOT_FOUND = "MESSAGE_NOT_FOUND"
    TICKET_NOT_FOUND = "TICKET_NOT_FOUND"
    USER_NOT_FOUND = "USER_NOT_FOUND"

@dataclass(slots=True)
class AdminReplyToTicketResult:
    success: bool
    tg_id: int | None = None
    error: AdminReplyToTicketErrorType | None = None

class AdminReplyToTicket(BaseUseCase):
    """Сценарий отправки сообщения админа пользователю."""
    def __init__(self, uow: AbstractUnitOfWork):
        self._uow = uow

    async def execute(self, thread_id: int, text: str) -> AdminReplyToTicketResult:
        async with self._uow as uow:
            ticket = await uow.tickets.get_by_thread_id(thread_id)
            if ticket is None:
                await self._audit(
                    uow,
                    AuditLevel.ERROR,
                    AuditEventType.TICKET_NOT_FOUND,
                    f"[AdminReplyToTicket][execute]\n"
                    f"Тикет не удалось найти в БД.\n"
                    f"thread_id={thread_id}."
                )
                return AdminReplyToTicketResult(success=False, error=AdminReplyToTicketErrorType.TICKET_NOT_FOUND)

            user = await uow.users.get_by_id(ticket.user_id)
            if user is None:
                await self._audit(
                    uow,
                    AuditLevel.ERROR,
                    AuditEventType.USER_NOT_FOUND,
                    f"[AdminReplyToTicket][execute]\n"
                    f"Не удалось найти пользователя, привязанного к тикету.\n"
                    f"user_id={ticket.user_id}, ticket_id={ticket.id}, "
                    f"thread_id={thread_id}."
                )
                return AdminReplyToTicketResult(success=False, error=AdminReplyToTicketErrorType.USER_NOT_FOUND)

            admin_message = Message(
                ticket_id=ticket.id,
                sender_type=MessageSenderType.SUPPORT,
                text=text
            )
            await uow.messages.add(admin_message)

            return AdminReplyToTicketResult(success=True, tg_id=user.tg_id)