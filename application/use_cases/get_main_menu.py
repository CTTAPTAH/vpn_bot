"""Backend-логика для формирования данных главного меню."""
from dataclasses import dataclass
from datetime import datetime

from application.use_cases.base_use_case import BaseUseCase
from application.ports.unit_of_work import AbstractUnitOfWork
from core.utils import utcnow

@dataclass(slots=True)
class MainMenuDTO:
    agreed_to_policy: bool
    trial_used: bool
    sub_id: int | None = None
    sub_end_at: datetime | None = None
    is_sub_active: bool = False

class GetMainMenuUseCase(BaseUseCase):
    """Сценарий получения данных для главного меню."""
    def __init__(self, uow: AbstractUnitOfWork):
        self._uow = uow

    async def execute(self, tg_id: int, username: str | None) -> MainMenuDTO:
        async with self._uow as uow:
            user = await uow.users.get_or_create(tg_id, username)

            now = utcnow()
            trial_used = await uow.payments.has_trial(user.id)
            sub = await uow.sub.get_by_user_id(user.id)

            if sub is None:
                return MainMenuDTO(agreed_to_policy=user.agreed_to_policy, trial_used=trial_used)

            return MainMenuDTO(
                agreed_to_policy=user.agreed_to_policy,
                trial_used=trial_used,
                sub_id=sub.id,
                sub_end_at=sub.end_at,
                is_sub_active=sub.end_at > now
            )