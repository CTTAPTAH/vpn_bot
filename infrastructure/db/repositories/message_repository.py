from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.message import Message as DomainMessage
from application.ports.repositories.message_repository import AbstractMessageRepository
from infrastructure.db.models.message import Message as ORMMessage


def to_domain(orm_message: ORMMessage) -> DomainMessage:
    return DomainMessage(
        id=orm_message.id,
        ticket_id=orm_message.ticket_id,
        sender_type=orm_message.sender_type,
        text=orm_message.text,
        telegram_message_id=orm_message.telegram_message_id,
        created_at=orm_message.created_at
    )


class SQLAlchemyMessageRepository(AbstractMessageRepository):
    """Реализация репозитория сообщения в поддержку на основе SQLAlchemy."""
    def __init__(self, session: AsyncSession):
        self._session = session

    # Получение данных
    async def get_by_id(self, message_id: int) -> DomainMessage | None:
        stmt = select(ORMMessage).where(ORMMessage.id == message_id)
        result = await self._session.execute(stmt)
        orm_message = result.scalar_one_or_none()

        if orm_message is None:
            return None

        return to_domain(orm_message)

    async def get_by_telegram_message_id(self, telegram_message_id) -> DomainMessage | None:
        stmt = select(ORMMessage).where(ORMMessage.telegram_message_id == telegram_message_id)
        result = await self._session.execute(stmt)
        orm_message = result.scalar_one_or_none()

        if orm_message is None:
            return None

        return to_domain(orm_message)

    # Добавление данных
    async def add(self, message: DomainMessage) -> None:
        orm_message = ORMMessage(
            ticket_id=message.ticket_id,
            sender_type=message.sender_type,
            text=message.text,
            telegram_message_id=message.telegram_message_id,
            created_at=message.created_at
        )
        self._session.add(orm_message)
        await self._session.flush()

        message.id = orm_message.id # синхронизация id

    # Обновление данных
    async def update(self, message: DomainMessage) -> None:
        orm_message = await self._session.get(ORMMessage, message.id)

        if orm_message is None:
            raise ValueError("Message not found")

        orm_message.ticket_id = message.ticket_id
        orm_message.sender_type = message.sender_type
        orm_message.text = message.text