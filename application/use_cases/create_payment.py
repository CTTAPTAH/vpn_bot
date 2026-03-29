"""Backend-логика для проверки на возможность покупки ключа пользователем и создание платежа, если это возможно."""
from dataclasses import dataclass
from enum import StrEnum

from application.ports.unit_of_work import AbstractUnitOfWork
from domain.enums import PaymentType, PaymentProvider, AuditLevel, AuditEventType, PaymentAction
from domain.entities.audit_log import AuditLog
from domain.entities.payment import Payment
from core.config import MAX_KEYS_PER_USER
import core.utils as utils

class CreatePaymentErrorType(StrEnum):
    """Тип ошибки при создании платежа."""
    LIMIT_KEYS = "LIMIT_KEYS"
    PLAN_NOT_FOUND = "PLAN_NOT_FOUND"

@dataclass
class CreatePaymentResult:
    success: bool
    error: CreatePaymentErrorType | None = None
    payment_id: int | None = None
    payment_link: str | None = None
    plan_name: str | None = None
    price: int | None = None
    is_existing: bool | None = None

class CreatePaymentUseCase:
    """Сценарий проверки возможности покупки и создания платежа."""
    def __init__(self, uow: AbstractUnitOfWork):
        self._uow = uow

    async def execute(self, tg_id: int, username: str, payment_action: PaymentAction,
                      provider: PaymentProvider, plan_id: int) -> CreatePaymentResult:
        async with self._uow as uow:
            user = await uow.users.get_or_create(tg_id, username)
            user_locked = await uow.users.get_by_id_for_update(user.id)

            # Если при попытке покупки лимит по ключам превышен, то платёж не может быть создан
            if payment_action == PaymentAction.CREATE:
                count_keys = await uow.keys.count_all_keys(user_locked.id)
                if count_keys >= MAX_KEYS_PER_USER:
                    await self._audit(
                        uow,
                        AuditLevel.INFO,
                        AuditEventType.KEY_LIMIT,
                        message=(
                            f"Попытка приобрести ключ, превысив лимит.\n"
                            f"tg_id={tg_id}, count_keys={count_keys}, limit={MAX_KEYS_PER_USER}."
                        )
                    )
                    return CreatePaymentResult(success=False, error=CreatePaymentErrorType.LIMIT_KEYS)

            # Проверяем, есть ли у пользователя не завершённый платёж
            payment = await uow.payments.get_user_pending_payment_for_update(user_locked.id)

            # Если такой платёж есть, то возвращаем его
            # ЗАГЛУШКА
            if payment is not None:
                plan = await uow.plans.get_by_id(payment.plan_id)
                return CreatePaymentResult(
                    success=True,
                    payment_id=payment.id,
                    payment_link="https://ya.ru/",
                    plan_name=plan.name,
                    price=plan.price,
                    is_existing=True
                )

            # Если такого платежа нет, то создаём новый
            plan = await uow.plans.get_by_id(plan_id)
            if plan is None:
                await self._audit(
                    uow,
                    AuditLevel.ERROR,
                    AuditEventType.PAYMENT_NOT_FOUND,
                    f"Платёж не создан, тариф не найден. user_id={user_locked.id}, plan_id={plan_id}"
                )
                return CreatePaymentResult(success=False, error=CreatePaymentErrorType.PLAN_NOT_FOUND)

            payment = await self._create_payment(uow, user_locked.id, plan_id, plan.price, payment_action, provider)

        # ЗАГЛУШКА
        return CreatePaymentResult(
            success=True,
            payment_id=payment.id,
            payment_link="https://ya.ru/",
            plan_name=plan.name,
            price=plan.price,
            is_existing=False
        )

    async def _create_payment(self, uow: AbstractUnitOfWork, user_id: int, plan_id: int, price: int,
                              action: PaymentAction, provider: PaymentProvider) -> Payment:
        payment = Payment(
            user_id=user_id,
            plan_id=plan_id,
            price=price,
            type=PaymentType.PURCHASE,
            action=action,
            provider=provider,
            provider_payment_id=utils.new_uuid()
        )
        await uow.payments.add(payment)
        return payment

    async def _audit(self, uow: AbstractUnitOfWork, level: AuditLevel, event: AuditEventType, message: str):
        await uow.audits.add(
            AuditLog(
                level=level,
                event_type=event,
                message=message
            )
        )