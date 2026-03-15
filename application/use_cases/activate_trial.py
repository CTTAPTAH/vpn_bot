"""Backend-логика выдачи пробного периода."""
from dataclasses import dataclass
from enum import StrEnum
from uuid import uuid4
from datetime import datetime

from application.ports.unit_of_work import AbstractUnitOfWork
from application.ports.vpn_gateway import VpnGateway
from application.common.dto import KeyDTO
from domain.entities.audit_log import AuditLog
from domain.entities.access_key import AccessKey
from domain.entities.user import User
from domain.entities.plan import Plan
from domain.entities.payment import Payment
from domain.enums import AuditLevel, AuditEventType, PaymentType, PaymentAction, PaymentProvider, PaymentStatus
import core.utils as utils

class ActiveTrialErrorType(StrEnum):
    """Тип ошибки во время выдачи пробного периода."""
    KEY_ALREADY_EXISTS = "KEY_ALREADY_EXISTS"
    KEY_NOT_FOUND = "KEY_NOT_FOUND"
    PAYMENT_NOT_OWNED = "PAYMENT_NOT_OWNED"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"

class ActiveTrialResult:
    """Базовый класс для результатов: ошибка или успех."""
    pass

@dataclass
class ActiveTrialSuccess(ActiveTrialResult):
    num_days: int
    vless: str

@dataclass
class ActiveTrialError(ActiveTrialResult):
    error_type: ActiveTrialErrorType

@dataclass
class ActiveTrialChooseKey(ActiveTrialResult):
    count_key: int
    keys: list[KeyDTO]

