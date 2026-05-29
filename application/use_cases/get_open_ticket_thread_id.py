"""Backend-логика для получения thread_id открытого тикета пользователя."""
from application.use_cases.base_use_case import BaseUseCase
from application.ports.unit_of_work import AbstractUnitOfWork

class GetOpenTicketThreadId(BaseUseCase):
    def __init__(self, uow: AbstractUnitOfWork):
        self._uow = uow

    async def execute(self, tg_id: int, username: str) -> int | None:
        async with self._uow as uow:
            user = await uow.users.get_or_create(tg_id, username)
            ticket = await uow.tickets.get_open_by_user_id(user.id)

            if ticket is None:
                return None

            return ticket.thread_id