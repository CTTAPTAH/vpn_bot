"""Backend-логика для удаления ключа пользователя."""
from dataclasses import dataclass
from enum import StrEnum

from application.ports.unit_of_work import AbstractUnitOfWork
from application.ports.vpn_gateway import VpnGateway
from domain.enums import AuditLevel, AuditEventType
from domain.entities.audit_log import AuditLog

class DeleteKeyErrorType(StrEnum):
    """Тип ошибки при удалении ключа."""
    KEY_NOT_FOUND = "KEY_NOT_FOUND"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"

class DeleteKeyResult:
    """Базовый класс для результатов: ошибка или успех."""
    pass

@dataclass
class DeleteKeySuccess(DeleteKeyResult):
    pass

@dataclass
class DeleteKeyError(DeleteKeyResult):
    error_type: DeleteKeyErrorType

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
                return DeleteKeyError(error_type=DeleteKeyErrorType.KEY_NOT_FOUND)
            await uow.keys.delete(key_id)

            try:
                email = str(key_id)
                if not await self._vpn.is_client_exists(email):
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
                    return DeleteKeyError(error_type=DeleteKeyErrorType.KEY_NOT_FOUND)

                await self._vpn.delete_key(email)
            except Exception as e:
                await uow.audits.add(
                    AuditLog(
                        level=AuditLevel.ERROR,
                        event_type=AuditEventType.XUI_DELETE,
                        message=f"Ошибка удаления ключа из XUI.\n"
                                f"tg_id={tg_id}, key_id={key_id}, Ошибка: {e}"
                    )
                )
                return DeleteKeyError(error_type=DeleteKeyErrorType.UNKNOWN_ERROR)

            return DeleteKeySuccess()