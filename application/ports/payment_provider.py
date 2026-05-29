"""
Абстракция (контракт) для использования провайдера кассы.

Определяет какие существуют методы для работы с кассой.

Application-слой должен зависеть только от этой абстракции,
а не от конкретной реализации (например, platega).

Реализация находится в infrastructure.
"""
from abc import ABC, abstractmethod
from datetime import timedelta

from domain.enums import PaymentMethod
from dataclasses import dataclass

@dataclass(slots=True)
class PaymentData:
    transaction_id: str
    redirect_url: str

@dataclass(slots=True)
class TransactionStatus:
    transaction_id: str
    status: str # PENDING, CONFIRMED, CANCELLED
    amount: int # сумма в рублях
    currency: str # RUB
    payment_method: str # SBPQR и т.д.
    expires_in: timedelta | None # оставшееся время жизни
    external_id: str # id на стороне кассы

class AbstractPaymentProvider(ABC):
    @abstractmethod
    async def create_payment(self, payment_method: PaymentMethod, amount: float,
                             currency: str, description: str) -> PaymentData:
        """Создание ссылки на оплату. Касса создает транзакцию и возвращает данные для оплаты."""
        ...

    @abstractmethod
    async def get_transaction_status(self, transaction_id: str) -> TransactionStatus:
        """Возвращает статус транзакции."""
        ...

    @abstractmethod
    async def is_payment_expiring_soon(self, transaction_id: str, threshold_minutes: int) -> bool:
        """Возвращает True если времени на оплату осталось меньше threshold_minutes минут."""
        ...