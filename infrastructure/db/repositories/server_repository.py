from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.server import Server as DomainServer, Server
from application.ports.repositories.server_repository import AbstractServerRepository
from infrastructure.db.models.server import Server as ORMServer

def to_domain(orm_server: ORMServer) -> DomainServer:
    return DomainServer(
        id=orm_server.id,
        name=orm_server.name,
        panel_url=orm_server.panel_url,
        panel_username=orm_server.panel_username,
        panel_password=orm_server.panel_password,
        host=orm_server.host,
        inbound_id=orm_server.inbound_id,
        inbound_name=orm_server.inbound_name,
        default_key_name=orm_server.default_key_name,
        max_clients=orm_server.max_clients
    )

class SQLAlchemyServerRepository(AbstractServerRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    # Получить данные
    async def get_by_id(self, server_id: int) -> Server | None:
        """Получение сервера по id."""
        stmt = select(ORMServer).where(ORMServer.id == server_id)
        result = await self._session.execute(stmt)
        orm_server = result.scalar_one_or_none()

        if orm_server is None:
            return None

        return to_domain(orm_server)

    async def get_id_active_servers(self) -> list[int]:
        """Получить id активных серверов."""
        stmt = (
            select(ORMServer.id)
            .where(ORMServer.is_active.is_(True))
            .order_by(ORMServer.id)
        )
        result = await self._session.execute(stmt)
        rows = list(result.scalars().all())

        return rows

    # Добавление данных
    async def add(self, server: DomainServer) -> None:
        orm_server = ORMServer(
            name=server.name,
            panel_url=server.panel_url,
            panel_username=server.panel_username,
            panel_password=server.panel_password,
            host=server.host,
            inbound_id=server.inbound_id,
            inbound_name=server.inbound_name,
            default_key_name=server.default_key_name,
            max_clients=server.max_clients
        )
        self._session.add(orm_server)
        await self._session.flush()

        server.id = orm_server.id  # синхронизируем id

    # Обновление данных
    async def update(self, server: DomainServer) -> None:
        orm_server = await self._session.get(ORMServer, server.id)

        if orm_server is None:
            raise ValueError("Server not found")

        orm_server.name = server.name
        orm_server.panel_url = server.panel_url
        orm_server.panel_username = server.panel_username
        orm_server.panel_password = server.panel_password
        orm_server.host = server.host
        orm_server.inbound_id = server.inbound_id
        orm_server.inbound_name=server.inbound_name
        orm_server.default_key_name = server.default_key_name
        orm_server.max_clients=server.max_clients