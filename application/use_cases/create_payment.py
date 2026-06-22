"""Backend-логика для проверки на возможность покупки ключа пользователем и создание платежа, если это возможно."""
from dataclasses import dataclass
from enum import StrEnum

from application.use_cases.base_use_case import BaseUseCase
from application.ports.unit_of_work import AbstractUnitOfWork
from application.ports.payment_provider import AbstractPaymentProvider
from domain.enums import (PaymentType, PaymentStatus, PaymentProvider, AuditLevel,
                          AuditEventType, PaymentAction, PaymentMethod)
from domain.entities.payment import Payment
from domain.entities.payment_ui_state import PaymentUiState
import core.config as config

class CreatePaymentErrorType(StrEnum):
    """Тип ошибки при создании платежа."""
    PLAN_NOT_FOUND = "PLAN_NOT_FOUND"
    EMPTY_PAYMENT_LINK = "EMPTY_PAYMENT_LINK"

@dataclass
class CreatePaymentResult:
    success: bool
    error: CreatePaymentErrorType | None = None
    payment_id: int | None = None
    payment_link: str | None = None
    plan_name: str | None = None
    price: int | None = None

class CreatePaymentUseCase(BaseUseCase):
    """Сценарий проверки возможности покупки и создания платежа."""
    def __init__(self, uow: AbstractUnitOfWork, payment_provider: AbstractPaymentProvider):
        self._uow = uow
        self._provider = payment_provider

    async def execute(self, tg_id: int, username: str, payment_action: PaymentAction, currency: str,
                      provider: PaymentProvider, plan_id: int, payment_method: PaymentMethod, *,
                      sub_id: int | None = None, tg_chat_id: int, tg_message_id: int) -> CreatePaymentResult:
        async with self._uow as uow:
            user = await uow.users.get_or_create(tg_id, username)
            user_locked = await uow.users.get_by_id_for_update(user.id)

            # Получаем тариф
            plan = await uow.plans.get_by_id(plan_id)
            if plan is None:
                await self._audit(
                    uow,
                    AuditLevel.ERROR,
                    AuditEventType.PAYMENT_NOT_FOUND,
                    f"[CreatePaymentUseCase][execute]\n"
                    f"Платёж не создан, тариф не найден.\n"
                    f"tg_id={tg_id}, plan_id={plan_id}."
                )
                return CreatePaymentResult(success=False, error=CreatePaymentErrorType.PLAN_NOT_FOUND)

            # Проверяем, есть ли у пользователя не завершённый платёж
            payment = await uow.payments.get_user_pending_payment_for_update(user_locked.id)

            # Если такой платёж есть
            if payment is not None:
                # Если это тот же тариф и до истечения времени больше n минут, то возвращаем
                is_payment_expiring = await self._provider.is_payment_expiring_soon(
                    payment.provider_payment_id,
                    config.PAYMENT_EXPIRY_THRESHOLD_MINUTES
                )
                if payment.plan_id == plan_id and not is_payment_expiring:
                    return CreatePaymentResult(
                        success=True,
                        payment_id=payment.id,
                        payment_link=payment.payment_url,
                        plan_name=plan.name,
                        price=plan.price,
                    )

                # Иначе ставим в статус CANCELLED
                else:
                    payment.status = PaymentStatus.CANCELLED
                    await uow.payments.update(payment)


            # Запоминаем данные, которые понадобятся вне транзакции
            plan_name = plan.name
            price = plan.price
            user_id = user_locked.id

        description = self._build_description(plan_name, payment_action)
        payment_data = await self._provider.create_payment(payment_method, price, currency, description)

        async with self._uow as uow:
            if not payment_data.redirect_url:
                await self._audit(
                    uow,
                    AuditLevel.ERROR,
                    AuditEventType.EMPTY_PAYMENT_LINK,
                    f"[CreatePaymentUseCase][execute]\n"
                    f"Касса прислала пустую ссылку.\n"
                    f"tg_id={tg_id}, url={payment_data.redirect_url}, plan_id={plan_id}, "
                    f"transaction_id={payment_data.transaction_id}."
                )
                return CreatePaymentResult(success=False, error=CreatePaymentErrorType.EMPTY_PAYMENT_LINK)

            payment = await self._create_payment(uow, user_id, plan_id, price, payment_method,
                                                 payment_action, provider, payment_data.transaction_id,
                                                 payment_data.redirect_url, sub_id=sub_id)

            # Запоминаем id сообщения, чтобы его можно было изменить при webhook
            payment_ui = PaymentUiState(
                payment_id=payment.id,
                tg_user_id=tg_id,
                tg_chat_id=tg_chat_id,
                tg_message_id=tg_message_id
            )
            await uow.payment_ui_states.add(payment_ui)

        return CreatePaymentResult(
            success=True,
            payment_id=payment.id,
            payment_link=payment_data.redirect_url,
            plan_name=plan_name,
            price=price,
        )

    async def _create_payment(self, uow: AbstractUnitOfWork, user_id: int, plan_id: int, price: int,
                              payment_method: PaymentMethod, action: PaymentAction, provider: PaymentProvider,
                              provider_payment_id: str, payment_url: str, *, sub_id: int | None = None) -> Payment:
        payment = Payment(
            user_id=user_id,
            plan_id=plan_id,
            sub_id=sub_id,
            price=price,
            payment_method=payment_method,
            type=PaymentType.PURCHASE,
            action=action,
            provider=provider,
            provider_payment_id=provider_payment_id,
            payment_url=payment_url
        )
        await uow.payments.add(payment)
        return payment

    def _build_description(self, plan_name: str, action: PaymentAction) -> str:
        if action == PaymentAction.CREATE:
            return f"Покупка доступа: тариф \"{plan_name}\""

        if action == PaymentAction.RENEW:
            return f"Продление доступа: тариф \"{plan_name}\""

        return f"Оплата тарифа \"{plan_name}\""