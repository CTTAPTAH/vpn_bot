from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.subscription import Subscription as DomainSubscription
from application.ports.repositories.subscription_repository import AbstractSubscriptionRepository
from infrastructure.db.models.subscription import Subscription as ORMSubscription

def to_domain(orm_sub: ORMSubscription) -> DomainSubscription:
    return DomainSubscription(
        id=orm_sub.id,
        user_id=orm_sub.user_id,
        plan_id=orm_sub.plan_id,
        sub_token=orm_sub.sub_token,
        start_at=orm_sub.start_at,
        end_at=orm_sub.end_at
    )

class SQLAlchemySubscriptionRepository(AbstractSubscriptionRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    # Получить данные
    async def get_by_id(self, sub_id: int) -> DomainSubscription | None:
        stmt = select(ORMSubscription).where(ORMSubscription.id == sub_id)
        result = await self._session.execute(stmt)
        orm_key = result.scalar_one_or_none()

        if orm_key is None:
            return None

        return to_domain(orm_key)

    async def get_for_update(self, sub_id: int) -> DomainSubscription | None:
        stmt = (
            select(ORMSubscription)
            .where(ORMSubscription.id == sub_id)
            .with_for_update()
        )
        result = await self._session.execute(stmt)
        orm_key = result.scalar_one_or_none()

        if orm_key is None:
            return None

        return to_domain(orm_key)

    async def get_by_token(self, token: str) -> DomainSubscription | None:
        stmt = (
            select(ORMSubscription)
            .where(ORMSubscription.sub_token == token)
        )
        result = await self._session.execute(stmt)
        orm_key = result.scalar_one_or_none()

        if orm_key is None:
            return None

        return to_domain(orm_key)

    async def get_by_user_id(self, user_id: int) -> DomainSubscription | None:
        stmt = (
            select(ORMSubscription)
            .where(ORMSubscription.user_id == user_id)
        )
        result = await self._session.execute(stmt)
        orm_key = result.scalar_one_or_none()

        if orm_key is None:
            return None

        return to_domain(orm_key)

    # Добавление данных
    async def add(self, sub: DomainSubscription) -> None:
        orm_sub = ORMSubscription(
            user_id=sub.user_id,
            plan_id=sub.plan_id,
            sub_token=sub.sub_token,
            start_at=sub.start_at,
            end_at=sub.end_at
        )
        self._session.add(orm_sub)
        await self._session.flush()

        sub.id = orm_sub.id  # синхронизируем id

    # Обновление данных
    async def update(self, sub: DomainSubscription) -> None:
        orm_sub = await self._session.get(ORMSubscription, sub.id)

        if orm_sub is None:
            raise ValueError("Subscription not found")

        orm_sub.plan_id = sub.plan_id
        orm_sub.end_at = sub.end_at