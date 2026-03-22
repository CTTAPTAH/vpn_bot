from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.plan import Plan as DomainPlan
from application.ports.repositories.plan_repository import AbstractPlanRepository
from infrastructure.db.models.plan import Plan as ORMPlan
from domain.enums import PlanType

def to_domain(orm_plan: ORMPlan) -> DomainPlan:
    return DomainPlan(
        id=orm_plan.id,
        name=orm_plan.name,
        duration_seconds=orm_plan.duration_seconds,
        price=orm_plan.price,
        base_price=orm_plan.base_price,
        plan_type=orm_plan.plan_type,
        is_active=orm_plan.is_active,
    )

class SQLAlchemyPlanRepository(AbstractPlanRepository):
    """Реализация репозитория тарифов на основе SQLAlchemy."""
    def __init__(self, session: AsyncSession):
        self._session = session

    # Получение данных
    async def get_by_id(self, plan_id: int) -> DomainPlan | None:
        """Получение тарифа по его id."""
        stmt = select(ORMPlan).where(ORMPlan.id == plan_id)
        result = await self._session.execute(stmt)
        orm_plan = result.scalar_one_or_none()

        if orm_plan is None:
            return None

        return to_domain(orm_plan)

    async def get_trial(self) -> DomainPlan | None:
        """Получить тариф пробного периода."""
        stmt = select(ORMPlan).where(ORMPlan.plan_type == PlanType.TRIAL).order_by(ORMPlan.price)
        result = await self._session.execute(stmt)
        orm_plan = result.scalar_one_or_none()

        if orm_plan is None:
            return None

        return to_domain(orm_plan)

    async def get_available_for_purchase(self) -> list[DomainPlan]:
        """Получить тарифы, которые активны и используются для продажи."""
        stmt = select(ORMPlan).where(
            ORMPlan.plan_type == PlanType.PAID,
            ORMPlan.is_active.is_(True)
        )
        result = await self._session.execute(stmt)
        orm_plans = result.scalars().all()

        return [to_domain(orm_plan) for orm_plan in orm_plans ]

    async def get_vip(self) -> DomainPlan | None:
        """Получить VIP тариф."""
        stmt = select(ORMPlan).where(ORMPlan.plan_type == PlanType.VIP)
        result = await self._session.execute(stmt)
        orm_plan = result.scalar_one_or_none()

        if orm_plan is None:
            return None

        return to_domain(orm_plan)

    # Добавление данных
    async def add(self, plan: DomainPlan) -> None:
        """Добавление тарифа."""
        orm_plan = ORMPlan(
            name=plan.name,
            duration_seconds=plan.duration_seconds,
            price=plan.price,
            base_price=plan.base_price,
            plan_type=plan.plan_type,
            is_active=plan.is_active
        )
        self._session.add(orm_plan)
        await self._session.flush()

        plan.id = orm_plan.id # синхронизируем id

    # Обновление данных
    async def update(self, plan: DomainPlan) -> None:
        """Обновление данных."""
        orm_plan = await self._session.get(ORMPlan, plan.id)

        if orm_plan is None:
            raise ValueError("Plan not found")

        orm_plan.name = plan.name
        orm_plan.duration_seconds = plan.duration_seconds
        orm_plan.price = plan.price
        orm_plan.base_price = plan.base_price
        orm_plan.plan_type = plan.plan_type
        orm_plan.is_active = plan.is_active