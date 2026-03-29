from abc import ABC, abstractmethod
from domain.entities.payment import Payment
from domain.enums import PaymentProvider

class AbstractPaymentRepository(ABC):
    """
    Контракт репозитория платежа.

    Application слой работает только с этим интерфейсом.
    """
    @abstractmethod
    async def get_by_id(self, payment_id: int) -> Payment | None:
        ...

    @abstractmethod
    async def get_for_update(self, payment_id: int) -> Payment | None:
        ...

    @abstractmethod
    async def get_by_provider_and_payment_id(self, provider: PaymentProvider,
                                             provider_payment_id: str) -> Payment | None:
        ...

    @abstractmethod
    async def get_user_pending_payment(self, user_id: int) -> Payment | None:
        ...

    @abstractmethod
    async def get_user_pending_payment_for_update(self, user_id: int) -> Payment | None:
        ...

    @abstractmethod
    async def has_trial(self, user_id: int) -> bool:
        ...

    @abstractmethod
    async def get_user_trial_for_update(self, user_id: int) -> Payment | None:
        ...

    @abstractmethod
    async def add(self, payment: Payment) -> None:
        ...

    @abstractmethod
    async def update(self, payment: Payment) -> None:
        ...