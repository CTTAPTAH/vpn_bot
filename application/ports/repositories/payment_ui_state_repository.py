from abc import ABC, abstractmethod
from domain.entities.payment_ui_state import PaymentUiState

class AbstractPaymentUiStateRepository(ABC):
    """
    Контракт репозитория ui состояния платежа.

    Application слой работает только с этим интерфейсом.
    """
    @abstractmethod
    async def get_by_id(self, payment_ui_id: int) -> PaymentUiState | None:
        ...

    @abstractmethod
    async def get_for_update(self, payment_ui_id: int) -> PaymentUiState | None:
        ...

    @abstractmethod
    async def get_by_payment_for_update(self, payment_id: int) -> PaymentUiState | None:
        ...

    @abstractmethod
    async def add(self, payment_ui: PaymentUiState) -> None:
        ...

    @abstractmethod
    async def update(self, payment_ui: PaymentUiState) -> None:
        ...