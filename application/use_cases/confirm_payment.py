"""Backend-логика для выдачи/продления доступа к серверу пользователю, потому что оплата прошла успешно."""
from dataclasses import dataclass
from enum import StrEnum
from datetime import timedelta, datetime

from application.use_cases.base_use_case import BaseUseCase
from application.ports.unit_of_work import AbstractUnitOfWork
from application.ports.vpn.gateway_factory import AbstractVpnGatewayFactory
from application.errors.vpn_errors import (
    VpnClientAlreadyExistsError,
    VpnKeyNotFoundError,
    VpnGatewayError
)
from domain.enums import PaymentProvider
from domain.enums import AuditLevel, AuditEventType, PaymentStatus, PaymentAction
from domain.entities.user import User
from domain.entities.payment import Payment
from domain.entities.plan import Plan
from domain.entities.access_key import AccessKey
from domain.entities.server import Server
from domain.entities.subscription import Subscription
import core.utils as utils

class ConfirmPaymentErrorType(StrEnum):
    """Тип ошибки при выдаче/продлении доступа."""
    PAYMENT_NOT_FOUND = "PAYMENT_NOT_FOUND"
    PAYMENT_NOT_OWNED = "PAYMENT_NOT_OWNED"
    UNSUPPORTED_PAYMENT_TYPE = "UNSUPPORTED_PAYMENT_TYPE"
    KEY_ALREADY_EXISTS = "KEY_ALREADY_EXISTS"
    KEY_NOT_FOUND = "KEY_NOT_FOUND"
    MISSING_KEY_ID = "MISSING_KEY_ID"
    NO_AVAILABLE_SERVERS = "NO_AVAILABLE_SERVERS"
    SERVER_NOT_FOUND = "SERVER_NOT_FOUND"
    PLAN_NOT_FOUND = "PLAN_NOT_FOUND"
    IS_PROCESSING = "IS_PROCESSING"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"

@dataclass
class ConfirmPaymentResult:
    success: bool
    payment_action: PaymentAction | None = None
    sub_token: str | None = None
    tg_user_id: int | None = None
    tg_chat_id: int | None = None
    tg_message_id: int | None = None
    error: ConfirmPaymentErrorType | None = None

