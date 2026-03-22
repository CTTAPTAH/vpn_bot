"""Backend-логика для удаления ключа пользователя."""
from dataclasses import dataclass
from enum import StrEnum

from application.ports.unit_of_work import AbstractUnitOfWork
from application.ports.vpn_gateway import VpnGateway
from application.errors.vpn_errors import (
    VpnKeyNotFoundError,
    VpnGatewayError
)
from domain.enums import AuditLevel, AuditEventType
from domain.entities.audit_log import AuditLog

class DeleteKeyErrorType(StrEnum):
    """Тип ошибки при удалении ключа."""
    KEY_NOT_FOUND = "KEY_NOT_FOUND"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"

@dataclass(slots=True)
class DeleteKeyResult:
    """Базовый класс для результатов: ошибка или успех."""
    success: bool
    error_type: DeleteKeyErrorType | None = None

class DeleteKeyUseCase:
    """Сценарий удаления ключа пользователя."""
    def __init__(self, uow: AbstractUnitOfWork, vpn: VpnGateway):
        self._uow = uow
        self._vpn = vpn

    async def execute(self, tg_id: int, key_id: int) -> DeleteKeyResult:
        """Удалить ключ пользователя."""
        async with self._uow as uow:
            key = await uow.keys.get_by_id(key_id)
            if key is None:
                return DeleteKeyResult(success=False, error_type=DeleteKeyErrorType.KEY_NOT_FOUND)
            await uow.keys.delete(key_id)

        try:
            email = str(key_id)
            await self._vpn.delete_key(email)

        except VpnKeyNotFoundError:
            async with self._uow as uow:
                await uow.audits.add(
                    AuditLog(
                        level=AuditLevel.ERROR,
                        event_type=AuditEventType.KEY_NOT_FOUND_IN_VPN,
                        message=(
                            f"Попытка удалить ключ, которого нет в XUI.\n"
                            f"tg_id={tg_id}, key_id={key_id}"
                        )
                    )
                )
            return DeleteKeyResult(success=False, error_type=DeleteKeyErrorType.KEY_NOT_FOUND)

        except VpnGatewayError as e:
            async with self._uow as uow:
                await uow.audits.add(
                    AuditLog(
                        level=AuditLevel.ERROR,
                        event_type=AuditEventType.VPN_KEY_DELETED,
                        message=f"Ошибка удаления ключа из XUI.\n"
                                f"tg_id={tg_id}, key_id={key_id}, Ошибка: {e}"
                    )
                )
            return DeleteKeyResult(success=False, error_type=DeleteKeyErrorType.UNKNOWN_ERROR)

        return DeleteKeyResult(success=True)