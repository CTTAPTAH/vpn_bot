"""Backend-логика для отправки сообщения админа пользователю."""
from application.ports.unit_of_work import AbstractUnitOfWork
from domain.entities.message import Message
from domain.enums import MessageSenderType

class AdminReplyToTicket:
    """Сценарий отправки сообщения админа пользователю."""
    def __init__(self, uow: AbstractUnitOfWork):
        self._uow = uow

    async def execute(self, reply_to_message_id: int, text: str) -> int: # Плохо возвращать int а не dto
        async with self._uow as uow:
            reply_message = await uow.messages.get_by_telegram_message_id(reply_to_message_id)
            if reply_message is None:
                raise ValueError("Reply message not found")

            ticket = await uow.tickets.get_by_id(reply_message.ticket_id)
            if ticket is None:
                raise ValueError("Reply ticket not found")

            user = await uow.users.get_by_id(ticket.user_id)
            if user is None:
                raise ValueError("Reply user not found")

            admin_message = Message(
                ticket_id=reply_message.ticket_id,
                sender_type=MessageSenderType.SUPPORT,
                text=text,
                telegram_message_id=0 # ЗАГЛУШКА. В БУДУЩЕМ СДЕЛАТЬ ПРАВИЛЬНО
            )

            await uow.messages.add(admin_message)

            return user.tg_id