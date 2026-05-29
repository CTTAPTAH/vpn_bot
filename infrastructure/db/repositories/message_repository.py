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

    async def get_all_by_ticket_id(self, ticket_id, limit: int) -> list[DomainMessage]:
        stmt = (
            select(ORMMessage)
            .where(ORMMessage.ticket_id == ticket_id)
            .order_by(ORMMessage.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        orm_messages = result.scalars().all()

        return [to_domain(message) for message in orm_messages]

    # Добавление данных
    async def add(self, message: DomainMessage) -> None:
        orm_message = ORMMessage(
            ticket_id=message.ticket_id,
            sender_type=message.sender_type,
            text=message.text,
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