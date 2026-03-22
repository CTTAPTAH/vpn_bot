"""Backend-логика для выдачи/продления доступа к серверу пользователю, потому что оплата прошла успешно."""
from dataclasses import dataclass
from enum import StrEnum
from datetime import timedelta, datetime

from application.ports.unit_of_work import AbstractUnitOfWork
from application.ports.vpn_gateway import VpnGateway
from application.errors.vpn_errors import (
    VpnClientAlreadyExistsError,
    VpnGatewayError
)
from domain.enums import AuditLevel, AuditEventType, PaymentStatus, PaymentAction
from domain.entities.audit_log import AuditLog
from domain.entities.user import User
from domain.entities.payment import Payment
from domain.entities.plan import Plan
from domain.entities.access_key import AccessKey
import core.utils as utils

class ConfirmPaymentErrorType(StrEnum):
    """Тип ошибки при получении информации о выбранном ключе."""
    PAYMENT_NOT_FOUND = "PAYMENT_NOT_FOUND"
    PAYMENT_NOT_OWNED = "PAYMENT_NOT_OWNED"
    UNSUPPORTED_PAYMENT_TYPE = "UNSUPPORTED_PAYMENT_TYPE"
    KEY_ALREADY_EXISTS = "KEY_ALREADY_EXISTS"
    KEY_NOT_FOUND = "KEY_NOT_FOUND"
    MISSING_KEY_ID = "MISSING_KEY_ID"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"

@dataclass
class ConfirmPaymentResult:
    success: bool
    error: ConfirmPaymentErrorType | None = None

