from abc import ABC, abstractmethod
from domain.entities.plan import Plan

class AbstractPlanRepository(ABC):
    """
    Контракт репозитория тарифа.

    Application слой работает только с этим интерфейсом.
    """
    @abstractmethod
    async def get_by_id(self, plan_id: int) -> Plan | None:
        ...

    @abstractmethod
    async def get_trial(self) -> Plan | None:
        ...

    @abstractmethod
    async def get_available_for_purchase(self) -> list[Plan]:
        ...

    @abstractmethod
    async def get_vip(self) -> Plan | None:
        ...

    @abstractmethod
    async def add(self, plan: Plan) -> None:
        ...

    @abstractmethod
    async def update(self, plan: Plan) -> None:
        ...