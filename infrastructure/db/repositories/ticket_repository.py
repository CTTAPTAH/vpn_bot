from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.ticket import Ticket as DomainTicket
from application.ports.repositories.ticket_repository import AbstractTicketRepository
from infrastructure.db.models.ticket import Ticket as ORMTicket
from domain.enums import TicketStatus

def to_domain(orm_ticket: ORMTicket) -> DomainTicket:
    return DomainTicket(
        id=orm_ticket.id,
        user_id=orm_ticket.user_id,
        thread_id=orm_ticket.thread_id,
        title=orm_ticket.title,
        status=orm_ticket.status,
        created_at=orm_ticket.created_at
    )

class SQLAlchemyTicketRepository(AbstractTicketRepository):
    """Реализация репозитория обращения в поддержку на основе SQLAlchemy."""
    def __init__(self, session: AsyncSession):
        self._session = session

    # Получение данных
    async def get_by_id(self, ticket_id: int) -> DomainTicket | None:
        stmt = select(ORMTicket).where(ORMTicket.id == ticket_id)
        result = await self._session.execute(stmt)
        orm_ticket = result.scalar_one_or_none()

        if orm_ticket is None:
            return None

        return to_domain(orm_ticket)

    async def get_open_by_user_id(self, user_id: int) -> DomainTicket | None:
        stmt = select(ORMTicket).where(
            ORMTicket.user_id == user_id,
            ORMTicket.status == TicketStatus.OPEN
        )
        result = await self._session.execute(stmt)
        orm_ticket = result.scalar_one_or_none()

        if orm_ticket is None:
            return None

        return to_domain(orm_ticket)

    async def get_by_thread_id(self, thread_id: int) -> DomainTicket | None:
        stmt = select(ORMTicket).where(ORMTicket.thread_id == thread_id)
        result = await self._session.execute(stmt)
        orm_ticket = result.scalar_one_or_none()

        if orm_ticket is None:
            return None

        return to_domain(orm_ticket)

    async def get_latest(self, user_id: int, limit: int) -> list[DomainTicket]:
        stmt = (
            select(ORMTicket).
            where(ORMTicket.user_id == user_id).
            order_by(ORMTicket.created_at.desc()).
            limit(limit)
        )
        result = await self._session.execute(stmt)
        orm_tickets = result.scalars().all()

        return [to_domain(orm_ticket) for orm_ticket in orm_tickets]

    # Добавление данных
    async def add(self, ticket: DomainTicket) -> None:
        orm_ticket = ORMTicket(
            user_id=ticket.user_id,
            thread_id=ticket.thread_id,
            title=ticket.title,
            status=ticket.status,
            created_at=ticket.created_at
        )

        self._session.add(orm_ticket)
        await self._session.flush()

        ticket.id = orm_ticket.id # синхронизация id

    # Обновление данных
    async def update(self, ticket: DomainTicket) -> None:
        orm_ticket = await self._session.get(ORMTicket, ticket.id)

        if orm_ticket is None:
            raise ValueError("Ticket not found")

        orm_ticket.status = ticket.status
        orm_ticket.closed_at = ticket.closed_at