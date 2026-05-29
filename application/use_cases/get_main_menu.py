"""Backend-логика для формирования данных главного меню."""
from dataclasses import dataclass

from application.use_cases.base_use_case import BaseUseCase
from application.ports.unit_of_work import AbstractUnitOfWork
from core.utils import utcnow

@dataclass(slots=True)
class MainMenuDTO:
    agreed_to_policy: bool
    active_keys: int
    trial_used: bool

class GetMainMenuUseCase(BaseUseCase):
    """Сценарий получения данных для главного меню."""
    def __init__(self, uow: AbstractUnitOfWork):
        self._uow = uow

    async def execute(self, tg_id: int, username: str | None) -> MainMenuDTO:
        async with self._uow as uow:
            user = await uow.users.get_or_create(tg_id, username)

            now = utcnow()
            agreed_to_policy = user.agreed_to_policy
            trial_used = await uow.payments.has_trial(user.id)
            active_keys = await uow.keys.count_active_keys(user.id, now)

        return MainMenuDTO(agreed_to_policy=agreed_to_policy, active_keys=active_keys, trial_used=trial_used)