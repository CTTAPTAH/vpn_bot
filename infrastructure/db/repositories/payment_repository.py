from sqlalchemy import select, exists, and_
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.payment import Payment as DomainPayment, Payment
from application.ports.repositories.payment_repository import AbstractPaymentRepository
from infrastructure.db.models.payment import Payment as ORMPayment
from domain.enums import PaymentProvider, PaymentType, PaymentStatus

def to_domain(orm_payment: ORMPayment) -> DomainPayment:
    return DomainPayment(
        id=orm_payment.id,
        user_id=orm_payment.user_id,
        plan_id=orm_payment.plan_id,
        key_id=orm_payment.key_id,
        price=orm_payment.price,
        type=orm_payment.type,
        action=orm_payment.action,
        provider=orm_payment.provider,
        provider_payment_id=orm_payment.provider_payment_id,
        status=orm_payment.status,
        granted_at=orm_payment.granted_at,
        created_at=orm_payment.created_at,
        paid_at=orm_payment.paid_at,
    )

class SQLAlchemyPaymentRepository(AbstractPaymentRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    # Получение данных
    async def get_by_id(self, payment_id: int) -> DomainPayment | None:
        """Получить платёж по id."""
        stmt = select(ORMPayment).where(ORMPayment.id == payment_id)
        result = await self._session.execute(stmt)
        orm_payment = result.scalar_one_or_none()

        if orm_payment is None:
            return None

        return to_domain(orm_payment)

    async def get_for_update(self, payment_id: int) -> Payment | None:
        """Получить платёж по id и блокировать строку для идемпотентности."""
        stmt = (select(ORMPayment)
                .where(ORMPayment.id == payment_id)
                .with_for_update()
                )
        result = await self._session.execute(stmt)
        orm_payment = result.scalar_one_or_none()

        if orm_payment is None:
            return None

        return to_domain(orm_payment)

    async def get_by_provider_and_payment_id(
            self,
            provider: PaymentProvider,
            provider_payment_id: str
    ) -> DomainPayment | None:
        """Получить платёж по его id у провайдера."""
        stmt = select(ORMPayment).where(
            ORMPayment.provider == provider,
            ORMPayment.provider_payment_id == provider_payment_id
        )
        result = await self._session.execute(stmt)
        orm_payment = result.scalar_one_or_none()

        if orm_payment is None:
            return None

        return to_domain(orm_payment)

    async def get_user_pending_payment(self, user_id: int) -> Payment | None:
        """Возвращает незавершённый платёж пользователя и блокирует его строку для идемпотентности."""
        stmt = (
            select(ORMPayment)
            .where(
                ORMPayment.status == PaymentStatus.PENDING,
                ORMPayment.user_id == user_id
            )
        )
        result = await self._session.execute(stmt)
        orm_payment = result.scalars().first()

        if orm_payment is None:
            return None

        return to_domain(orm_payment)

    async def get_user_pending_payment_for_update(self, user_id: int) -> Payment | None:
        """Возвращает незавершённый платёж пользователя и блокирует его строку для идемпотентности."""
        stmt = (
            select(ORMPayment)
            .where(
                ORMPayment.status == PaymentStatus.PENDING,
                ORMPayment.user_id == user_id
            )
            .with_for_update()
        )
        result = await self._session.execute(stmt)
        orm_payment = result.scalars().first()

        if orm_payment is None:
            return None

        return to_domain(orm_payment)

    async def has_trial(self, user_id: int) -> bool:
        """Проверяет, существует ли у пользователя платёж типа TRIAL."""
        stmt = select(
            exists().where(
                and_(
                    ORMPayment.user_id == user_id,
                    ORMPayment.type == PaymentType.TRIAL
                )
            )
        )
        return bool(await self._session.scalar(stmt))

    async def get_user_trial_for_update(self, user_id: int):
        stmt = (
            select(ORMPayment)
            .where(
                ORMPayment.user_id == user_id,
                ORMPayment.type == PaymentType.TRIAL
            )
            .with_for_update()
        )

        result = await self._session.execute(stmt)
        orm_model = result.scalar_one_or_none()

        if orm_model is None:
            return None

        return to_domain(orm_model)

    # Добавление данных
    async def add(self, payment: DomainPayment) -> None:
        orm_payment = ORMPayment(
            user_id=payment.user_id,
            plan_id=payment.plan_id,
            key_id=payment.key_id,
            price=payment.price,
            type=payment.type,
            action=payment.action,
            provider=payment.provider,
            provider_payment_id=payment.provider_payment_id,
            status=payment.status,
            granted_at=payment.granted_at,
            created_at=payment.created_at,
            paid_at=payment.paid_at,
        )
        self._session.add(orm_payment)
        await self._session.flush()

        payment.id = orm_payment.id # синхронизируем id

    # Обновление данных
    async def update(self, payment: DomainPayment) -> None:
        orm_payment = await self._session.get(ORMPayment, payment.id)

        if orm_payment is None:
            raise ValueError("Payment not found")

        orm_payment.key_id = payment.key_id
        orm_payment.status = payment.status
        orm_payment.granted_at = payment.granted_at
        orm_payment.paid_at = payment.paid_at