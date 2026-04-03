"""Backend-логика для создания или добавления сообщения в обращение."""
from sqlalchemy.exc import IntegrityError

from application.ports.unit_of_work import AbstractUnitOfWork
from domain.entities.ticket import Ticket
from domain.entities.message import Message
from domain.enums import TicketStatus, MessageSenderType

class CreateOrAppendUserTicketMessage:
    """Сценарий создания или добавления сообщения в обращение."""
    def __init__(self, uow: AbstractUnitOfWork):
        self._uow = uow

    async def execute(self, tg_id: int, username: str, text: str, telegram_message_id: int) -> None:
        async with self._uow as uow:
            user = await uow.users.get_or_create(tg_id, username)
            ticket = await uow.tickets.get_open_by_user_id(user.id)

            if ticket is None:
                try:
                    ticket = Ticket(
                        user_id=user.id,
                        status=TicketStatus.OPEN
                    )
                    await uow.tickets.add(ticket)
                except IntegrityError:
                    ticket = await uow.tickets.get_open_by_user_id(user.id)
                    if ticket is None:
                        # ЛОГИРОВАТЬ
                        raise RuntimeError("Failed to get or create ticket")

            message = Message(
                ticket_id=ticket.id,
                sender_type=MessageSenderType.USER,
                text=text,
                telegram_message_id=telegram_message_id
            )
            await uow.messages.add(message)