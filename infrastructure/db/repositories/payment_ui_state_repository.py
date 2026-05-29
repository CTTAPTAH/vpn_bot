from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.payment_ui_state import PaymentUiState as DomainPaymentUi
from application.ports.repositories.payment_ui_state_repository import AbstractPaymentUiStateRepository
from infrastructure.db.models.payment_ui_state import PaymentUiState as ORMPaymentUi

def to_domain(orm_payment_ui: ORMPaymentUi) -> DomainPaymentUi:
    return DomainPaymentUi(
        id=orm_payment_ui.id,
        payment_id=orm_payment_ui.payment_id,
        tg_user_id=orm_payment_ui.tg_user_id,
        tg_chat_id=orm_payment_ui.tg_chat_id,
        tg_message_id=orm_payment_ui.tg_message_id
    )

class SQLAlchemyPaymentUiStateRepository(AbstractPaymentUiStateRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    # Получение данных
    async def get_by_id(self, payment_ui_id: int) -> DomainPaymentUi | None:
        """Получить ui информацию о платеже по id."""
        stmt = select(ORMPaymentUi).where(ORMPaymentUi.id == payment_ui_id)
        result = await self._session.execute(stmt)
        orm_payment_ui = result.scalar_one_or_none()

        if orm_payment_ui is None:
            return None

        return to_domain(orm_payment_ui)

    async def get_for_update(self, payment_ui_id: int) -> DomainPaymentUi | None:
        """Получить ui информацию о платеже по id и блокировать строку для идемпотентности."""
        stmt = (select(ORMPaymentUi)
                .where(ORMPaymentUi.id == payment_ui_id)
                .with_for_update()
                )
        result = await self._session.execute(stmt)
        orm_payment_ui = result.scalar_one_or_none()

        if orm_payment_ui is None:
            return None

        return to_domain(orm_payment_ui)

    async def get_by_payment_for_update(self, payment_id: int) -> DomainPaymentUi | None:
        """Получить ui информацию о платеже по payment_id и блокировать строку для идемпотентности."""
        stmt = (select(ORMPaymentUi)
                .where(ORMPaymentUi.payment_id == payment_id)
                .with_for_update()
                )
        result = await self._session.execute(stmt)
        orm_payment_ui = result.scalar_one_or_none()

        if orm_payment_ui is None:
            return None

        return to_domain(orm_payment_ui)

    # Добавление данных
    async def add(self, payment_ui: DomainPaymentUi) -> None:
        orm_payment_ui = ORMPaymentUi(
            payment_id=payment_ui.payment_id,
            tg_user_id=payment_ui.tg_user_id,
            tg_chat_id=payment_ui.tg_chat_id,
            tg_message_id=payment_ui.tg_message_id
        )
        self._session.add(orm_payment_ui)
        await self._session.flush()

        payment_ui.id = orm_payment_ui.id # синхронизируем id

    # Обновление данных
    async def update(self, payment_ui: DomainPaymentUi) -> None:
        orm_payment_ui = await self._session.get(ORMPaymentUi, payment_ui.id)

        if orm_payment_ui is None:
            raise ValueError("Payment not found")

        orm_payment_ui.tg_user_id = payment_ui.tg_user_id
        orm_payment_ui.tg_chat_id = payment_ui.tg_chat_id
        orm_payment_ui.tg_message_id = payment_ui.tg_message_id