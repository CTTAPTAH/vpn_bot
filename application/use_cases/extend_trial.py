"""Backend-логика продление ключа пользователя временем пробного периода."""
from dataclasses import dataclass
from enum import StrEnum
from datetime import datetime, timedelta

from application.use_cases.base_use_case import BaseUseCase
from application.ports.unit_of_work import AbstractUnitOfWork
from application.ports.vpn.gateway_factory import AbstractVpnGatewayFactory
from application.errors.vpn_errors import VpnGatewayError, VpnKeyNotFoundError
from domain.entities.access_key import AccessKey
from domain.entities.payment import Payment
from domain.entities.server import Server
from domain.enums import AuditLevel, AuditEventType, PaymentType, PaymentAction, PaymentProvider, PaymentStatus
import core.utils as utils

class ExtendTrialErrorType(StrEnum):
    KEY_NOT_FOUND = "KEY_NOT_FOUND"
    KEY_NOT_OWNED = "KEY_NOT_OWNED"
    TRIAL_PLAN_NOT_FOUND = "TRIAL_PLAN_NOT_FOUND"
    VPN_SYNC_FAILED = "VPN_SYNC_FAILED"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"

@dataclass
class ExtendTrialResult:
    success: bool
    error: ExtendTrialErrorType | None = None
    plan_name: str | None = None
    num_days: int | None = None

class ExtendTrialUseCase(BaseUseCase):
    """Сценарий выдачи/возврата результата пробного периода."""
    def __init__(self, uow: AbstractUnitOfWork, gateway_factory: AbstractVpnGatewayFactory):
        self._uow = uow
        self._gateway_factory = gateway_factory

    async def execute(self, tg_id: int, username: str, key_id: int) -> ExtendTrialResult:
        """Продлить пробный период."""
        async with self._uow as uow:
            user = await uow.users.get_or_create(tg_id, username)

            key = await uow.keys.get_by_id(key_id)
            if key is None:
                await self._audit(
                    uow,
                    AuditLevel.ERROR,
                    AuditEventType.KEY_NOT_FOUND_IN_DB,
                    f"[ExtendTrialUseCase][execute]\n"
                    f"Не удалось продлить пробным периодом. ключ не найден.\n"
                    f"tg_id={tg_id}, key_id={key_id}."
                )
                return ExtendTrialResult(False, ExtendTrialErrorType.KEY_NOT_FOUND)

            if key.user_id != user.id:
                await self._audit(
                    uow,
                    AuditLevel.ERROR,
                    AuditEventType.KEY_NOT_OWNED_BY_USER,
                    f"[ExtendTrialUseCase][execute]\n"
                    f"Не удалось продлить пробным периодом. чужой ключ.\n"
                    f"tg_id={tg_id}, key_id={key.id}."
                )
                return ExtendTrialResult(False, ExtendTrialErrorType.KEY_NOT_OWNED)

            server = await uow.servers.get_by_id(key.server_id)
            if server is None:
                await self._audit(
                    uow,
                    AuditLevel.ERROR,
                    AuditEventType.SERVER_NOT_FOUND,
                    f"[ExtendTrialUseCase][_sync_vpn]\n"
                    f"Сервер не найден в БД.\n"
                    f"server_id={key.server_id}, tg_id={tg_id}."
                )

            plan = await uow.plans.get_trial()
            if plan is None:
                await self._audit(
                    uow,
                    AuditLevel.ERROR,
                    AuditEventType.PLAN_NOT_FOUND,
                    f"[ExtendTrialUseCase][execute]\n"
                    f"Пробный период не найден.\n"
                    f"tg_id={tg_id}."
                )
                return ExtendTrialResult(False, ExtendTrialErrorType.TRIAL_PLAN_NOT_FOUND)

            trial_days = utils.days_from_seconds(plan.duration_seconds)

            # Если пробного периода у пользователя не было, то продлеваем доступ
            trial_payment = await uow.payments.get_user_trial_for_update(user.id) # Блокируем платёж
            if trial_payment is not None:
                await self._audit(
                    uow,
                    AuditLevel.INFO,
                    AuditEventType.TRIAL_ALREADY_GRANTED,
                    f"[ExtendTrialUseCase][execute]\n"
                    f"Пробный период уже был выдан.\n"
                    f"tg_id={tg_id}."
                )
                return ExtendTrialResult(True, None, plan.name, trial_days)

            expiry_time = self._calculate_new_expiry(key, plan.duration_seconds)
            await self._extend_key(uow, key, plan.id, expiry_time)

            payment = await self._create_trial_payment(
                uow,
                user.id,
                key.id,
                plan.id,
                plan.price
            )

        vpn_ok = await self._sync_vpn(uow, key.id, server, expiry_time, tg_id)
        if not vpn_ok:
            return ExtendTrialResult(False, ExtendTrialErrorType.VPN_SYNC_FAILED)

        await self._audit(
            uow,
            AuditLevel.INFO,
            AuditEventType.TRIAL_GRANTED,
            f"[ExtendTrialUseCase][execute]\n"
            f"Пробный доступ выдан.\n"
            f"user_id={user.id}, key_id={key.id}, payment_id={payment.id}."
        )

        return ExtendTrialResult(True, None, plan.name, trial_days)

    def _calculate_new_expiry(self, key: AccessKey, duration_seconds: int) -> datetime:
        now = utils.utcnow()
        base_time = max(key.end_at, now)
        return base_time + timedelta(seconds=duration_seconds)

    async def _extend_key(self, uow: AbstractUnitOfWork, key: AccessKey, plan_id: int, expiry_time: datetime) -> None:
        key.plan_id = plan_id
        key.end_at = expiry_time
        await uow.keys.update(key)

    async def _create_trial_payment(self, uow: AbstractUnitOfWork, user_id: int,
                                    key_id: int, plan_id: int, price: int) -> Payment:
        now = utils.utcnow()

        payment = Payment(
            user_id=user_id,
            plan_id=plan_id,
            price=price,
            type=PaymentType.TRIAL,
            action=PaymentAction.RENEW,
            provider=PaymentProvider.INTERNAL,
            provider_payment_id=utils.new_uuid(),
            status=PaymentStatus.CONFIRMED,
            key_id=key_id,
            created_at=now,
            granted_at=now,
            paid_at=now,
        )

        await uow.payments.add(payment)
        return payment

    async def _sync_vpn(self, uow: AbstractUnitOfWork, key_id: int, server: Server,
                        expiry_time: datetime, tg_id: int) -> bool:
        try:
            vpn = await self._gateway_factory.get_gateway(server)
            vpn_email = str(key_id)
            await vpn.update_expiry(vpn_email, expiry_time)
            return True

        except VpnKeyNotFoundError:
            await self._audit(
                uow,
                AuditLevel.ERROR,
                AuditEventType.KEY_NOT_FOUND_IN_VPN,
                f"[ExtendTrialUseCase][_sync_vpn]\n"
                f"Ключ не найден."
                f"tg_id={tg_id}, key_id={key_id}."
            )
            return False

        except VpnGatewayError as e:
            await self._audit(
                uow,
                AuditLevel.ERROR,
                AuditEventType.VPN_ERROR,
                f"[ExtendTrialUseCase][_sync_vpn]\n"
                f"Неизвестная ошибка синхронизации БД с vpn при выдачи пробного периода.\n"
                f"key_id={key_id}.\n"
                f"error={e}"
            )
            return False