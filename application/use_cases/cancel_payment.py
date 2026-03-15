"""Backend-логика для отмены покупки пользователем."""
from dataclasses import dataclass
from enum import StrEnum

from application.ports.unit_of_work import AbstractUnitOfWork
from domain.enums import AuditLevel, AuditEventType, PaymentStatus
from domain.entities.audit_log import AuditLog

class CancelPaymentErrorType(StrEnum):
    """Тип ошибки при отмене платежа."""
    KEY_NOT_FOUND = "KEY_NOT_FOUND"

class CancelPaymentResult:
    """Базовый класс для получения результатов: ошибка, успех."""
    pass

@dataclass
class CancelPaymentSuccess(CancelPaymentResult):
    pass

@dataclass
class CancelPaymentError(CancelPaymentResult):
    error_type: CancelPaymentErrorType

class CancelPaymentUseCase:
    """Сценарий отмены платежа."""
    def __init__(self, uow: AbstractUnitOfWork):
        self._uow = uow

    async def execute(self, tg_id: int, username: str) -> CancelPaymentResult:
        """Попытка отменить платёж"""
        async with self._uow as uow:
            user = await uow.users.get_or_create(tg_id, username)

            # Проверяем, есть ли у пользователя не завершённый платёж
            payment = await uow.payments.get_user_pending_payment(user.id)

            # Если такой платёж не найден, то ошибка
            if payment is None:
                await uow.audits.add(
                    AuditLog(
                        level=AuditLevel.ERROR,
                        event_type=AuditEventType.PAYMENT_NOT_FOUND,
                        message=(
                            f"Пользователь попытался отменить платёж, но платёж не найден.\n"
                            f"tg_id={tg_id}."
                        )
                    )
                )
                return CancelPaymentError(error_type=CancelPaymentErrorType.KEY_NOT_FOUND)

            # Если такой платёж существует, то отменяем
            payment.status = PaymentStatus.FAILED
            await uow.payments.update(payment)

            await uow.audits.add(
                AuditLog(
                    level=AuditLevel.INFO,
                    event_type=AuditEventType.PAYMENT_CANCELLED,
                    message=(
                        f"Пользователь успешно отменил платёж.\n"
                        f"tg_id={tg_id}, payment_id={payment.id}."
                    )
                )
            )
            return CancelPaymentSuccess()