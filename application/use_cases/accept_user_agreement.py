"""Backend-логика соглашения пользователя с политикой."""
from application.ports.unit_of_work import AbstractUnitOfWork

class AcceptUserAgreementUseCase:
    """Сценарий соглашения пользователя с политикой."""
    def __init__(self, uow: AbstractUnitOfWork):
        self._uow = uow

    async def execute(self, tg_id: int, username: str | None) -> None:
        async with self._uow as uow:
            user = await uow.users.get_or_create(tg_id, username)
            user.agreed_to_policy = True

            await uow.users.update(user)