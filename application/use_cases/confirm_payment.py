"""Backend-логика для выдачи/продления доступа к серверу пользователю, потому что оплата прошла успешно."""
from dataclasses import dataclass
from enum import StrEnum
from datetime import timedelta

from application.ports.unit_of_work import AbstractUnitOfWork
from application.ports.vpn_gateway import VpnGateway
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

class ConfirmPaymentResult:
    """Базовый класс для результатов: ошибка или успех."""
    pass

@dataclass
class ConfirmPaymentSuccess(ConfirmPaymentResult):
    pass

@dataclass
class ConfirmPaymentError(ConfirmPaymentResult):
    error_type: ConfirmPaymentErrorType

class ConfirmPaymentUseCase:
    """Сценарий выдачи/продления доступа при успешном платеже."""
    def __init__(self, uow: AbstractUnitOfWork, vpn: VpnGateway):
        self._uow = uow
        self._vpn = vpn

    async def _fixing_payment(self, uow: AbstractUnitOfWork, payment: Payment, key_id: int):
        """Фиксация платежа после покупки или продления."""
        now = utils.utcnow_naive()
        payment.status = PaymentStatus.COMPLETED
        payment.paid_at = now
        payment.key_id = key_id
        payment.granted_at = now
        await uow.payments.update(payment)

    async def _handle_purchase(self, uow: AbstractUnitOfWork, user: User, payment: Payment,
                               plan: Plan) -> ConfirmPaymentResult:
        """Выдача доступа."""
        # Если доступ у этого платежа не выдан, то выдаём
        if payment.granted_at is None:
            # Создаём ключ в БД
            expiry_time = utils.add_seconds_to_now_naive(plan.duration_seconds)
            key = AccessKey(
                user_id=user.id,
                plan_id=plan.id,
                end_at=expiry_time,
                price_at_purchase=plan.price
            )
            await uow.keys.add(key)

            # Создаём клиента в XUI (синхронизируем с БД)
            vpn_email = str(key.id)

            try:
                if await self._vpn.is_client_exists(vpn_email):
                    await uow.audits.add(
                        AuditLog(
                            level=AuditLevel.ERROR,
                            event_type=AuditEventType.XUI_ADD,
                            message=(
                                f"Не удалось выдать пользователю ключ, "
                                f"потому что такой ключ уже есть в xui.\n"
                                f"user_id={user.id}, key_id={key.id}, payment_id={payment.id}."
                            )
                        )
                    )
                    return ConfirmPaymentError(error_type=ConfirmPaymentErrorType.KEY_ALREADY_EXISTS)

                await self._vpn.create_key(vpn_email, expiry_time)
            except Exception as e:
                await uow.audits.add(
                    AuditLog(
                        level=AuditLevel.ERROR,
                        event_type=AuditEventType.XUI_ADD,
                        message=(
                            f"Не удалось выдать доступ пользователю после покупки ключа.\n"
                            f"user_id={user.id}, key_id={key.id}, payment_id={payment.id}.\n"
                            f"Ошибка: {e}"
                        )
                    )
                )
                return ConfirmPaymentError(error_type=ConfirmPaymentErrorType.UNKNOWN_ERROR)

            # Фиксируем платёж
            await self._fixing_payment(uow, payment, key.id)

        return ConfirmPaymentSuccess()

    async def _handle_renew(self, uow: AbstractUnitOfWork, user: User, payment: Payment,
                               plan: Plan, key_id: int) -> ConfirmPaymentResult:
        """Продление доступа."""
        # Если продление у этого платежа не выполнено, то выполняем
        if payment.granted_at is None:
            # Получаем ключ из БД
            key = await uow.keys.get_by_id(key_id)
            if key is None:
                await uow.audits.add(
                    AuditLog(
                        level=AuditLevel.ERROR,
                        event_type=AuditEventType.KEY_NOT_FOUND_IN_DB,
                        message=(
                            f"Ключ для продления не найден.\n"
                            f"user_id={user.id}, key_id={key_id}, payment_id={payment.id}."
                        )
                    )
                )
                return ConfirmPaymentError(
                    error_type=ConfirmPaymentErrorType.KEY_NOT_FOUND
                )

            if key.user_id != user.id:
                await uow.audits.add(
                    AuditLog(
                        level=AuditLevel.ERROR,
                        event_type=AuditEventType.KEY_NOT_OWNED_BY_USER,
                        message=(
                            f"Попытка продлить чужой ключ!\n"
                            f"user_id={user.id}, key_user_id={key.user_id}, key_id={key.id}, payment_id={payment.id}."
                        )
                    )
                )
                return ConfirmPaymentError(
                    error_type=ConfirmPaymentErrorType.KEY_NOT_FOUND
                )

            # Обновляем клиента в XUI (синхронизируем с БД)
            now = utils.utcnow_naive()
            if key.end_at > now:
                base_time = key.end_at
            else:
                base_time = now
            expiry_time = base_time + timedelta(seconds=plan.duration_seconds)
            vpn_email = str(key.id)

            try:
                if not await self._vpn.is_client_exists(vpn_email):
                    await uow.audits.add(
                        AuditLog(
                            level=AuditLevel.ERROR,
                            event_type=AuditEventType.XUI_UPDATE,
                            message=(
                                f"Не удалось обновить ключ пользователя, "
                                f"потому что ключ не найде в xui.\n"
                                f"user_id={user.id}, key_id={key.id}, payment_id={payment.id}."
                            )
                        )
                    )
                    return ConfirmPaymentError(error_type=ConfirmPaymentErrorType.KEY_NOT_FOUND)

                await self._vpn.update_expiry(vpn_email, expiry_time)
            except Exception as e:
                await uow.audits.add(
                    AuditLog(
                        level=AuditLevel.ERROR,
                        event_type=AuditEventType.XUI_ADD,
                        message=(
                            f"Не удалось продлить доступ пользователю после покупки тарифа.\n"
                            f"user_id={user.id}, key_id={key.id}, payment_id={payment.id}.\n"
                            f"Ошибка: {e}"
                        )
                    )
                )
                return ConfirmPaymentError(error_type=ConfirmPaymentErrorType.UNKNOWN_ERROR)

            # Фиксируем платёж и доступ
            key.end_at = expiry_time
            await uow.keys.update(key)
            await self._fixing_payment(uow, payment, key.id)

        return ConfirmPaymentSuccess()

    async def execute(self, tg_id: int, username: str, payment_id: int,
                      *, key_id: int | None = None) -> ConfirmPaymentResult:
        """Выдача доступа пользователю."""
        async with self._uow as uow:
            user = await uow.users.get_or_create(tg_id, username)
            payment = await uow.payments.get_by_id(payment_id)

            # Проверки на корректность платежа
            if payment is None:
                await uow.audits.add(
                    AuditLog(
                        level=AuditLevel.ERROR,
                        event_type=AuditEventType.PAYMENT_NOT_FOUND,
                        message=(
                            f"Пользователь оплатил доступ, но платёж не найден в БД.\n"
                            f"tg_id={tg_id}, payment_id={payment_id}, user_id={user.id}."
                        )
                    )
                )
                return ConfirmPaymentError(error_type=ConfirmPaymentErrorType.PAYMENT_NOT_FOUND)

            if payment.user_id != user.id:
                await uow.audits.add(
                    AuditLog(
                        level=AuditLevel.ERROR,
                        event_type=AuditEventType.PAYMENT_NOT_FOUND,
                        message=(
                            f"Платёж имеет user_id, который не соответствует пользователю.\n"
                            f"tg_id={tg_id}, payment_id={payment_id}, user_id={user.id}."
                        )
                    )
                )
                return ConfirmPaymentError(error_type=ConfirmPaymentErrorType.PAYMENT_NOT_OWNED)

            plan = await uow.plans.get_by_id(payment.plan_id)

            if payment.action == PaymentAction.CREATE:
                return await self._handle_purchase(uow, user, payment, plan)

            elif payment.action == PaymentAction.RENEW:
                if key_id is None:
                    await uow.audits.add(
                        AuditLog(
                            level=AuditLevel.ERROR,
                            event_type=AuditEventType.SYSTEM_ERROR,
                            message=(
                                f"Не удалось продлить ключ. ID ключа не был передан.\n"
                                f"tg_id={tg_id}, payment_id={payment_id}."
                            )
                        )
                    )
                    return ConfirmPaymentError(error_type=ConfirmPaymentErrorType.MISSING_KEY_ID)

                return await self._handle_renew(uow, user, payment, plan, key_id)

            else:
                # Невозможно, чтобы ошибка возникла. Она для перестраховки
                await uow.audits.add(
                    AuditLog(
                        level=AuditLevel.WARNING,
                        event_type=AuditEventType.PAYING_OTHER,
                        message=(
                            f"Пользователь оплатил доступ, но это не покупка и не продление.\n"
                            f"tg_id={tg_id}, payment_id={payment_id}."
                        )
                    )
                )
                return ConfirmPaymentError(error_type=ConfirmPaymentErrorType.UNSUPPORTED_PAYMENT_TYPE)