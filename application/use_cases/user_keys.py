"""Backend-логика для формирования данных для отображения информации о ключах пользователя."""
from dataclasses import dataclass

from application.common.dto import KeyDTO
from application.ports.unit_of_work import AbstractUnitOfWork
from core.utils import utcnow_naive

@dataclass
class UserKeysDTO:
    """Для заполнения данными информации о ключах пользователя."""
    count_all_keys: int
    count_active_keys: int
    keys: list[KeyDTO]

class GetUserKeysUseCase:
    """Сценарий получения данных о ключах пользователя."""
    def __init__(self, uow: AbstractUnitOfWork):
        self._uow = uow

    async def execute(self, tg_id: int, username: str) -> UserKeysDTO:
        """Возвращает данные, необходимые для отображения информации о ключах пользователя."""
        now = utcnow_naive()

        async with self._uow as uow:
            user = await uow.users.get_or_create(tg_id, username)

            count_all_keys = await uow.keys.count_all_keys(user.id)
            count_active_keys = await uow.keys.count_active_keys(user.id, now)
            views = await uow.keys.list_view_by_user(user.id)

        keys_dto = [
            KeyDTO(
                id=v.id,
                plan_name=v.plan_name,
                end_at=v.end_at,
                is_expired=now > v.end_at
            )
            for v in views
        ]

        return UserKeysDTO(
            count_active_keys=count_active_keys,
            count_all_keys=count_all_keys,
            keys=keys_dto
        )