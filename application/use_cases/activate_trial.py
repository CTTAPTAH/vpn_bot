"""Backend-логика выдачи пробного периода."""
from dataclasses import dataclass
from enum import StrEnum
from datetime import datetime, timedelta

from application.use_cases.base_use_case import BaseUseCase
from application.ports.unit_of_work import AbstractUnitOfWork
from application.ports.vpn.gateway_factory import AbstractVpnGatewayFactory
from application.errors.vpn_errors import (
    VpnClientAlreadyExistsError,
    VpnKeyNotFoundError,
    VpnGatewayError
)
from domain.entities.access_key import AccessKey
from domain.entities.user import User
from domain.entities.plan import Plan
from domain.entities.payment import Payment
from domain.entities.server import Server
from domain.entities.subscription import Subscription
from domain.enums import AuditLevel, AuditEventType, PaymentType, PaymentAction, PaymentProvider, PaymentStatus
import core.utils as utils

class ActivateTrialErrorType(StrEnum):
    """Тип ошибки во время выдачи пробного периода."""
    SUB_ALREADY_EXISTS = "SUB_ALREADY_EXISTS"
    SUB_NOT_FOUND = "SUB_NOT_FOUND"
    KEY_ALREADY_EXISTS = "KEY_ALREADY_EXISTS"
    KEY_NOT_FOUND = "KEY_NOT_FOUND"
    PLAN_NOT_FOUND = "PLAN_NOT_FOUND"
    PAYMENT_NOT_OWNED = "PAYMENT_NOT_OWNED"
    PAYING_OTHER = "PAYING_OTHER"
    IS_PROCESSING = "IS_PROCESSING"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"

@dataclass(slots=True)
class ActivateTrialResult:
    success: bool
    action: PaymentAction | None = None
    sub_token: str | None = None
    sub_end_at: datetime | None = None
    error: ActivateTrialErrorType | None = None

