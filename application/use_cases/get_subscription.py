from dataclasses import dataclass
from application.use_cases.base_use_case import BaseUseCase
from application.ports.unit_of_work import AbstractUnitOfWork

@dataclass
class GetSubscriptionResult:
    success: bool
    vless_links: list[str] | None = None

class GetSubscriptionUseCase(BaseUseCase):
    """Возвращает список vless-ссылок для подписки по токену."""
    def __init__(self, uow: AbstractUnitOfWork):
        self._uow = uow

    async def execute(self, token: str) -> GetSubscriptionResult:
        async with self._uow as uow:
            sub = await uow.sub.get_by_token(token)
            if sub is None:
                return GetSubscriptionResult(success=False)

            keys = await uow.keys.list_by_sub(sub.id)
            links = [key.vless_link for key in keys if key.vless_link]

            return GetSubscriptionResult(success=True, vless_links=links)