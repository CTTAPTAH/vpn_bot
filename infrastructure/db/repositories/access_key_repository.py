from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from domain.entities.access_key import AccessKey as DomainAccessKey
from application.ports.repositories.access_key_repository import (
    AbstractAccessKeyRepository,
    AccessKeyView
)
from infrastructure.db.models.access_key import AccessKey as ORMAccessKey
from infrastructure.db.models.plan import Plan as ORMPlan

def to_domain(orm_access_key: ORMAccessKey) -> DomainAccessKey:
    return DomainAccessKey(
        id=orm_access_key.id,
        user_id=orm_access_key.user_id,
        plan_id=orm_access_key.plan_id,
        start_at=orm_access_key.start_at,
        end_at=orm_access_key.end_at,
        vless_link=orm_access_key.vless_link
    )

class SQLAlchemyAccessKeyRepository(AbstractAccessKeyRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    # Получить данные
    async def get_by_id(self, access_key_id: int) -> DomainAccessKey | None:
        """Получение ключа по id."""
        stmt = select(ORMAccessKey).where(ORMAccessKey.id == access_key_id)
        result = await self._session.execute(stmt)
        orm_key = result.scalar_one_or_none()

        if orm_key is None:
            return None

        return to_domain(orm_key)

    async def get_for_update(self, key_id: int) -> DomainAccessKey | None:
        """Возвращает ключ и блокирует строку в БД до конца транзакции."""
        stmt = (
            select(ORMAccessKey)
            .where(ORMAccessKey.id == key_id)
            .with_for_update()
        )

        result = await self._session.execute(stmt)
        orm_model = result.scalar_one_or_none()

        if orm_model is None:
            return None

        return to_domain(orm_model)

    async def get_view_by_id(self, access_key_id: int) -> AccessKeyView | None:
        """Получение информации для отображения ключа по id."""
        stmt = (
            select(
                ORMAccessKey.id,
                ORMPlan.name,
                ORMAccessKey.end_at,
                ORMAccessKey.vless_link
            )
            .join(ORMPlan, ORMAccessKey.plan_id == ORMPlan.id)
            .where(ORMAccessKey.id == access_key_id)
        )
        result = await self._session.execute(stmt)
        row = result.one_or_none()

        if row is None:
            return None

        return AccessKeyView(
            id=row.id,
            plan_name=row.name,
            end_at=row.end_at,
            vless_link=row.vless_link
        )

    async def list_by_user(self, user_id: int) -> list[DomainAccessKey]:
        """Получить все ключи пользователя."""
        stmt = (
            select(ORMAccessKey)
            .where(ORMAccessKey.user_id == user_id)
            .order_by(ORMAccessKey.start_at.desc())
        )
        result = await self._session.execute(stmt)
        orm_keys = result.scalars().all()

        return [to_domain(orm_key) for orm_key in orm_keys]

    async def list_view_by_user(self, user_id: int) -> list[AccessKeyView]:
        """Информация, которая отображается пользователю."""
        stmt = (
            select(
                ORMAccessKey.id,
                ORMPlan.name,
                ORMAccessKey.end_at,
                ORMAccessKey.vless_link
            )
            .join(ORMPlan, ORMAccessKey.plan_id == ORMPlan.id)
            .where(ORMAccessKey.user_id == user_id)
            .order_by(ORMAccessKey.end_at.desc())
        )
        result = await self._session.execute(stmt)
        rows = result.all()

        return [
            AccessKeyView(
                id=row.id,
                plan_name=row.name,
                end_at=row.end_at,
                vless_link=row.vless_link
            )
            for row in rows
        ]

    async def count_all_keys(self, user_id: int) -> int:
        """Возвращает количество всех ключей пользователя."""
        stmt = (
            select(func.count())
            .select_from(ORMAccessKey)
            .where(ORMAccessKey.user_id == user_id)
        )

        result = await self._session.scalar(stmt)
        return int(result)

    async def count_active_keys(self, user_id: int, now: datetime) -> int:
        """Возвращает количество активных (не истёкших) ключей пользователя."""
        stmt = select(func.count()).where(
            ORMAccessKey.user_id == user_id,
            ORMAccessKey.end_at > now
        )

        result = await self._session.scalar(stmt)
        return int(result)

    # Добавление данных
    async def add(self, access_key: DomainAccessKey) -> None:
        orm_key = ORMAccessKey(
            user_id=access_key.user_id,
            plan_id=access_key.plan_id,
            start_at=access_key.start_at,
            end_at=access_key.end_at,
            vless_link=access_key.vless_link
        )
        self._session.add(orm_key)
        await self._session.flush()

        access_key.id = orm_key.id # синхронизируем id

    # Обновление данных
    async def update(self, access_key: DomainAccessKey) -> None:
        orm_key = await self._session.get(ORMAccessKey, access_key.id)

        if orm_key is None:
            raise ValueError("AccessKey not found")

        orm_key.user_id = access_key.user_id
        orm_key.plan_id = access_key.plan_id
        orm_key.end_at = access_key.end_at
        orm_key.vless_link = access_key.vless_link

    # Удаление данных
    async def delete(self, access_key_id: int) -> None:
        """Удаляет ключ из базы по ID."""
        stmt = select(ORMAccessKey).where(ORMAccessKey.id == access_key_id)
        result = await self._session.execute(stmt)
        orm_key = result.scalar_one_or_none()

        if orm_key is None:
            raise ValueError(f"AccessKey with id={access_key_id} not found")

        await self._session.delete(orm_key)