class ConfirmPaymentUseCase(BaseUseCase):
    """Сценарий выдачи/продления доступа при успешном платеже."""
    def __init__(self, uow: AbstractUnitOfWork, gateway_factory: AbstractVpnGatewayFactory,):
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
        keys: list[AccessKey] | None = None
        servers: dict[int, Server] | None = None  # server_id -> Server
        expiry_time: datetime | None = None
        error: ConfirmPaymentErrorType | None = None

    @dataclass(slots=True)
    class _ProvisionResult:
        """Сохранение необходимый информации после создания ключей на VPN сервере."""
        success: bool
        vless_links: dict[int, str] | None = None # key_id -> vless_link
        error: ConfirmPaymentErrorType | None = None

    async def execute(self, provider: PaymentProvider, payment_provider_id: str) -> ConfirmPaymentResult:
        """Выдача доступа пользователю."""
        async with self._uow as uow:
            payment = await uow.payments.get_by_provider_and_payment_id_for_update(provider, payment_provider_id)
            if payment is None:
                await self._audit(
                    uow,
                    AuditLevel.ERROR,
                    AuditEventType.PAYMENT_NOT_FOUND,
                    f"[ConfirmPaymentUseCase][execute].\n"
                    f"Платёж не найден в БД.\n"
                    f"provider={provider}, payment_provider_id={payment_provider_id}."
                )
                return ConfirmPaymentResult(success=False, error=ConfirmPaymentErrorType.PAYMENT_NOT_FOUND)

            user = await uow.users.get_by_id_for_update(payment.user_id)

            # Проверка на корректность БД
            validate_error = await self._validate_payment(uow, payment, user, user.tg_id, payment.id)
            if validate_error:
                await self._fail_payment(payment.id)
                return validate_error

            # Не выдаём доступ повторно
            if payment.granted_at is not None:
                payment_ui = await uow.payment_ui_states.get_by_payment_for_update(payment.id)
                sub = await uow.sub.get_by_id(payment.sub_id)
                if sub is None:
                    await self._audit(
                        uow,
                        AuditLevel.ERROR,
                        AuditEventType.SUB_NOT_FOUND_IN_DB,
                        f"[ConfirmPaymentUseCase][execute].\n"
                        f"Подписка не найдена в БД по id платежа.\n"
                        f"tg_id={user.tg_id}, payment_id={payment.id}, sub_id={payment.sub_id}."
                    )
                    return ConfirmPaymentResult(success=False, error=ConfirmPaymentErrorType.KEY_NOT_FOUND)

                return ConfirmPaymentResult(
                    success=True,
                    payment_action=payment.action,
                    sub_token=sub.sub_token,
                    tg_user_id=payment_ui.tg_user_id,
                    tg_chat_id=payment_ui.tg_chat_id,
                    tg_message_id=payment_ui.tg_message_id
                )

            plan = await uow.plans.get_by_id(payment.plan_id)
            if plan is None:
                await self._audit(
                    uow,
                    AuditLevel.ERROR,
                    AuditEventType.PLAN_NOT_FOUND,
                    f"[ConfirmPaymentUseCase][execute].\n"
                    f"Тариф не найден в БД.\n"
                    f"tg_id={user.tg_id}, payment_id={payment.id}."
                )
                return ConfirmPaymentResult(success=False, error=ConfirmPaymentErrorType.PLAN_NOT_FOUND)

            # Сначала создаём подписку В БД в первой транзакции
            if payment.action == PaymentAction.CREATE:
                prepare = await self._prepare_purchase(uow, user, plan, payment)

            elif payment.action == PaymentAction.RENEW:
                prepare = await self._prepare_renew(uow, payment, user, plan, payment.sub_id, user.tg_id)

            if not prepare.success:
                await self._fail_payment(payment.id)
                return ConfirmPaymentResult(success=False, error=prepare.error)

        # Потом создаём ключи на VPN сервере вне транзакции. И завершаем платёж внутри второй транзакции
        if prepare.action == PaymentAction.CREATE:
            provision = await self._provision_purchase(prepare, user.tg_id)
            if not provision.success:
                await self._fail_payment(payment.id)
                return ConfirmPaymentResult(success=False, error=provision.error)

            return await self._finalize_purchase(provision.vless_links, prepare.payment_id,
                                                 prepare.sub_id, prepare.sub_token)

        elif prepare.action == PaymentAction.RENEW:
            provision = await self._provision_renew(prepare, user.tg_id)
            if not provision.success:
                await self._fail_payment(payment.id)
                return ConfirmPaymentResult(success=False, error=provision.error)

            return await self._finalize_renew(prepare.payment_id, prepare.sub_id, prepare.sub_token)

        else:
            await self._fail_payment(payment.id)
            return ConfirmPaymentResult(success=False, error=ConfirmPaymentErrorType.UNSUPPORTED_PAYMENT_TYPE)

    async def _validate_payment(self, uow: AbstractUnitOfWork, payment: Payment | None, user: User,
                                tg_id: int, payment_id: int) -> ConfirmPaymentResult | None:
        # Проверки на корректность платежа
        if payment.user_id != user.id:
            await self._audit(
                uow,
                AuditLevel.ERROR,
                AuditEventType.PAYMENT_NOT_OWNED_BY_USER,
                f"[ConfirmPaymentUseCase][_validate_payment].\n"
                f"Платёж имеет user_id, который не соответствует пользователю.\n"
                f"tg_id={tg_id}, payment_id={payment_id}."
            )
            return ConfirmPaymentResult(success=False, error=ConfirmPaymentErrorType.PAYMENT_NOT_OWNED)

        # Невозможно, чтобы ошибка возникла. Она для перестраховки
        if payment.action not in (PaymentAction.CREATE, PaymentAction.RENEW):
            await self._audit(
                uow,
                AuditLevel.ERROR,
                AuditEventType.PAYING_OTHER,
                f"[ConfirmPaymentUseCase][_validate_payment]\n"
                f"Ожидается действие выдачи (CREATE) или продления (RENEW) доступа.\n"
                f"tg_id={tg_id}, payment_id={payment_id}, action={payment.action}."
            )
            return ConfirmPaymentResult(success=False, error=ConfirmPaymentErrorType.UNSUPPORTED_PAYMENT_TYPE)

        return None

    # Оплата
    async def _prepare_purchase(self, uow: AbstractUnitOfWork, user: User,
                                plan: Plan, payment: Payment) -> _PrepareResult:
        """Создание подписки и ключей в БД. Установить статус платежа на PROCESSING."""
        # Если уже обрабатывается действие
        if payment.status != PaymentStatus.PENDING:
            await self.is_processing_audit(uow, user.tg_id, payment.id)
            return self._PrepareResult(success=False, error=ConfirmPaymentErrorType.IS_PROCESSING)

        # Установить статус платежа на PROCESSING, защита от гонок
        payment.status = PaymentStatus.PROCESSING
        await uow.payments.update(payment)

        # Создание подписки
        expiry_time = utils.add_seconds_to_now(plan.duration_seconds)
        sub = Subscription(
            user_id=user.id,
            plan_id=plan.id,
            end_at=expiry_time
        )
        await uow.sub.add(sub)

        # Создаём ключи на всех серверах
        servers = await uow.servers.get_active_servers()

        keys = []
        for server in servers:
            key = AccessKey(
                sub_id=sub.id,
                server_id=server.id,
                vless_link=""
            )
            await uow.keys.add(key)
            keys.append(key)
        servers_map = {server.id: server for server in servers}

        return self._PrepareResult(
            success=True,
            payment_id=payment.id,
            action=payment.action,
            sub_id=sub.id,
            sub_token=sub.sub_token,
            keys=keys,
            servers=servers_map,
            expiry_time=expiry_time
        )

    async def _provision_purchase(self, prepare: _PrepareResult, tg_id: int) -> _ProvisionResult:
        vless_links_map = {}
        for key in prepare.keys:
            server = prepare.servers[key.server_id]
            vpn = await self._gateway_factory.get_gateway(server)
            vpn_email = str(key.id)
            try:
                await vpn.create_key(vpn_email, prepare.expiry_time)
                vless_link = await vpn.get_link(vpn_email, server.default_key_name)
                vless_links_map[key.id] = vless_link

            except VpnClientAlreadyExistsError:
                async with self._uow as uow:
                    await self._audit(
                        uow,
                        AuditLevel.ERROR,
                        AuditEventType.VPN_KEY_CREATED,
                        f"[ConfirmPaymentUseCase][_provision_purchase]\n"
                        f"Ключ с таким email уже существует на vpn сервере.\n"
                        f"tg_id={tg_id}, sub_id={prepare.sub_id}, payment_id={prepare.payment_id}."
                    )
                return self._ProvisionResult(success=False, error=ConfirmPaymentErrorType.KEY_ALREADY_EXISTS)

            except VpnKeyNotFoundError:
                async with self._uow as uow:
                    await self._audit(
                        uow,
                        AuditLevel.ERROR,
                        AuditEventType.VPN_KEY_CREATED,
                        f"[ConfirmPaymentUseCase][_provision_purchase]\n"
                        f"Ключ не найден на сервере.\n"
                        f"tg_id={tg_id}, sub_id={prepare.sub_id}, payment_id={prepare.payment_id}."
                    )
                return self._ProvisionResult(success=False, error=ConfirmPaymentErrorType.KEY_NOT_FOUND)

            except VpnGatewayError as e:
                async with self._uow as uow:
                    await self._audit(
                        uow,
                        AuditLevel.ERROR,
                        AuditEventType.VPN_ERROR,
                        f"[ConfirmPaymentUseCase][_provision_purchase]\n"
                        f"Неизвестная ошибка при взаимодействии с сервером.\n"
                        f"tg_id={tg_id}, sub_id={prepare.sub_id}, payment_id={prepare.payment_id}.\n"
                        f"Ошибка: {e}."
                    )
                return self._ProvisionResult(success=False, error=ConfirmPaymentErrorType.UNKNOWN_ERROR)

        return self._ProvisionResult(success=True, vless_links=vless_links_map)

    async def _finalize_purchase(self, vless_links: dict[int, str], payment_id: int, sub_id: int,
                                 sub_token: str) -> ConfirmPaymentResult:
        """Добавляем vless ссылки к ключам и фиксируем платёж."""
        async with self._uow as uow:
            payment = await uow.payments.get_for_update(payment_id)

            # Добавляем vless ссылки всем созданным ключам
            for key_id, vless_link in vless_links.items():
                key = await uow.keys.get_for_update(key_id)

                key.vless_link = vless_link
                await uow.keys.update(key)

            # Фиксируем платёж
            await self._finalize_payment(uow, payment, sub_id)
            payment_ui = await uow.payment_ui_states.get_by_payment_for_update(payment.id)

            return ConfirmPaymentResult(
                success=True,
                payment_action=payment.action,
                sub_token=sub_token,
                tg_user_id=payment_ui.tg_user_id,
                tg_chat_id=payment_ui.tg_chat_id,
                tg_message_id=payment_ui.tg_message_id
            )

    # Продление доступа
    async def _prepare_renew(self, uow: AbstractUnitOfWork, payment: Payment, user: User,
                             plan: Plan, sub_id: int | None, tg_id: int) -> _PrepareResult:
        # Если уже обрабатывается действие
        if payment.status != PaymentStatus.PENDING:
            await self.is_processing_audit(uow, user.tg_id, payment.id)
            return self._PrepareResult(success=False, error=ConfirmPaymentErrorType.IS_PROCESSING)

        # Обновляем статус платежа на PROCESSING, защита от гонок
        payment.status = PaymentStatus.PROCESSING
        await uow.payments.update(payment)

        # Проверка, что подписка не None
        validate_error = await self._validate_sub_id(uow, sub_id, tg_id, payment.id)
        if validate_error:
            return self._PrepareResult(success=False, error=validate_error)

        # Получаем подписку из БД
        sub = await uow.sub.get_for_update(sub_id)
        if sub is None:
            await self._audit(
                uow,
                AuditLevel.ERROR,
                AuditEventType.KEY_NOT_FOUND_IN_DB,
                f"[ConfirmPaymentUseCase][_prepare_renew]\n"
                f"Подписка для продления не найден.\n"
                f"tg_id={tg_id}, sub_id={sub_id}, payment_id={payment.id}."
            )
            return self._PrepareResult(success=False, error=ConfirmPaymentErrorType.KEY_NOT_FOUND)

        if sub.user_id != user.id:
            await self._audit(
                uow,
                AuditLevel.ERROR,
                AuditEventType.KEY_NOT_OWNED_BY_USER,
                f"[ConfirmPaymentUseCase][_prepare_renew]\n"
                f"Попытка продлить чужую подписку.\n"
                f"user_id={user.id}, sub_user_id={sub.user_id}, sub_id={sub.id}, payment_id={payment.id}."
            )
            return self._PrepareResult(success=False, error=ConfirmPaymentErrorType.KEY_NOT_FOUND)

        # Обновляем подписку в БД
        await self._extend_sub_time(uow, sub, plan.duration_seconds)

        # Получаем все сервера
        keys = await uow.keys.list_by_sub(sub_id)
        server_ids = [key.server_id for key in keys]
        servers = await uow.servers.get_by_ids(server_ids)
        servers_map = {server.id: server for server in servers}

        return self._PrepareResult(
            success=True,
            payment_id=payment.id,
            action=payment.action,
            sub_id=sub.id,
            sub_token=sub.sub_token,
            keys=keys,
            servers=servers_map,
            expiry_time=sub.end_at
        )

    async def _validate_sub_id(self, uow: AbstractUnitOfWork, sub_id: int | None,
                               tg_id: int, payment_id: int) -> ConfirmPaymentErrorType | None:
        if sub_id is None:
            await self._audit(
                uow,
                AuditLevel.ERROR,
                AuditEventType.SYSTEM_ERROR,
                f"[ConfirmPaymentUseCase][_validate_sub_id]\n"
                f"Не удалось продлить ключ. ID ключа не был передан в функцию.\n"
                f"tg_id={tg_id}, payment_id={payment_id}."
            )
            return ConfirmPaymentErrorType.MISSING_KEY_ID

        return None

    async def _extend_sub_time(self, uow: AbstractUnitOfWork, sub: Subscription, duration_seconds: int) -> None:
        now = utils.utcnow()
        if sub.end_at > now:
            base_time = sub.end_at
        else:
            base_time = now
        expiry_time = base_time + timedelta(seconds=duration_seconds)
        sub.end_at = expiry_time
        await uow.sub.update(sub)

    async def _provision_renew(self, prepare: _PrepareResult, tg_id: int) -> _ProvisionResult:
        for key in prepare.keys:
            server = prepare.servers[key.server_id]
            vpn = await self._gateway_factory.get_gateway(server)

            try:
                await vpn.update_expiry(str(key.id), prepare.expiry_time)
            except VpnKeyNotFoundError:
                async with self._uow as uow:
                    await self._audit(
                        uow,
                        AuditLevel.ERROR,
                        AuditEventType.VPN_KEY_UPDATED,
                        f"[ConfirmPaymentUseCase][_provision_renew]\n"
                        f"Подписка не найдена.\n"
                        f"tg_id={tg_id}, sub_id={prepare.sub_id}, payment_id={prepare.payment_id}."
                    )
                return self._ProvisionResult(success=False, error=ConfirmPaymentErrorType.KEY_NOT_FOUND)
            except VpnGatewayError as e:
                async with self._uow as uow:
                    await self._audit(
                        uow,
                        AuditLevel.ERROR,
                        AuditEventType.VPN_ERROR,
                        f"[ConfirmPaymentUseCase][_provision_renew]\n"
                        f"Неизвестная ошибка.\n"
                        f"tg_id={tg_id}, sub_id={prepare.sub_id}, payment_id={prepare.payment_id}.\n"
                        f"Ошибка: {e}."
                    )
                return self._ProvisionResult(success=False, error=ConfirmPaymentErrorType.UNKNOWN_ERROR)

        return self._ProvisionResult(success=True)

    async def _finalize_renew(self, payment_id: int, sub_id: int, sub_token: str) -> ConfirmPaymentResult:
        """Продление доступа."""
        # Фиксируем платёж и доступ
        async with self._uow as uow:
            payment = await uow.payments.get_for_update(payment_id)
            await self._finalize_payment(uow, payment, sub_id)

            payment_ui = await uow.payment_ui_states.get_by_payment_for_update(payment.id)

            return ConfirmPaymentResult(
                success=True,
                payment_action=payment.action,
                sub_token=sub_token,
                tg_user_id=payment_ui.tg_user_id,
                tg_chat_id=payment_ui.tg_chat_id,
                tg_message_id=payment_ui.tg_message_id
            )

    async def _finalize_payment(self, uow: AbstractUnitOfWork, payment: Payment, sub_id: int):
        """Фиксация платежа после покупки или продления."""
        now = utils.utcnow()
        payment.status = PaymentStatus.CONFIRMED
        payment.paid_at = now
        payment.sub_id = sub_id
        payment.granted_at = now
        await uow.payments.update(payment)

    async def _fail_payment(self, payment_id: int):
        async with self._uow as uow:
            payment = await uow.payments.get_for_update(payment_id)
            payment.status = PaymentStatus.FAILED
            await uow.payments.update(payment)

    async def is_processing_audit(self, uow: AbstractUnitOfWork, tg_id: int, payment_id: int) -> None:
        await self._audit(
            uow,
            AuditLevel.WARNING,
            AuditEventType.IS_PROCESSING,
            f"[ConfirmPaymentUseCase][_prepare_purchase]\n"
            f"Гонка. Этот use_case уже выполняется.\n"
            f"tg_id={tg_id}, payment={payment_id}."
        )