"""Backend-логика для отмены покупки пользователем."""
from dataclasses import dataclass
from enum import StrEnum

from application.use_cases.base_use_case import BaseUseCase
from application.ports.unit_of_work import AbstractUnitOfWork
from domain.enums import AuditLevel, AuditEventType, PaymentStatus

class CancelPaymentErrorType(StrEnum):
    """Тип ошибки при отмене платежа."""
    PAYMENT_NOT_FOUND = "PAYMENT_NOT_FOUND"

@dataclass
class CancelPaymentResult:
    success: bool
    error: CancelPaymentErrorType | None = None

class CancelPaymentUseCase(BaseUseCase):
    """Сценарий отмены платежа."""
    def __init__(self, uow: AbstractUnitOfWork):
        self._uow = uow

    async def execute(self, tg_id: int, username: str) -> CancelPaymentResult:
        async with self._uow as uow:
            user = await uow.users.get_or_create(tg_id, username)

            # Проверяем, есть ли у пользователя не завершённый платёж
            payment = await uow.payments.get_user_pending_payment_for_update(user.id)

            # Если такой платёж не найден, то ошибка
            if payment is None:
                await self._audit(
                    uow,
                    AuditLevel.ERROR,
                    AuditEventType.PAYMENT_NOT_FOUND,
                    f"[CancelPaymentUseCase][execute]\n"
                    f"Платёж не найден.\n"
                    f"tg_id={tg_id}."
                )
                return CancelPaymentResult(success=False, error=CancelPaymentErrorType.PAYMENT_NOT_FOUND)

            # Если такой платёж существует, то отменяем
            payment.status = PaymentStatus.FAILED
            await uow.payments.update(payment)

            await self._audit(
                uow,
                AuditLevel.INFO,
                AuditEventType.PAYMENT_CANCELLED,
                f"[CancelPaymentUseCase][execute]\n"
                f"Пользователь успешно отменил платёж.\n"
                f"tg_id={tg_id}, payment_id={payment.id}."
            )

            return CancelPaymentResult(success=True)