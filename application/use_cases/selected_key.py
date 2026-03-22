"""Backend-логика для формирования данных для отображения информации о ключе, который выбрал пользователь."""
from dataclasses import dataclass
from enum import StrEnum

from application.common.dto import KeyDTO
from application.ports.unit_of_work import AbstractUnitOfWork
from application.ports.vpn_gateway import VpnGateway
from infrastructure.xui.exceptions import XuiError
from domain.entities.audit_log import AuditLog
from domain.enums import AuditLevel, AuditEventType
from core.utils import utcnow

class SelectedKeyErrorType(StrEnum):
    """Тип ошибки при получении информации о выбранном ключе."""
    NOT_FOUND_IN_DB = "NOT_FOUND_IN_DB"
    NOT_FOUND_IN_VPN = "NOT_FOUND_IN_VPN"
    VPN_ERROR = "VPN_ERROR"

@dataclass
class SelectedKeyResult:
    success: bool
    key: KeyDTO | None = None
    vless: str | None = None
    error_type: SelectedKeyErrorType | None = None

class GetSelectedKeyUseCase:
    """Сценарий получения данных о ключе пользователя."""
    def __init__(self, uow: AbstractUnitOfWork, vpn: VpnGateway):
        self._uow = uow
        self._vpn = vpn

    async def execute(self, key_id: int, tg_id: int, server_name: str) -> SelectedKeyResult:
        now = utcnow()

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
                return SelectedKeyResult(success=False, error_type=SelectedKeyErrorType.NOT_FOUND_IN_DB)

            # Поиск ключа в xui
            vpn_key_id = str(key.id)
            try:
                # Если ключ не создан в xui, то создаём аудит ошибки
                if not await self._vpn.is_client_exists(vpn_key_id):
                    await uow.audits.add(
                        AuditLog(
                            level=AuditLevel.ERROR,
                            event_type=AuditEventType.KEY_NOT_FOUND_IN_VPN,
                            message=(
                                f"Не удалось выдать информацию о ключе.\n"
                                f"Ключ не найден в xui.\n"
                                f"(key_id={vpn_key_id}, tg_id={tg_id})."
                            )
                        )
                    )
                    return SelectedKeyResult(success=False, error_type=SelectedKeyErrorType.NOT_FOUND_IN_VPN)

                # Иначе проблем нет и получаем vless ссылку пользователя
                vless = await self._vpn.get_link(vpn_key_id, server_name)
            except XuiError as e:
                await uow.audits.add(
                    AuditLog(
                        level=AuditLevel.ERROR,
                        event_type=AuditEventType.VPN_ERROR,
                        message=(
                            f"Не удалось выдать информацию о ключе.\n"
                            f"(key_id={vpn_key_id}, tg_id={tg_id}).\n"
                            f"Ошибка: {e}."
                        )
                    )
                )
                return SelectedKeyResult(success=False, error_type=SelectedKeyErrorType.VPN_ERROR)

        return SelectedKeyResult(
            success=True,
            key=KeyDTO(
                id=key.id,
                plan_name=key.plan_name,
                end_at=key.end_at,
                is_expired=now > key.end_at
            ),
            vless=vless
        )