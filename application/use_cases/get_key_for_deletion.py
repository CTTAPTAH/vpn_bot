"""Backend-логика получения информации о ключе, который собирается удалить пользователь."""
from dataclasses import dataclass
from enum import StrEnum

from application.common.dto import KeyDTO
from application.ports.unit_of_work import AbstractUnitOfWork
from domain.entities.audit_log import AuditLog
from domain.enums import AuditLevel, AuditEventType
from core.utils import utcnow_naive

class GetKeyForDeletionErrorType(StrEnum):
    """Тип ошибки при получении информации о ключе, который хотят удалить."""
    NOT_FOUND_IN_DB = "NOT_FOUND_IN_DB"

class GetKeyForDeletionResult:
    """Базовый класс для результатов: ошибка, успех"""
    pass

@dataclass
class GetKeyForDeletionSuccess(GetKeyForDeletionResult):
    key: KeyDTO

@dataclass
class GetKeyForDeletionError(GetKeyForDeletionResult):
    error_type: GetKeyForDeletionErrorType

class GetKeyForDeletionUseCase:
    """Сценарий получения данных о ключе, который хочет удалить пользователь."""
    def __init__(self, uow: AbstractUnitOfWork):
        self._uow = uow

    async def execute(self, key_id: int, tg_id: int) -> GetKeyForDeletionResult:
        """Получить информацию о выбранном ключе, который хотят удалить."""
        now = utcnow_naive()

        # Поиск ключа в БД
        async with self._uow as uow:
            key = await uow.keys.get_view_by_id(key_id)
            if key is None:
                await uow.audits.add(
                    AuditLog(
                        level=AuditLevel.ERROR,
                        event_type=AuditEventType.KEY_NOT_FOUND_IN_DB,
                        message=(
                            f"Не удалось выдать информацию о ключе.\n"
                            f"Ключ не найден в базе данных.\n"
                            f"(key_id={key_id}, tg_id={tg_id})."
                        )
                    )
                )
                return GetKeyForDeletionError(error_type=GetKeyForDeletionErrorType.NOT_FOUND_IN_DB)

        return GetKeyForDeletionSuccess(
            key=KeyDTO(
                id=key.id,
                plan_name=key.plan_name,
                end_at=key.end_at,
                is_expired=now > key.end_at
            )
        )