"""Backend-логика для формирования данных для отображения информации о подписке пользователя."""
from dataclasses import dataclass
from datetime import datetime

from application.use_cases.base_use_case import BaseUseCase
from application.ports.unit_of_work import AbstractUnitOfWork
from core.utils import utcnow

@dataclass
class UserSubDTO:
    """Для заполнения данными информации о подписке пользователя."""
    sub_id: int | None = None
    sub_end_at: datetime | None = None
    is_sub_active: bool = False
    sub_token: str | None = None

class GetUserSubUseCase(BaseUseCase):
    """Сценарий получения данных о подписке пользователя."""
    def __init__(self, uow: AbstractUnitOfWork):
        self._uow = uow

    async def execute(self, tg_id: int, username: str | None) -> UserSubDTO:
        """Возвращает данные, необходимые для отображения информации о подписке пользователя."""
        now = utcnow()
        async with self._uow as uow:
            user = await uow.users.get_or_create(tg_id, username)
            sub = await uow.sub.get_by_user_id(user.id)

            if sub is None:
                return UserSubDTO()

            return UserSubDTO(
                sub_id=sub.id,
                sub_end_at=sub.end_at,
                is_sub_active=sub.end_at > now,
                sub_token=sub.sub_token
            )