class ActiveTrialUseCase:
    """Сценарий выдачи пробного периода."""
    def __init__(self, uow: AbstractUnitOfWork, vpn: VpnGateway):
        self._uow = uow
        self._vpn = vpn

    async def _create_trial_key(self, uow: AbstractUnitOfWork, user: User, plan: Plan,
                                now: datetime, expiry_time: datetime) -> AccessKey:
        """Создаёт ключ пробного периода в БД."""
        key = AccessKey(
            user_id=user.id,
            plan_id=plan.id,
            end_at=expiry_time,
            start_at=now,
            price_at_purchase=plan.price
        )
        await uow.keys.add(key)
        return key

    async def _create_trial_payment(self, uow: AbstractUnitOfWork, user: User,
                                    plan: Plan, key: AccessKey, now: datetime) -> Payment:
        """Создаёт платеж для идемпотентности пробного периода."""
        payment = Payment(
            user_id=user.id,
            plan_id=plan.id,
            price=plan.price,
            type=PaymentType.TRIAL,
            action=PaymentAction.CREATE,
            provider=PaymentProvider.INTERNAL,
            provider_payment_id=str(uuid4()),
            status=PaymentStatus.COMPLETED,
            key_id=key.id,
            created_at=now,
            granted_at=now,
            paid_at=now
        )
        await uow.payments.add(payment)
        return payment

    async def _update_xui_expiry(self, uow: AbstractUnitOfWork, key: AccessKey,
                            payment: Payment, expiry_time: datetime) -> ActiveTrialErrorType | None:
        """Создаёт ключ в XUI и логирует ошибки."""
        vpn_email = str(key.id)
        try:
            if await self._vpn.is_client_exists(vpn_email):
                await uow.audits.add(
                    AuditLog(
                        level=AuditLevel.ERROR,
                        event_type=AuditEventType.XUI_ADD,
                        message=f"Ключ уже существует в XUI. "
                                f"user_id={key.user_id}, key_id={key.id}, payment_id={payment.id}"
                    )
                )
                return ActiveTrialErrorType.KEY_ALREADY_EXISTS

            await self._vpn.create_key(vpn_email, expiry_time)
        except Exception as e:
            await uow.audits.add(
                AuditLog(
                    level=AuditLevel.ERROR,
                    event_type=AuditEventType.XUI_ADD,
                    message=f"Ошибка создания ключа в XUI. "
                            f"user_id={key.user_id}, key_id={key.id}, payment_id={payment.id}, Ошибка: {e}"
                )
            )
            return ActiveTrialErrorType.UNKNOWN_ERROR

        return None

    async def _get_vless_link(self, uow: AbstractUnitOfWork, vpn_email: str,
                              key: AccessKey, payment: Payment) -> str | ActiveTrialErrorType:
        """Получение VLESS ссылки для ключа."""
        try:
            if not await self._vpn.is_client_exists(vpn_email):
                await uow.audits.add(
                    AuditLog(
                        level=AuditLevel.ERROR,
                        event_type=AuditEventType.KEY_NOT_FOUND_IN_VPN,
                        message=f"Ключ отсутствует в XUI. "
                                f"user_id={key.user_id}, key_id={key.id}, payment_id={payment.id}"
                    )
                )
                return ActiveTrialErrorType.KEY_NOT_FOUND

            return await self._vpn.get_link(vpn_email)
        except Exception as e:
            await uow.audits.add(
                AuditLog(
                    level=AuditLevel.ERROR,
                    event_type=AuditEventType.XUI_GET,
                    message=f"Ошибка получения ссылки VLESS. "
                            f"user_id={key.user_id}, key_id={key.id}, payment_id={payment.id}, Ошибка: {e}"
                )
            )
            return ActiveTrialErrorType.UNKNOWN_ERROR

    async def execute(self, tg_id: int, username: str) -> ActiveTrialResult:
        """Выдать пробный период."""
        async with self._uow as uow:
            user = await uow.users.get_or_create(tg_id, username)
            payment = await uow.payments.get_user_trial(user.id)
            plan = await uow.plans.get_trial()

            now = utils.utcnow_naive()
            expiry_time = utils.add_seconds_to_now_naive(plan.duration_seconds)
            trial_days = utils.days_from_seconds(plan.duration_seconds)

            # Если пробный период у пользователя не был, то выдаём доступ
            if payment is None:
                count_all_keys = await uow.keys.count_all_keys(user.id)

                # Если превышен лимит по ключам, то предлагаем продление
                if count_all_keys >= 5:
                    views = await uow.keys.list_view_by_user(user.id)
                    keys_dto = [
                        KeyDTO(
                            id=v.id,
                            plan_name=v.plan_name,
                            end_at=v.end_at,
                            is_expired=now > v.end_at
                        )
                        for v in views
                    ]
                    return ActiveTrialChooseKey(count_key=count_all_keys, keys=keys_dto)

                key = await self._create_trial_key(uow, user, plan, now, expiry_time)
                payment = await self._create_trial_payment(uow, user, plan, key, now)

                if payment.user_id != user.id:
                    await uow.audits.add(
                        AuditLog(
                            level=AuditLevel.ERROR,
                            event_type=AuditEventType.PAYMENT_NOT_FOUND,
                            message=(
                                f"Платёж имеет user_id, который не соответствует пользователю.\n"
                                f"tg_id={tg_id}, payment_id={payment.id}."
                            )
                        )
                    )
                    return ActiveTrialError(error_type=ActiveTrialErrorType.PAYMENT_NOT_OWNED)

                # Синхронизация с XUI
                vpn_error = await self._update_xui_expiry(uow, key, payment, expiry_time)
                if vpn_error is not None:
                    return ActiveTrialError(error_type=vpn_error)
            else:
                key = await uow.keys.get_by_id(payment.key_id)

            # Получение ключ-ссылки для пробного периода
            vpn_email = str(key.id)
            vless_link_or_error = await self._get_vless_link(uow, vpn_email, key, payment)
            if isinstance(vless_link_or_error, ActiveTrialErrorType):
                return ActiveTrialError(error_type=vless_link_or_error)

            return ActiveTrialSuccess(num_days=trial_days, vless=vless_link_or_error)