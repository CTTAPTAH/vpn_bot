"""Backend-логика для проверки на возможность покупки ключа пользователем и создание платежа, если это возможно."""
from dataclasses import dataclass
from enum import StrEnum
from uuid import uuid4

from application.ports.unit_of_work import AbstractUnitOfWork
from domain.enums import PaymentType, PaymentProvider, AuditLevel, AuditEventType, PaymentAction
from domain.entities.audit_log import AuditLog
from domain.entities.payment import Payment
from core.config import MAX_KEYS_PER_USER

class CreatePaymentErrorType(StrEnum):
    """Тип ошибки при создании платежа."""
    LIMIT_KEYS = "LIMIT_KEYS"

class CreatePaymentResult:
    """Базовый класс для результатов получения информации о созданном ключе."""
    pass

@dataclass
class CreatePaymentSuccess(CreatePaymentResult):
    payment_id: int
    payment_link: str
    plan_name: str
    price: int
    is_existing: bool

@dataclass
class CreatePaymentError(CreatePaymentResult):
    error_type: CreatePaymentErrorType

class CreatePaymentUseCase:
    """Сценарий получения создания платежа пользователя."""
    def __init__(self, uow: AbstractUnitOfWork):
        self._uow = uow

    async def execute(self, tg_id: int, username: str, payment_action: PaymentAction,
                      provider: PaymentProvider, plan_id: int) -> CreatePaymentResult:
        """Попытка создать платёж для пользователя"""
        async with self._uow as uow:
            user = await uow.users.get_or_create(tg_id, username)

            # Если при попытке покупки лимит по ключам превышен, то платёж не может быть создан
            if payment_action == PaymentAction.CREATE:
                count_keys = await uow.keys.count_all_keys(user.id)
                if count_keys >= MAX_KEYS_PER_USER:
                    await uow.audits.add(
                        AuditLog(
                            level=AuditLevel.INFO,
                            event_type=AuditEventType.KEY_LIMIT,
                            message=(
                                f"Попытка приобрести ключ, превысив лимит.\n"
                                f"tg_id={tg_id}, count__keys={count_keys}, limit={MAX_KEYS_PER_USER}."
                            )
                        )
                    )
                    return CreatePaymentError(error_type=CreatePaymentErrorType.LIMIT_KEYS)

            # Проверяем, есть ли у пользователя не завершённый платёж
            payment = await uow.payments.get_user_pending_payment(user.id)

            # Если такой платёж есть, то возвращаем его
            # ЗАГЛУШКА
            if payment is not None:
                plan = await uow.plans.get_by_id(payment.plan_id)
                return CreatePaymentSuccess(
                    payment_id=payment.id,
                    payment_link="https://ya.ru/",
                    plan_name=plan.name,
                    price=plan.price,
                    is_existing=True
                )

            # Если такого платежа нет, то создаём новый
            plan = await uow.plans.get_by_id(plan_id)
            payment = Payment(
                    user_id=user.id,
                    plan_id=plan.id,
                    price=plan.price,
                    type=PaymentType.PURCHASE,
                    action=payment_action,
                    provider=provider,
                    provider_payment_id=str(uuid4()), # ЗАГЛУШКА
                )
            await uow.payments.add(payment)

        # ЗАГЛУШКА
        return CreatePaymentSuccess(
            payment_id=payment.id,
            payment_link="https://ya.ru/",
            plan_name=plan.name,
            price=plan.price,
            is_existing=False)