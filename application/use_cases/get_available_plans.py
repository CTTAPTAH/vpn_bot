"""Backend-логика для формирования данных о всех тарифах."""
from dataclasses import dataclass

from application.ports.unit_of_work import AbstractUnitOfWork
from core.utils import months_from_seconds

@dataclass
class PlanDTO:
    id: int
    name: str
    price: int
    duration_month: int

class GetAvailablePlansUseCase:
    """Сценарий получения данных о тарифах."""
    def __init__(self, uow: AbstractUnitOfWork):
        self._uow = uow

    async def execute(self) -> list[PlanDTO]:
        """Возвращает данные, необходимые для отображения информации о тарифах."""
        async with self._uow as uow:
            plans = await uow.plans.get_available_for_purchase()

        return [
            PlanDTO(
                id=plan.id,
                name=plan.name,
                price=plan.price,
                duration_month=months_from_seconds(plan.duration_seconds)
            )
            for plan in plans
        ]