class ConfirmPaymentUseCase:
    """Сценарий выдачи/продления доступа при успешном платеже."""
    def __init__(self, uow: AbstractUnitOfWork, vpn: VpnGateway):
        self._uow = uow
        self._vpn = vpn

    @dataclass(slots=True)
    class _PrepareResult:
        """Сохранение необходимый информации после создания ключа в БД."""
        success: bool
        payment_id: int | None = None
        action: PaymentAction | None = None
        key_id: int | None = None
        expiry_time: datetime | None = None
        error: ConfirmPaymentErrorType | None = None

    @dataclass(slots=True)
    class _ProvisionResult:
        """Сохранение необходимый информации после создания ключа на VPN сервере."""
        success: bool
        error: ConfirmPaymentErrorType | None = None
        vless_link: str | None = None

    async def execute(self, tg_id: int, username: str, payment_id: int, server_name: str,
                      *, key_id: int | None = None) -> ConfirmPaymentResult:
        """Выдача доступа пользователю."""
        async with self._uow as uow:
            payment = await uow.payments.get_for_update(payment_id)
            user = await uow.users.get_or_create(tg_id, username)

            # Проверка на корректность БД
            validate_error = await self._validate_payment(uow, payment, user, tg_id, payment_id)
            if validate_error:
                return validate_error

            # Не выдаём доступ повторно
            if payment.granted_at is not None or payment.status == PaymentStatus.PROCESSING:
                return ConfirmPaymentResult(success=True)

            plan = await uow.plans.get_by_id(payment.plan_id)

            # Сначала создаём ключ В БД в первой транзакции
            if payment.action == PaymentAction.CREATE:
                prepare = await self._prepare_purchase(uow, user, plan, payment)

            elif payment.action == PaymentAction.RENEW:
                 prepare = await self._prepare_renew(uow, payment, user, plan, key_id, tg_id)

            if not prepare.success:
                return ConfirmPaymentResult(success=False, error=prepare.error)

        # Потом создаём ключ на VPN сервере вне транзакции. И завершаем платёж внутри второй транзакции
        if prepare.action == PaymentAction.CREATE:
            provision = await self._provision_purchase(prepare.key_id, prepare.payment_id,
                                                              prepare.expiry_time, server_name, tg_id)
            if not provision.success:
                return ConfirmPaymentResult(success=False, error=provision.error)

            await self._finalize_purchase(prepare.key_id, prepare.payment_id, provision.vless_link)

        elif prepare.action == PaymentAction.RENEW:
            provision = await self._provision_renew(prepare.key_id, prepare.payment_id, prepare.expiry_time, tg_id)
            if not provision.success:
                return ConfirmPaymentResult(success=False, error=provision.error)

            await self._finalize_renew(payment_id, key_id)

        return ConfirmPaymentResult(success=True)

    async def _validate_payment(self, uow: AbstractUnitOfWork, payment: Payment | None, user: User,
                                tg_id: int, payment_id: int) -> ConfirmPaymentResult | None:
        # Проверки на корректность платежа
        if payment is None:
            await self._audit(
                uow,
                AuditLevel.ERROR,
                AuditEventType.PAYMENT_NOT_FOUND,
                f"Пользователь оплатил доступ, но платёж не найден в БД. tg_id={tg_id}, "
                f"payment_id={payment_id}, user_id={user.id}."
            )
            return ConfirmPaymentResult(success=False, error=ConfirmPaymentErrorType.PAYMENT_NOT_FOUND)

        if payment.user_id != user.id:
            await self._audit(
                uow,
                AuditLevel.ERROR,
                AuditEventType.PAYMENT_NOT_OWNED_BY_USER,
                f"Платёж имеет user_id, который не соответствует пользователю. "
                f"tg_id={tg_id}, payment_id={payment_id}, user_id={user.id}."
            )
            return ConfirmPaymentResult(success=False, error=ConfirmPaymentErrorType.PAYMENT_NOT_OWNED)

        # Невозможно, чтобы ошибка возникла. Она для перестраховки
        if payment.action not in (PaymentAction.CREATE, PaymentAction.RENEW):
            await self._audit(
                uow,
                AuditLevel.ERROR,
                AuditEventType.PAYING_OTHER,
                f"Пользователь оплатил доступ, но это не покупка и не продление. "
                f"tg_id={tg_id}, payment_id={payment_id}."
            )
            return ConfirmPaymentResult(success=False, error=ConfirmPaymentErrorType.UNSUPPORTED_PAYMENT_TYPE)

        return None

    # Оплата
    async def _prepare_purchase(self, uow: AbstractUnitOfWork, user: User,
                                plan: Plan, payment: Payment) -> _PrepareResult:
        """Создание ключа в БД. Установить статус платежа на PROCESSING."""
        # Установить статус платежа на PROCESSING
        payment.status = PaymentStatus.PROCESSING
        await uow.payments.update(payment)

        expiry_time = utils.add_seconds_to_now(plan.duration_seconds)
        key = AccessKey(
            user_id=user.id,
            plan_id=plan.id,
            end_at=expiry_time
        )
        await uow.keys.add(key)

        return self._PrepareResult(
            success=True,
            payment_id=payment.id,
            action=payment.action,
            key_id=key.id,
            expiry_time=expiry_time,
        )

    async def _provision_purchase(self, key_id: int, payment_id: int, expiry_time: datetime,
                                  server_name: str, tg_id: int) -> _ProvisionResult:
        vpn_email = str(key_id)
        try:
            await self._vpn.create_key(vpn_email, expiry_time)
            vless_link = await self._vpn.get_link(vpn_email, server_name)
        except VpnClientAlreadyExistsError:
            async with self._uow as uow:
                await self._audit(
                    uow,
                    AuditLevel.ERROR,
                    AuditEventType.VPN_KEY_CREATED,
                    f"Не удалось выдать пользователю ключ. "
                    f"Ключ с таким email уже есть в xui. "
                    f"tg_id={tg_id}, key_id={key_id}, payment_id={payment_id}."
                )
            return self._ProvisionResult(success=False, error=ConfirmPaymentErrorType.KEY_ALREADY_EXISTS)
        except VpnGatewayError as e:
            async with self._uow as uow:
                await self._audit(
                    uow,
                    AuditLevel.ERROR,
                    AuditEventType.VPN_ERROR,
                    f"Не удалось выдать доступ пользователю после покупки ключа. "
                    f"tg_id={tg_id}, key_id={key_id}, payment_id={payment_id}. "
                    f"Ошибка: {e}."
                )
            return self._ProvisionResult(success=False, error=ConfirmPaymentErrorType.UNKNOWN_ERROR)

        return self._ProvisionResult(success=True, vless_link=vless_link)

    async def _finalize_purchase(self, key_id: int, payment_id: int, vless_link: str) -> None:
        """Добавляем vless ссылку к ключу и фиксируем платёж."""
        async with self._uow as uow:
            # Добавляем vless ссылку
            payment = await uow.payments.get_for_update(payment_id)
            key = await uow.keys.get_for_update(key_id)

            key.vless_link = vless_link
            await uow.keys.update(key)

            # Фиксируем платёж
            await self._fixing_payment(uow, payment, key.id)

    # Продление доступа
    async def _prepare_renew(self, uow: AbstractUnitOfWork, payment: Payment, user: User,
                             plan: Plan, key_id: int | None, tg_id: int) -> _PrepareResult:
        # Обновляем статус платежа на PROCESSING
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
                f"Ключ для продления не найден. "
                f"tg_id={tg_id}, key_id={key_id}, payment_id={payment.id}."
            )
            return self._PrepareResult(success=False, error=ConfirmPaymentErrorType.KEY_NOT_FOUND)

        if key.user_id != user.id:
            await self._audit(
                uow,
                AuditLevel.ERROR,
                AuditEventType.KEY_NOT_OWNED_BY_USER,
                f"Попытка продлить чужой ключ! "
                f"user_id={user.id}, key_user_id={key.user_id}, key_id={key.id}, payment_id={payment.id}."
            )
            return self._PrepareResult(success=False, error=ConfirmPaymentErrorType.KEY_NOT_FOUND)

        # Обновляем ключ в БД
        await self._extend_key_time(uow, key, plan.duration_seconds)

        return self._PrepareResult(
            success=True,
            payment_id=payment.id,
            action=payment.action,
            key_id = key.id,
            expiry_time=key.end_at
        )

    async def _validate_key_id(self, uow: AbstractUnitOfWork, key_id: int | None,
                               tg_id: int, payment_id: int) -> ConfirmPaymentErrorType | None:
        if key_id is None:
            await self._audit(
                uow,
                AuditLevel.ERROR,
                AuditEventType.SYSTEM_ERROR,
                f"Не удалось продлить ключ. ID ключа не был передан. "
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

    async def _provision_renew(self, key_id: int, payment_id: int,
                               expiry_time: datetime, tg_id: int) -> _ProvisionResult:
        try:
            await self._vpn.update_expiry(str(key_id), expiry_time)
        except VpnClientAlreadyExistsError:
            async with self._uow as uow:
                await self._audit(
                    uow,
                    AuditLevel.ERROR,
                    AuditEventType.VPN_KEY_UPDATED,
                    f"Не удалось обновить ключ пользователя. "
                    f"Ключ не найден в vpn. "
                    f"tg_id={tg_id}, key_id={key_id}, payment_id={payment_id}."
                )
                return self._ProvisionResult(success=False, error=ConfirmPaymentErrorType.KEY_NOT_FOUND)
        except VpnGatewayError as e:
            async with self._uow as uow:
                await self._audit(
                    uow,
                    AuditLevel.ERROR,
                    AuditEventType.VPN_ERROR,
                    f"Не удалось продлить доступ пользователю после покупки тарифа. "
                    f"tg_id={tg_id}, key_id={key_id}, payment_id={payment_id}. "
                    f"Ошибка: {e}."
                )
            return self._ProvisionResult(success=False, error=ConfirmPaymentErrorType.UNKNOWN_ERROR)

        return self._ProvisionResult(success=True)

    async def _finalize_renew(self, payment_id: int, key_id: int) -> ConfirmPaymentResult:
        """Продление доступа."""
        # Фиксируем платёж и доступ
        async with self._uow as uow:
            payment = await uow.payments.get_for_update(payment_id)
            await self._fixing_payment(uow, payment, key_id)

        return ConfirmPaymentResult(success=True)

    async def _fixing_payment(self, uow: AbstractUnitOfWork, payment: Payment, key_id: int):
        """Фиксация платежа после покупки или продления."""
        now = utils.utcnow()
        payment.status = PaymentStatus.COMPLETED
        payment.paid_at = now
        payment.key_id = key_id
        payment.granted_at = now
        await uow.payments.update(payment)

    async def _audit(self, uow: AbstractUnitOfWork, level: AuditLevel, event: AuditEventType, message: str):
        await uow.audits.add(
            AuditLog(
                level=level,
                event_type=event,
                message=message
            )
        )