"""Backend-логика для формирования данных о всех тарифах."""
from dataclasses import dataclass

from application.ports.unit_of_work import AbstractUnitOfWork
from application.common.dto import PlanDTO
from core.utils import months_from_seconds

@dataclass
class AvailablePlansDTO:
    plans: list[PlanDTO]
    pending_payment_id: int | None

class GetAvailablePlansUseCase:
    """Сценарий получения данных о тарифах."""
    def __init__(self, uow: AbstractUnitOfWork):
        self._uow = uow

    async def execute(self, tg_id: int, username: str) -> AvailablePlansDTO:
        async with self._uow as uow:
            user = await uow.users.get_or_create(tg_id, username)
            plans = await uow.plans.get_available_for_purchase()
            pending = await uow.payments.get_user_pending_payment_for_update(user.id)

        plans = [PlanDTO(
                id=plan.id,
                name=plan.name,
                price=plan.price,
                duration_months=months_from_seconds(plan.duration_seconds)
            )
            for plan in plans]
        return AvailablePlansDTO(
            plans=plans,
            pending_payment_id=pending.id if pending is not None else None
        )