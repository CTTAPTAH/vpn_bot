import random

from application.ports.repositories.access_key_repository import AbstractAccessKeyRepository

class NoAvailableServersError(Exception):
    pass

class ServerSelectionService:
    """Сервис выбора сервера для размещения нового ключа по принципу наименьшей загрузки."""
    async def select_server(self, key_repo: AbstractAccessKeyRepository, server_ids: list[int]) -> int:
        if not server_ids:
            raise NoAvailableServersError()

        loads = await key_repo.get_servers_keys_load(server_ids)
        available = [
            server for server in loads
            if server.keys_count < server.max_clients
        ]
        if not available:
            raise NoAvailableServersError()

        min_load = min(server.keys_count for server in available)

        candidates = [
            server for server in available
            if server.keys_count == min_load
        ]
        selected = random.choice(candidates)

        return selected.server_id