"""Backend-логика для удаления ключа пользователя."""
from dataclasses import dataclass
from enum import StrEnum

from application.use_cases.base_use_case import BaseUseCase
from application.ports.unit_of_work import AbstractUnitOfWork
from application.ports.vpn.gateway_factory import AbstractVpnGatewayFactory
from application.errors.vpn_errors import (
    VpnKeyNotFoundError,
    VpnGatewayError
)
from domain.enums import AuditLevel, AuditEventType

class DeleteKeyErrorType(StrEnum):
    """Тип ошибки при удалении ключа."""
    KEY_NOT_FOUND = "KEY_NOT_FOUND"
    SERVER_NOT_FOUND = "SERVER_NOT_FOUND"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"

@dataclass(slots=True)
class DeleteKeyResult:
    """Базовый класс для результатов: ошибка или успех."""
    success: bool
    error_type: DeleteKeyErrorType | None = None

class DeleteKeyUseCase(BaseUseCase):
    """Сценарий удаления ключа пользователя."""
    def __init__(self, uow: AbstractUnitOfWork, gateway_factory: AbstractVpnGatewayFactory):
        self._uow = uow
        self._gateway_factory = gateway_factory

    async def execute(self, tg_id: int, key_id: int) -> DeleteKeyResult:
        """Удалить ключ пользователя."""
        async with self._uow as uow:
            key = await uow.keys.get_by_id(key_id)
            if key is None:
                return DeleteKeyResult(success=False, error_type=DeleteKeyErrorType.KEY_NOT_FOUND)
            await uow.keys.delete(key_id)
            server_id = key.id

        try:
            async with self._uow as uow:
                server = await uow.servers.get_by_id(server_id)
                if server is None:
                    await self._audit(
                        uow,
                        AuditLevel.ERROR,
                        AuditEventType.SERVER_NOT_FOUND,
                        f"[DeleteKeyUseCase][execute]"
                        f"Сервер не найден в БД.\n"
                        f"tg_id={tg_id}, server_id={server_id}."
                    )
                    return DeleteKeyResult(success=False, error_type=DeleteKeyErrorType.SERVER_NOT_FOUND)
            vpn = await self._gateway_factory.get_gateway(server)
            email = str(key_id)
            await vpn.delete_key(email)

        except VpnKeyNotFoundError:
            async with self._uow as uow:
                await self._audit(
                    uow,
                    AuditLevel.ERROR,
                    AuditEventType.KEY_NOT_FOUND_IN_VPN,
                    f"[DeleteKeyUseCase][execute]"
                    f"Попытка удалить ключ, которого нет в VPN.\n"
                    f"tg_id={tg_id}, key_id={key_id}."
                )
            return DeleteKeyResult(success=False, error_type=DeleteKeyErrorType.KEY_NOT_FOUND)

        except VpnGatewayError as e:
            async with self._uow as uow:
                await self._audit(
                    uow,
                    AuditLevel.ERROR,
                    AuditEventType.VPN_KEY_DELETED,
                    f"[DeleteKeyUseCase][execute]"
                    f"Неизвестная ошибка удаления ключа из XUI.\n"
                    f"tg_id={tg_id}, key_id={key_id}.\n"
                    f"Ошибка: {e}"
                )
                return DeleteKeyResult(success=False, error_type=DeleteKeyErrorType.UNKNOWN_ERROR)

        return DeleteKeyResult(success=True)