class ActivateTrialUseCase(BaseUseCase):
    """Сценарий выдачи пробного периода."""
    def __init__(self, uow: AbstractUnitOfWork, gateway_factory: AbstractVpnGatewayFactory):
        self._uow = uow
        self._gateway_factory = gateway_factory

    @dataclass(slots=True)
    class _PrepareResult:
        """Сохранение необходимый информации после создания ключей в БД."""
        success: bool
        payment_id: int | None = None
        action: PaymentAction | None = None
        sub_id: int | None = None
        sub_token: str | None = None
        sub_end_at: datetime | None = None
        keys: list[AccessKey] | None = None
        servers: dict[int, Server] | None = None  # server_id -> Server
        expiry_time: datetime | None = None
        error: ActivateTrialErrorType | None = None

    @dataclass(slots=True)
    class _ProvisionResult:
        """Сохранение необходимый информации после создания ключей на VPN сервере."""
        success: bool
        vless_links: dict[int, str] | None = None  # key_id -> vless_link
        error: ActivateTrialErrorType | None = None

    async def execute(self, tg_id: int, username: str) -> ActivateTrialResult:
        """Выдать пробный период."""
        # В первой транзакции создаём подписку в БД или продлеваем доступ
        async with self._uow as uow:
            user = await uow.users.get_or_create(tg_id, username)
            payment = await uow.payments.get_user_trial_for_update(user.id)
            plan = await uow.plans.get_trial()

            # Если платёж уже существует и доступ выдан, то не выдаём повторно
            if payment and payment.granted_at:
                sub = await uow.sub.get_by_user_id(user.id)
                if sub is None:
                    await self._audit(
                        uow,
                        AuditLevel.ERROR,
                        AuditEventType.SUB_NOT_FOUND_IN_DB,
                        f"[ActiveTrialUseCase][execute]\n"
                        f"Подписка не найдена в БД, хотя платёж с пробным периодом уже существует "
                        f"и имеет дату выдачи.\n"
                        f"tg_id={tg_id}, payment_id={payment.id}."
                    )
                    return ActivateTrialResult(success=False, error=ActivateTrialErrorType.SUB_NOT_FOUND)

                return ActivateTrialResult(
                    success=True,
                    action=payment.action,
                    sub_token=sub.sub_token,
                    sub_end_at=sub.end_at
                )

            if payment and payment.status is PaymentStatus.PROCESSING:
                await self._audit(
                    uow,
                    AuditLevel.ERROR,
                    AuditEventType.SUB_NOT_FOUND_IN_DB,
                    f"[ActiveTrialUseCase][execute]\n"
                    f"Платёж в статусе {PaymentStatus.PROCESSING} во время выдачи пробного периода.\n"
                    f"tg_id={tg_id}, payment_id={payment.id}."
                )
                return ActivateTrialResult(success=False, error=ActivateTrialErrorType.IS_PROCESSING)

            # Проверка, что тариф пробного периода существует
            if plan is None:
                await self._audit(
                    uow,
                    AuditLevel.ERROR,
                    AuditEventType.PLAN_NOT_FOUND,
                    f"[ActiveTrialUseCase][execute]\n"
                    f"Пробный период не найден в БД.\n"
                    f"tg_id={tg_id}."
                )
                return ActivateTrialResult(success=False, error=ActivateTrialErrorType.PLAN_NOT_FOUND)

            # Выдача доступа
            prepare = await self._prepare(uow, payment, user, plan, tg_id)

            if not prepare.success:
                return ActivateTrialResult(success=False, error=prepare.error)

        # Потом создаём ключи на VPN сервере вне транзакции. И завершаем платёж внутри второй транзакции
        provision = await self._provision(prepare, user.tg_id)
        if not provision.success:
            return ActivateTrialResult(success=False, error=provision.error)

        return await self._finalize(
            payment_id=prepare.payment_id,
            sub_id=prepare.sub_id,
            sub_token=prepare.sub_token,
            sub_end_at=prepare.sub_end_at,
            vless_links=provision.vless_links
        )

    async def _prepare(self, uow: AbstractUnitOfWork, payment: Payment, user: User, plan: Plan,
                       tg_id: int) -> _PrepareResult:
        """Выдача доступа в БД."""
        # Узнаём есть ли подписка у пользователя
        sub = await uow.sub.get_by_user_id(user.id)
        action = PaymentAction.CREATE if not sub else PaymentAction.RENEW

        # Если платежа нет, то создать. Но если он каким-то образом существует, то установить status на PROCESSING
        if not payment:
            payment = Payment(
                user_id=user.id,
                plan_id=plan.id,
                price=plan.price,
                type=PaymentType.TRIAL,
                action=action,
                provider=PaymentProvider.INTERNAL,
                provider_payment_id=utils.new_uuid(),
                status=PaymentStatus.PROCESSING
            )
            await uow.payments.add(payment)
        else:
            payment.status = PaymentStatus.PROCESSING
            await uow.payments.update(payment)

        # Невозможно, чтобы ошибка возникла. Она для перестраховки
        if action not in (PaymentAction.CREATE, PaymentAction.RENEW):
            await self._audit(
                uow,
                AuditLevel.ERROR,
                AuditEventType.PAYING_OTHER,
                f"[ActiveTrialUseCase][execute]\n"
                f"Неожиданный PaymentAction во время выдачи пробного периода.\n"
                f"tg_id={tg_id}, payment_id={payment.id}, payment_action={action}."
            )
            return self._PrepareResult(success=False, error=ActivateTrialErrorType.PAYING_OTHER)

        # Создание или продление подписки
        keys = []
        servers_map = {}
        if action is PaymentAction.CREATE:
            # Создание подписки
            sub = Subscription(
                user_id=user.id,
                plan_id=plan.id,
                end_at=utils.add_seconds_to_now(plan.duration_seconds)
            )
            await uow.sub.add(sub)

            # Создание ключей
            servers = await uow.servers.get_active_servers()
            keys = []
            for server in servers:
                key = AccessKey(
                    server_id=server.id,
                    sub_id=sub.id,
                    vless_link=""
                )
                await uow.keys.add(key)
                keys.append(key)
            servers_map = {server.id: server for server in servers}

        elif action is PaymentAction.RENEW:
            await self._extend_sub_time(uow, sub, plan.duration_seconds)
            keys = await uow.keys.list_by_sub(sub.id)
            server_ids = [key.server_id for key in keys]
            servers = await uow.servers.get_by_ids(server_ids)
            servers_map = {server.id: server for server in servers}

        return self._PrepareResult(
            success=True,
            payment_id=payment.id,
            action=action,
            sub_id=sub.id,
            sub_token=sub.sub_token,
            sub_end_at=sub.end_at,
            keys=keys,
            servers=servers_map,
            expiry_time=sub.end_at
        )

    async def _extend_sub_time(self, uow: AbstractUnitOfWork, sub: Subscription, duration_seconds: int) -> None:
        now = utils.utcnow()
        if sub.end_at > now:
            base_time = sub.end_at
        else:
            base_time = now
        expiry_time = base_time + timedelta(seconds=duration_seconds)
        sub.end_at = expiry_time
        await uow.sub.update(sub)

    async def _provision(self, prepare: _PrepareResult, tg_id: int) -> _ProvisionResult:
        vless_links = {}
        for key in prepare.keys:
            server = prepare.servers[key.server_id]
            vpn = await self._gateway_factory.get_gateway(server)
            email = str(key.id)

            try:
                if prepare.action is PaymentAction.CREATE:
                    await vpn.create_key(email, prepare.expiry_time)
                    vless_link = await vpn.get_link(email, server.default_key_name)
                    vless_links[key.id] = vless_link
                else:
                    await vpn.update_expiry(email, prepare.expiry_time)

            except VpnClientAlreadyExistsError:
                async with self._uow as uow:
                    await self._audit(
                        uow,
                        AuditLevel.ERROR,
                        AuditEventType.VPN_KEY_CREATED,
                        f"[ActiveTrialUseCase][_provision]\n"
                        f"Ключ с таким email уже существует на vpn сервере.\n"
                        f"tg_id={tg_id}, sub_id={prepare.sub_id}, payment_id={prepare.payment_id}."
                    )
                return self._ProvisionResult(success=False, error=ActivateTrialErrorType.KEY_ALREADY_EXISTS)

            except VpnKeyNotFoundError:
                async with self._uow as uow:
                    await self._audit(
                        uow,
                        AuditLevel.ERROR,
                        AuditEventType.VPN_KEY_CREATED,
                        f"[ActiveTrialUseCase][_provision]\n"
                        f"Ключ не найден на сервере.\n"
                        f"tg_id={tg_id}, sub_id={prepare.sub_id}, payment_id={prepare.payment_id}."
                    )
                return self._ProvisionResult(success=False, error=ActivateTrialErrorType.KEY_NOT_FOUND)

            except VpnGatewayError as e:
                async with self._uow as uow:
                    await self._audit(
                        uow,
                        AuditLevel.ERROR,
                        AuditEventType.VPN_ERROR,
                        f"[ActiveTrialUseCase][_provision]\n"
                        f"Неизвестная ошибка при взаимодействии с сервером.\n"
                        f"tg_id={tg_id}, sub_id={prepare.sub_id}, payment_id={prepare.payment_id}.\n"
                        f"Ошибка: {e}."
                    )
                return self._ProvisionResult(success=False, error=ActivateTrialErrorType.UNKNOWN_ERROR)

        return self._ProvisionResult(success=True, vless_links=vless_links)

    async def _finalize(self, payment_id: int, sub_id: int, sub_token: str, sub_end_at: datetime,
                        vless_links: dict[int, str]) -> ActivateTrialResult:
        async with self._uow as uow:
            payment = await uow.payments.get_for_update(payment_id)

            if vless_links:
                for key_id, vless_link in vless_links.items():
                    key = await uow.keys.get_for_update(key_id)
                    key.vless_link = vless_link
                    await uow.keys.update(key)

            # Фиксируем платёж
            await self._finalize_payment(uow, payment, sub_id)

        return ActivateTrialResult(
            success=True,
            action=payment.action,
            sub_token=sub_token,
            sub_end_at=sub_end_at
        )

    async def _finalize_payment(self, uow: AbstractUnitOfWork, payment: Payment, sub_id: int):
        """Фиксация платежа после покупки или продления."""
        now = utils.utcnow()
        payment.status = PaymentStatus.CONFIRMED
        payment.paid_at = now
        payment.sub_id = sub_id
        payment.granted_at = now
        await uow.payments.update(payment)