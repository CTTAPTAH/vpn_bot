from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from domain.entities.user import User as DomainUser
from application.ports.repositories.user_repository import AbstractUserRepository
from infrastructure.db.models.user import User as ORMUser

def to_domain(orm_user: ORMUser) -> DomainUser:
    return DomainUser(
        id=orm_user.id,
        tg_id=orm_user.tg_id,
        username=orm_user.username,
        created_at=orm_user.created_at,
        is_blocked=orm_user.is_blocked,
        agreed_to_policy=orm_user.agreed_to_policy
    )

class SQLAlchemyUserRepository(AbstractUserRepository):
    """Реализация репозитория пользователей на основе SQLAlchemy."""
    def __init__(self, session: AsyncSession):
        self._session = session

    # Получение данных
    async def get_by_id(self, user_id: int) -> DomainUser | None:
        """Получение пользователя по его id."""
        stmt = select(ORMUser).where(ORMUser.id == user_id)
        result = await self._session.execute(stmt)
        orm_user = result.scalar_one_or_none()

        if orm_user is None:
            return None

        return to_domain(orm_user)

    async def get_by_id_for_update(self, user_id: int) -> DomainUser | None:
        """Получение пользователя по его id."""
        stmt = select(ORMUser).where(ORMUser.id == user_id).with_for_update()
        result = await self._session.execute(stmt)
        orm_user = result.scalar_one_or_none()

        if orm_user is None:
            return None

        return to_domain(orm_user)

    async def get_by_tg_id(self, tg_id: int) -> DomainUser | None:
        """Получение пользователя по его tg ig."""
        stmt = select(ORMUser).where(ORMUser.tg_id == tg_id)
        result = await self._session.execute(stmt)
        orm_user = result.scalar_one_or_none()

        if orm_user is None:
            return None

        return to_domain(orm_user)

    async def get_or_create(self, tg_id: int, username: str | None) -> DomainUser:
        """Получить пользователя, если его нет, то создать."""
        stmt = select(ORMUser).where(ORMUser.tg_id == tg_id)
        result = await self._session.execute(stmt)
        orm_user = result.scalar_one_or_none()

        if orm_user:
            if orm_user.username != username:
                orm_user.username = username

            return to_domain(orm_user)

        # Если его нет, то создаём
        domain_user = DomainUser(
            tg_id=tg_id,
            username=username
        )
        try:
            async with self._session.begin_nested():
                await self.add(domain_user)
        except IntegrityError:
            return await self.get_by_tg_id(tg_id)

        return domain_user

    # Добавление данных
    async def add(self, user: DomainUser) -> None:
        orm_user = ORMUser(
            tg_id=user.tg_id,
            username=user.username,
            created_at=user.created_at,
            is_blocked=user.is_blocked,
            agreed_to_policy=user.agreed_to_policy
        )
        self._session.add(orm_user)
        await self._session.flush()

        user.id = orm_user.id # синхронизируем id

    # Обновление данных
    async def update(self, user: DomainUser) -> None:
        orm_user = await self._session.get(ORMUser, user.id)

        if orm_user is None:
            raise ValueError("User not found")

        orm_user.username = user.username
        orm_user.is_blocked = user.is_blocked
        orm_user.agreed_to_policy = user.agreed_to_policy