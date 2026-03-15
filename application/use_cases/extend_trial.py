"""Backend-логика продление ключа пользователя временем пробного периода."""
from dataclasses import dataclass
from enum import StrEnum
from uuid import uuid4
from datetime import datetime, timedelta

from application.ports.unit_of_work import AbstractUnitOfWork
from application.ports.vpn_gateway import VpnGateway
from domain.entities.audit_log import AuditLog
from domain.entities.access_key import AccessKey
from domain.entities.user import User
from domain.entities.plan import Plan
from domain.entities.payment import Payment
from domain.enums import AuditLevel, AuditEventType, PaymentType, PaymentAction, PaymentProvider, PaymentStatus
import core.utils as utils

class ExtendTrialErrorType(StrEnum):
    """Тип ошибки во время продления ключе пробным периодом."""
    KEY_NOT_FOUND_IN_DB = "KEY_NOT_FOUND_IN_DB"
    KEY_NOT_FOUND_IN_XUI = "KEY_NOT_FOUND_IN_XUI"
    PAYMENT_NOT_OWNED = "PAYMENT_NOT_OWNED"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"

class ExtendTrialResult:
    """Базовый класс для результатов: ошибка или успех."""
    pass

@dataclass
class ExtendTrialSuccess(ExtendTrialResult):
    key_name: str
    num_days: int

@dataclass
class ExtendTrialError(ExtendTrialResult):
    error_type: ExtendTrialErrorType

class ExtendTrialUseCase:
    """Сценарий продления выбранного ключа пробным периодом."""
    def __init__(self, uow: AbstractUnitOfWork, vpn: VpnGateway):
        self._uow = uow
        self._vpn = vpn

    async def _create_trial_payment(self, uow: AbstractUnitOfWork, user: User,
                                    plan: Plan, key: AccessKey, now: datetime) -> Payment:
        """Создаёт платеж для идемпотентности пробного периода."""
        payment = Payment(
            user_id=user.id,
            plan_id=plan.id,
            price=plan.price,
            type=PaymentType.TRIAL,
            action=PaymentAction.RENEW,
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

    async def _sync_key_with_xui(self, uow: AbstractUnitOfWork, key: AccessKey,
                            payment: Payment, expiry_time: datetime) -> ExtendTrialErrorType | None:
        """Создаёт ключ в XUI и логирует ошибки."""
        vpn_email = str(key.id)
        try:
            if not await self._vpn.is_client_exists(vpn_email):
                await uow.audits.add(
                    AuditLog(
                        level=AuditLevel.ERROR,
                        event_type=AuditEventType.XUI_UPDATE,
                        message=f"Ключ не найден в XUI. Не удалось продлить доступ через пробный период.\n"
                                f"user_id={key.user_id}, key_id={key.id}, payment_id={payment.id}"
                    )
                )
                return ExtendTrialErrorType.KEY_NOT_FOUND_IN_XUI

            await self._vpn.update_expiry(vpn_email, expiry_time)
        except Exception as e:
            await uow.audits.add(
                AuditLog(
                    level=AuditLevel.ERROR,
                    event_type=AuditEventType.XUI_UPDATE,
                    message=f"Ошибка продления ключа в XUI.\n"
                            f"user_id={key.user_id}, key_id={key.id}, payment_id={payment.id}, Ошибка: {e}"
                )
            )
            return ExtendTrialErrorType.UNKNOWN_ERROR

        return None

    async def execute(self, tg_id: int, username: str, key_id: int) -> ExtendTrialResult:
        """Продлить пробный период."""
        async with self._uow as uow:
            user = await uow.users.get_or_create(tg_id, username)
            payment = await uow.payments.get_user_trial(user.id)
            plan = await uow.plans.get_trial()
            key = await uow.keys.get_by_id(key_id)

            if key is None:
                await uow.audits.add(
                    AuditLog(
                        level=AuditLevel.ERROR,
                        event_type=AuditEventType.KEY_NOT_FOUND_IN_DB,
                        message=(
                            f"Пользователь попытался продлить ключ за счёт пробного периода, но ключ не найден в БД.\n"
                            f"tg_id={tg_id}."
                        )
                    )
                )
                return ExtendTrialError(error_type=ExtendTrialErrorType.KEY_NOT_FOUND_IN_DB)

            trial_days = utils.days_from_seconds(plan.duration_seconds)

            # Если пробного периода у пользователя не было, то продлеваем доступ
            if payment is None:
                now = utils.utcnow_naive()

                base_time = max(key.end_at, now)
                expiry_time = base_time + timedelta(seconds=plan.duration_seconds)

                key.plan_id = plan.id
                key.end_at = expiry_time

                await uow.keys.update(key)
                payment = await self._create_trial_payment(uow, user, plan, key, now)

                # Синхронизация с XUI
                vpn_error = await self._sync_key_with_xui(uow, key, payment, expiry_time)
                if vpn_error is not None:
                    return ExtendTrialError(error_type=vpn_error)

            return ExtendTrialSuccess(key_name=plan.name, num_days=trial_days)