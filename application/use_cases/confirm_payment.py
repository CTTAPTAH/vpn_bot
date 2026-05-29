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
from application.services.server_selection import ServerSelectionService, NoAvailableServersError
from domain.enums import PaymentProvider
from domain.enums import AuditLevel, AuditEventType, PaymentStatus, PaymentAction
from domain.entities.user import User
from domain.entities.payment import Payment
from domain.entities.plan import Plan
from domain.entities.access_key import AccessKey
from domain.entities.server import Server
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
    vless_link: str | None = None
    tg_user_id: int | None = None
    tg_chat_id: int | None = None
    tg_message_id: int | None = None
    error: ConfirmPaymentErrorType | None = None

class ConfirmPaymentUseCase(BaseUseCase):
    """Сценарий выдачи/продления доступа при успешном платеже."""
    def __init__(self, uow: AbstractUnitOfWork, gateway_factory: AbstractVpnGatewayFactory,
                 selector: ServerSelectionService):
        self._uow = uow
        self._selector = selector
        self._gateway_factory = gateway_factory

    @dataclass(slots=True)
    class _PrepareResult:
        """Сохранение необходимый информации после создания ключа в БД."""
        success: bool
        payment_id: int | None = None
        action: PaymentAction | None = None
        key_id: int | None = None
        key_name: str | None = None
        server: Server | None = None
        expiry_time: datetime | None = None
        error: ConfirmPaymentErrorType | None = None

    @dataclass(slots=True)
    class _ProvisionResult:
        """Сохранение необходимый информации после создания ключа на VPN сервере."""
        success: bool
        error: ConfirmPaymentErrorType | None = None
        vless_link: str | None = None

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
                key = await uow.keys.get_by_id(payment.key_id)
                if key is None:
                    await self._audit(
                        uow,
                        AuditLevel.ERROR,
                        AuditEventType.KEY_NOT_FOUND_IN_DB,
                        f"[ConfirmPaymentUseCase][execute].\n"
                        f"Ключ не найден в БД по id платежа.\n"
                        f"tg_id={user.tg_id}, payment_id={payment.id}, key_id={payment.key_id}."
                    )
                    return ConfirmPaymentResult(success=False, error=ConfirmPaymentErrorType.KEY_NOT_FOUND)

                return ConfirmPaymentResult(
                    success=True,
                    payment_action=payment.action,
                    vless_link=key.vless_link,
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

            # Сначала создаём ключ В БД в первой транзакции
            if payment.action == PaymentAction.CREATE:
                prepare = await self._prepare_purchase(uow, user, plan, payment)

            elif payment.action == PaymentAction.RENEW:
                prepare = await self._prepare_renew(uow, payment, user, plan, payment.key_id, user.tg_id)

            if not prepare.success:
                await self._fail_payment(payment.id)
                return ConfirmPaymentResult(success=False, error=prepare.error)

        # Потом создаём ключ на VPN сервере вне транзакции. И завершаем платёж внутри второй транзакции
        if prepare.action == PaymentAction.CREATE:
            provision = await self._provision_purchase(prepare.key_id, prepare.payment_id, prepare.server,
                                                              prepare.expiry_time, prepare.key_name, user.tg_id)
            if not provision.success:
                await self._fail_payment(payment.id)
                return ConfirmPaymentResult(success=False, error=provision.error)

            return await self._finalize_purchase(prepare.key_id, prepare.payment_id, provision.vless_link)

        elif prepare.action == PaymentAction.RENEW:
            provision = await self._provision_renew(prepare.key_id, prepare.payment_id, prepare.server,
                                                    prepare.expiry_time, user.tg_id)
            if not provision.success:
                await self._fail_payment(payment.id)
                return ConfirmPaymentResult(success=False, error=provision.error)

            return await self._finalize_renew(payment.id, payment.key_id)

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
        """Создание ключа в БД. Установить статус платежа на PROCESSING."""
        # Если уже обрабатывается действие
        if payment.status != PaymentStatus.PENDING:
            await self.is_processing_audit(uow, user.tg_id, payment.id)
            return self._PrepareResult(success=False, error=ConfirmPaymentErrorType.IS_PROCESSING)

        # Установить статус платежа на PROCESSING, защита от гонок
        payment.status = PaymentStatus.PROCESSING
        await uow.payments.update(payment)

        # Выбираем север
        server_ids = await uow.servers.get_id_active_servers()
        try:
            server_id = await self._selector.select_server(uow.keys, server_ids)
        except NoAvailableServersError:
            await self._audit(
                uow,
                AuditLevel.ERROR,
                AuditEventType.NO_AVAILABLE_SERVERS,
                f"[ConfirmPaymentUseCase][_prepare_purchase]\n"
                f"Не удалось получить сервер, где будет располагаться ключ.\n"
                f"server_ids={server_ids}, tg_id={user.tg_id}, payment={payment.id}."
            )
            return self._PrepareResult(success=False, error=ConfirmPaymentErrorType.NO_AVAILABLE_SERVERS)
        server = await uow.servers.get_by_id(server_id)

        if server is None:
            await self._audit(
                uow,
                AuditLevel.ERROR,
                AuditEventType.SERVER_NOT_FOUND,
                f"[ConfirmPaymentUseCase][_prepare_purchase]\n"
                f"Сервер на найден в БД.\n"
                f"server_id={server_id}, tg_id={user.tg_id}, payment={payment.id}."
            )
            return self._PrepareResult(success=False, error=ConfirmPaymentErrorType.SERVER_NOT_FOUND)

        expiry_time = utils.add_seconds_to_now(plan.duration_seconds)
        key = AccessKey(
            user_id=user.id,
            plan_id=plan.id,
            server_id=server_id,
            end_at=expiry_time
        )
        await uow.keys.add(key)

        return self._PrepareResult(
            success=True,
            payment_id=payment.id,
            action=payment.action,
            key_id=key.id,
            key_name=server.default_key_name,
            server=server,
            expiry_time=expiry_time
        )

    async def _provision_purchase(self, key_id: int, payment_id: int, server: Server,
                                  expiry_time: datetime, key_name: str, tg_id: int) -> _ProvisionResult:

        vpn = await self._gateway_factory.get_gateway(server)
        vpn_email = str(key_id)
        try:
            await vpn.create_key(vpn_email, expiry_time)
            vless_link = await vpn.get_link(vpn_email, key_name)

        except VpnClientAlreadyExistsError:
            async with self._uow as uow:
                await self._audit(
                    uow,
                    AuditLevel.ERROR,
                    AuditEventType.VPN_KEY_CREATED,
                    f"[ConfirmPaymentUseCase][_provision_purchase]\n"
                    f"Ключ с таким email уже есть в vpn.\n"
                    f"tg_id={tg_id}, key_id={key_id}, payment_id={payment_id}."
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
                    f"tg_id={tg_id}, key_id={key_id}, payment_id={payment_id}."
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
                    f"tg_id={tg_id}, key_id={key_id}, payment_id={payment_id}.\n"
                    f"Ошибка: {e}."
                )
            return self._ProvisionResult(success=False, error=ConfirmPaymentErrorType.UNKNOWN_ERROR)

        return self._ProvisionResult(success=True, vless_link=vless_link)

    async def _finalize_purchase(self, key_id: int, payment_id: int, vless_link: str) -> ConfirmPaymentResult:
        """Добавляем vless ссылку к ключу и фиксируем платёж."""
        async with self._uow as uow:
            # Добавляем vless ссылку
            payment = await uow.payments.get_for_update(payment_id)
            key = await uow.keys.get_for_update(key_id)

            key.vless_link = vless_link
            await uow.keys.update(key)

            # Фиксируем платёж
            await self._finalize_payment(uow, payment, key.id)

            payment_ui = await uow.payment_ui_states.get_by_payment_for_update(payment.id)

            return ConfirmPaymentResult(
                success=True,
                payment_action=payment.action,
                vless_link=vless_link,
                tg_user_id=payment_ui.tg_user_id,
                tg_chat_id=payment_ui.tg_chat_id,
                tg_message_id=payment_ui.tg_message_id
            )

    # Продление доступа
    async def _prepare_renew(self, uow: AbstractUnitOfWork, payment: Payment, user: User,
                             plan: Plan, key_id: int | None, tg_id: int) -> _PrepareResult:
        # Если уже обрабатывается действие
        if payment.status != PaymentStatus.PENDING:
            await self.is_processing_audit(uow, user.tg_id, payment.id)
            return self._PrepareResult(success=False, error=ConfirmPaymentErrorType.IS_PROCESSING)

        # Обновляем статус платежа на PROCESSING, защита от гонок
        payment.status = PaymentStatus.PROCESSING
        await uow.payments.update(payment)

        # Проверка, что ключ не None
        validate_error = await self._validate_key_id(uow, key_id, tg_id, payment.id)
        if validate_error:
            return self._PrepareResult(success=False, error=validate_error)

        # Получаем ключ из БД
        key = await uow.keys.get_for_update(key_id)
        if key is None:
            await self._audit(
                uow,
                AuditLevel.ERROR,
                AuditEventType.KEY_NOT_FOUND_IN_DB,
                f"[ConfirmPaymentUseCase][_prepare_renew]\n"
                f"Ключ для продления не найден.\n"
                f"tg_id={tg_id}, key_id={key_id}, payment_id={payment.id}."
            )
            return self._PrepareResult(success=False, error=ConfirmPaymentErrorType.KEY_NOT_FOUND)

        if key.user_id != user.id:
            await self._audit(
                uow,
                AuditLevel.ERROR,
                AuditEventType.KEY_NOT_OWNED_BY_USER,
                f"[ConfirmPaymentUseCase][_prepare_renew]\n"
                f"Попытка продлить чужой ключ.\n"
                f"user_id={user.id}, key_user_id={key.user_id}, key_id={key.id}, payment_id={payment.id}."
            )
            return self._PrepareResult(success=False, error=ConfirmPaymentErrorType.KEY_NOT_FOUND)

        # Получаем сервер
        server = await uow.servers.get_by_id(key.server_id)

        if server is None:
            await self._audit(
                uow,
                AuditLevel.ERROR,
                AuditEventType.SERVER_NOT_FOUND,
                f"[ConfirmPaymentUseCase][_prepare_renew]\n"
                f"Во время выдачи доступа после оплаты не удалось найти сервер в БД.\n"
                f"server_id={key.server_id}, tg_id={tg_id}."
            )
            return self._PrepareResult(success=False, error=ConfirmPaymentErrorType.SERVER_NOT_FOUND)

        # Обновляем ключ в БД
        await self._extend_key_time(uow, key, plan.duration_seconds)

        return self._PrepareResult(
            success=True,
            payment_id=payment.id,
            action=payment.action,
            key_id=key.id,
            server=server,
            expiry_time=key.end_at
        )

    async def _validate_key_id(self, uow: AbstractUnitOfWork, key_id: int | None,
                               tg_id: int, payment_id: int) -> ConfirmPaymentErrorType | None:
        if key_id is None:
            await self._audit(
                uow,
                AuditLevel.ERROR,
                AuditEventType.SYSTEM_ERROR,
                f"[ConfirmPaymentUseCase][_validate_key_id]\n"
                f"Не удалось продлить ключ. ID ключа не был передан в функцию.\n"
                f"tg_id={tg_id}, payment_id={payment_id}."
            )
            return ConfirmPaymentErrorType.MISSING_KEY_ID

        return None

    async def _extend_key_time(self, uow: AbstractUnitOfWork, key: AccessKey, duration_seconds: int) -> None:
        now = utils.utcnow()
        if key.end_at > now:
            base_time = key.end_at
        else:
            base_time = now
        expiry_time = base_time + timedelta(seconds=duration_seconds)
        key.end_at = expiry_time
        await uow.keys.update(key)

    async def _provision_renew(self, key_id: int, payment_id: int, server: Server,
                               expiry_time: datetime, tg_id: int) -> _ProvisionResult:
        vpn = await self._gateway_factory.get_gateway(server)

        try:
            await vpn.update_expiry(str(key_id), expiry_time)
        except VpnClientAlreadyExistsError:
            async with self._uow as uow:
                await self._audit(
                    uow,
                    AuditLevel.ERROR,
                    AuditEventType.VPN_KEY_UPDATED,
                    f"[ConfirmPaymentUseCase][_provision_renew]\n"
                    f"Ключ уже существует на VPN сервере.\n"
                    f"tg_id={tg_id}, key_id={key_id}, payment_id={payment_id}."
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
                    f"tg_id={tg_id}, key_id={key_id}, payment_id={payment_id}.\n"
                    f"Ошибка: {e}."
                )
            return self._ProvisionResult(success=False, error=ConfirmPaymentErrorType.UNKNOWN_ERROR)

        return self._ProvisionResult(success=True)

    async def _finalize_renew(self, payment_id: int, key_id: int) -> ConfirmPaymentResult:
        """Продление доступа."""
        # Фиксируем платёж и доступ
        async with self._uow as uow:
            payment = await uow.payments.get_for_update(payment_id)
            await self._finalize_payment(uow, payment, key_id)

            payment_ui = await uow.payment_ui_states.get_by_payment_for_update(payment.id)
            key = await uow.keys.get_by_id(payment.key_id)
            if key is None:
                await self._audit(
                    uow,
                    AuditLevel.ERROR,
                    AuditEventType.KEY_NOT_FOUND_IN_DB,
                    f"[ConfirmPaymentUseCase][execute].\n"
                    f"Ключ не найден в БД по id платежа.\n"
                    f"payment_id={payment.id}, key_id={payment.key_id}."
                )
                return ConfirmPaymentResult(success=False, error=ConfirmPaymentErrorType.KEY_NOT_FOUND)

            return ConfirmPaymentResult(
                success=True,
                payment_action=payment.action,
                vless_link=key.vless_link,
                tg_user_id=payment_ui.tg_user_id,
                tg_chat_id=payment_ui.tg_chat_id,
                tg_message_id=payment_ui.tg_message_id
            )

    async def _finalize_payment(self, uow: AbstractUnitOfWork, payment: Payment, key_id: int):
        """Фиксация платежа после покупки или продления."""
        now = utils.utcnow()
        payment.status = PaymentStatus.CONFIRMED
        payment.paid_at = now
        payment.key_id = key_id
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