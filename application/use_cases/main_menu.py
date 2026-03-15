"""Backend-логика для формирования данных главного меню."""
from dataclasses import dataclass

from application.ports.unit_of_work import AbstractUnitOfWork
from core.utils import utcnow_naive

@dataclass
class MainMenuDTO:
    """Для заполнения данными главного меню."""
    active_keys: int
    has_trial: bool

class GetMainMenuUseCase:
    """Сценарий получения данных для главного меню."""
    def __init__(self, uow: AbstractUnitOfWork):
        self._uow = uow

    async def execute(self, tg_id: int, username: str) -> MainMenuDTO:
        """Возвращает данные, необходимые для отображения главного меню."""
        async with self._uow as uow:
            user = await uow.users.get_or_create(tg_id, username)

            has_trial = await uow.payments.has_trial(user.id)
            active_keys = await uow.keys.count_active_keys(user.id, utcnow_naive())

        return MainMenuDTO(active_keys=active_keys, has_trial=has_trial)