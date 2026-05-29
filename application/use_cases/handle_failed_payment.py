"""Backend-логика выдачи необходимой информации для изменения сообщения ui и изменить статус платежа на CANCELLED."""
from dataclasses import dataclass
from enum import StrEnum

from application.use_cases.base_use_case import BaseUseCase
from application.ports.unit_of_work import AbstractUnitOfWork
from domain.enums import PaymentProvider
from domain.enums import AuditLevel, AuditEventType, PaymentStatus

class HandleFailedPaymentErrorType(StrEnum):
    PAYMENT_NOT_FOUND = "PAYMENT_NOT_FOUND"
    PAYMENT_UI_NOT_FOUND = "PAYMENT_UI_NOT_FOUND"

@dataclass
class HandleFailedPaymentResult:
    success: bool
    tg_chat_id: int | None = None
    tg_message_id: int | None = None
    error: HandleFailedPaymentErrorType | None = None

class HandleFailedPaymentUseCase(BaseUseCase):
    """Сценарий выдачи/продления доступа при успешном платеже."""
    def __init__(self, uow: AbstractUnitOfWork):
        self._uow = uow

    async def execute(self, provider: PaymentProvider, payment_provider_id: str) -> HandleFailedPaymentResult:
        async with self._uow as uow:
            # Устанавливаем платёж на CANCELLED
            payment = await uow.payments.get_by_provider_and_payment_id_for_update(provider, payment_provider_id)
            if payment is None:
                await self._audit(
                    uow,
                    AuditLevel.ERROR,
                    AuditEventType.PAYMENT_NOT_FOUND,
                    f"[HandleFailedPaymentUseCase][execute].\n"
                    f"Платёж не найден в БД.\n"
                    f"provider={provider}, payment_provider_id={payment_provider_id}."
                )
                return HandleFailedPaymentResult(success=False, error=HandleFailedPaymentErrorType.PAYMENT_NOT_FOUND)

            payment.status = PaymentStatus.CANCELLED
            await uow.payments.update(payment)

            # Получаем данные для изменения ui
            payment_ui = await uow.payment_ui_states.get_by_payment_for_update(payment.id)
            if payment_ui is None:
                await self._audit(
                    uow,
                    AuditLevel.ERROR,
                    AuditEventType.PAYMENT_UI_NOT_FOUND,
                    f"[HandleFailedPaymentUseCase][execute].\n"
                    f"Платёж ui не найден в БД.\n"
                    f"payment_id={payment.id}."
                )
                return HandleFailedPaymentResult(
                    success=False,
                    error=HandleFailedPaymentErrorType.PAYMENT_UI_NOT_FOUND
                )

            return HandleFailedPaymentResult(
                success=True,
                tg_chat_id=payment_ui.tg_chat_id,
                tg_message_id=payment_ui.tg_message_id
            )