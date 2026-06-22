from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.access_key import AccessKey as DomainAccessKey
from application.ports.repositories.access_key_repository import AbstractAccessKeyRepository
from infrastructure.db.models.access_key import AccessKey as ORMAccessKey

def to_domain(orm_access_key: ORMAccessKey) -> DomainAccessKey:
    return DomainAccessKey(
        id=orm_access_key.id,
        server_id=orm_access_key.server_id,
        sub_id=orm_access_key.sub_id,
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

    async def list_by_sub(self, sub_id: int) -> list[DomainAccessKey]:
        stmt = (
            select(ORMAccessKey)
            .where(ORMAccessKey.sub_id == sub_id)
        )
        result = await self._session.execute(stmt)
        orm_keys = result.scalars().all()

        return [to_domain(orm_key) for orm_key in orm_keys]

    # Добавление данных
    async def add(self, access_key: DomainAccessKey) -> None:
        orm_key = ORMAccessKey(
            server_id=access_key.server_id,
            sub_id=access_key.sub_id,
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

        orm_key.vless_link = access_key.vless_link

    # Удаление данных
    async def delete(self, access_key_id: int) -> None:
        """Удаляет ключ из базы по ID."""
        stmt = (
            delete(ORMAccessKey)
            .where(ORMAccessKey.id == access_key_id)
            .returning(ORMAccessKey.id)
        )
        result = await self._session.scalar(stmt)

        if result is None:
            raise ValueError("AccessKey not found")