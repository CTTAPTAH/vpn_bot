"""Backend-логика выдачи пробного периода."""
from dataclasses import dataclass
from enum import StrEnum
from uuid import uuid4
from datetime import datetime

from application.ports.unit_of_work import AbstractUnitOfWork
from application.ports.vpn.gateway_factory import AbstractVpnGatewayFactory
from application.common.dto import KeyDTO
from application.errors.vpn_errors import (
    VpnClientAlreadyExistsError,
    VpnGatewayError
)
from application.services.server_selection import ServerSelectionService, NoAvailableServersError
from domain.entities.audit_log import AuditLog
from domain.entities.access_key import AccessKey
from domain.entities.user import User
from domain.entities.plan import Plan
from domain.entities.payment import Payment
from domain.enums import AuditLevel, AuditEventType, PaymentType, PaymentAction, PaymentProvider, PaymentStatus
import core.utils as utils

class ActiveTrialErrorType(StrEnum):
    """Тип ошибки во время выдачи пробного периода."""
    KEY_ALREADY_EXISTS = "KEY_ALREADY_EXISTS"
    KEY_NOT_FOUND = "KEY_NOT_FOUND"
    PAYMENT_NOT_OWNED = "PAYMENT_NOT_OWNED"
    NO_AVAILABLE_SERVERS = "NO_AVAILABLE_SERVERS"
    SERVER_NOT_FOUND = "SERVER_NOT_FOUND"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"

class ActiveTrialResultType(StrEnum):
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"
    CHOOSE_KEY = "CHOOSE_KEY"

@dataclass(slots=True)
class ActiveTrialResult:
    pass

# SUCCESS
@dataclass(slots=True)
class ActiveTrialSuccess(ActiveTrialResult):
    num_days: int
    vless_link: str

# ERROR
@dataclass(slots=True)
class ActiveTrialError(ActiveTrialResult):
    error_type: ActiveTrialErrorType

# CHOOSE_KEY
@dataclass(slots=True)
class ActiveTrialChooseKey(ActiveTrialResult):
    count_keys: int
    keys: list[KeyDTO]

class ActiveTrialUseCase:
    """Сценарий выдачи пробного периода."""
    def __init__(self, uow: AbstractUnitOfWork, gateway_factory: AbstractVpnGatewayFactory,
                 selector: ServerSelectionService):
        self._uow = uow
        self._selector = selector
        self._gateway_factory = gateway_factory

    @dataclass(slots=True)
    class _PrepareResult:
        """Сохранение необходимый информации после создания ключа в БД."""
        pass

    @dataclass(slots=True)
    class _PrepareChooseKey(_PrepareResult):
        count_keys: int
        keys: list[KeyDTO]

    @dataclass(slots=True)
    class _PrepareError(_PrepareResult):
        error: ActiveTrialErrorType

    @dataclass(slots=True)
    class _PrepareReady(_PrepareResult):
        key_id: int
        key_name: str
        payment_id: int
        server_id: int
        need_create_vpn: bool
        is_processing: bool

    async def execute(self, tg_id: int, username: str) -> ActiveTrialResult:
        """Выдать пробный период."""
        # В первой транзакции создаём ключ в БД или предупреждаем о лимите ключей
        async with self._uow as uow:
            user = await uow.users.get_or_create(tg_id, username)
            payment = await uow.payments.get_user_trial_for_update(user.id)
            plan = await uow.plans.get_trial()

            now = utils.utcnow()
            expiry_time = utils.add_seconds_to_now(plan.duration_seconds)
            trial_days = utils.days_from_seconds(plan.duration_seconds)

            # Если пробного период у пользователя не было, то выдаём доступ
            prepare = await self._prepare(uow, payment, user, plan, expiry_time, now, tg_id)

            if isinstance(prepare, self._PrepareError):
                return ActiveTrialError(error_type=prepare.error)

            if isinstance(prepare, self._PrepareChooseKey):
                return ActiveTrialChooseKey(count_keys=prepare.count_keys, keys=prepare.keys)

        if isinstance(prepare, self._PrepareReady):
            # Если статус платежа PROCESSING, то выходим
            if prepare.is_processing:
                vless_link = await self._get_vless_link_or_error(prepare.key_id, prepare.server_id,
                                                                 prepare.key_name, tg_id)
                return ActiveTrialSuccess(num_days=trial_days, vless_link=vless_link)

            # Создаём ключ на сервере VPN
            error = await self._sync_with_vpn(
                prepare.key_id,
                prepare.payment_id,
                prepare.server_id,
                expiry_time, tg_id,
                prepare.need_create_vpn
            )
            if error:
                return ActiveTrialError(error_type=error)

            # Получаем vless ссылку
            link_or_error = await self._get_vless_link_or_error(prepare.key_id, prepare.server_id,
                                                                prepare.key_name, tg_id)
            if isinstance(link_or_error, ActiveTrialErrorType):
                return ActiveTrialError(link_or_error)

            # Завершаем создание ключа второй транзакцией в БД, где мы запоминаем vless_link
            await self._finalize(prepare.key_id, prepare.payment_id, now, link_or_error, prepare.need_create_vpn)

            return ActiveTrialSuccess(num_days=trial_days, vless_link=link_or_error)

        else:
            return ActiveTrialError(error_type=ActiveTrialErrorType.UNKNOWN_ERROR)

    async def _prepare(self, uow: AbstractUnitOfWork, payment: Payment, user: User, plan: Plan,
                       expiry_time: datetime, now: datetime, tg_id: int) -> _PrepareResult:
        is_processing = False
        need_create_vpn = True
        # Если пробного период у пользователя не было, то выдаём доступ, иначе просто возвращаем данные
        if payment is None:
            count_all_keys = await uow.keys.count_all_keys(user.id)

            # Если превышен лимит по ключам, то предлагаем продление
            if count_all_keys >= 5:
                views = await uow.keys.list_view_by_user(user.id)
                keys_dto = [
                    KeyDTO(
                        id=v.id,
                        plan_name=v.plan_name,
                        end_at=v.end_at,
                        is_expired=now > v.end_at
                    )
                    for v in views
                ]
                return self._PrepareChooseKey(
                    count_keys=count_all_keys,
                    keys=keys_dto
                )

            # Выбираем сервер создаём ключ и платёж
            server_ids = await uow.servers.get_id_active_servers()
            try:
                server_id = await self._selector.select_server(uow.keys, server_ids)
            except NoAvailableServersError:
                await self._audit(
                    uow,
                    AuditLevel.ERROR,
                    AuditEventType.NO_AVAILABLE_SERVERS,
                    f"Во время выдачи доступа после получения пробного доступа не удалось найти сервер, "
                    f"на котором будет находится ключ. server_ids={server_ids}, tg_id={user.tg_id}"
                )
                return self._PrepareError(error=ActiveTrialErrorType.NO_AVAILABLE_SERVERS)
            async with self._uow as uow:
                server = await uow.servers.get_by_id(server_id)

                if server is None:
                    await self._audit(
                        uow,
                        AuditLevel.ERROR,
                        AuditEventType.SERVER_NOT_FOUND,
                        f"Во время выдачи доступа после получения пробного доступа "
                        f"не удалось найти сервер в БД. "
                        f"server_id={server_id}, tg_id={tg_id}"
                    )
                    return self._PrepareError(error=ActiveTrialErrorType.SERVER_NOT_FOUND)
            key = await self._create_trial_key(uow, user, plan, server_id, now, expiry_time)
            payment = await self._create_trial_payment(uow, user, plan, key, now)

            if payment.user_id != user.id:
                await self._audit(
                    uow,
                    AuditLevel.ERROR,
                    AuditEventType.PAYMENT_NOT_FOUND,
                    f"Платёж имеет user_id, который не соответствует пользователю. "
                    f"tg_id={tg_id}, payment_id={payment.id}."
                )
                return self._PrepareError(
                    error=ActiveTrialErrorType.PAYMENT_NOT_OWNED
                )
        else:
            need_create_vpn = False
            if payment.status == PaymentStatus.PROCESSING:
                is_processing = True
            key = await uow.keys.get_by_id(payment.key_id)
            server_id = key.server_id

        return self._PrepareReady(
            key_id=key.id,
            key_name=server.default_key_name,
            payment_id=payment.id,
            server_id=server_id,
            need_create_vpn=need_create_vpn,
            is_processing=is_processing
        )

    async def _sync_with_vpn(self, key_id: int, payment_id: int, server_id: int, expiry_time: datetime,
                          tg_id: int, need_create_vpn: bool) -> ActiveTrialErrorType | None:
        try:
            if need_create_vpn:
                # Получаем сервер
                async with self._uow as uow:
                    server = await uow.servers.get_by_id(server_id)

                    if server is None:
                        await self._audit(
                            uow,
                            AuditLevel.ERROR,
                            AuditEventType.SERVER_NOT_FOUND,
                            f"Во время выдачи доступа после получения пробного доступа "
                            f"не удалось найти сервер в БД. "
                            f"server_id={server_id}, tg_id={tg_id}"
                        )
                        return ActiveTrialErrorType.SERVER_NOT_FOUND

                vpn = await self._gateway_factory.get_gateway(server)
                vpn_email = str(key_id)
                await vpn.create_key(vpn_email, expiry_time)
            return None

        except VpnClientAlreadyExistsError:
            async with self._uow as uow:
                await self._audit(
                    uow,
                    AuditLevel.ERROR,
                    AuditEventType.VPN_KEY_CREATED,
                    f"Ключ уже существует в XUI. "
                    f"tg_id={tg_id}, key_id={key_id}, payment_id={payment_id}"
                )
            return ActiveTrialErrorType.KEY_ALREADY_EXISTS

        except VpnGatewayError as e:
            async with self._uow as uow:
                await uow.audits.add(
                    AuditLog(
                        level=AuditLevel.ERROR,
                        event_type=AuditEventType.VPN_ERROR,
                        message=f"Ошибка создания ключа в XUI. "
                                f"tg_id={tg_id}, key_id={key_id}, payment_id={payment_id}, Ошибка: {e}"
                    )
                )
                return ActiveTrialErrorType.UNKNOWN_ERROR

    async def _get_vless_link_or_error(self, key_id: int, server_id: int,
                                       key_name: str, tg_id: int) -> str | ActiveTrialErrorType:
        try:
            # Получаем сервер
            async with self._uow as uow:
                server = await uow.servers.get_by_id(server_id)

                if server is None:
                    await self._audit(
                        uow,
                        AuditLevel.ERROR,
                        AuditEventType.SERVER_NOT_FOUND,
                        f"Во время выдачи доступа после получения пробного доступа "
                        f"не удалось найти сервер в БД. "
                        f"server_id={server_id}, tg_id={tg_id}"
                    )
                    return ActiveTrialErrorType.SERVER_NOT_FOUND

            vpn = await self._gateway_factory.get_gateway(server)
            vless_link = await vpn.get_link(str(key_id), key_name)
            return vless_link

        except VpnClientAlreadyExistsError:
            async with self._uow as uow:
                await self._audit(
                    uow,
                    AuditLevel.ERROR,
                    AuditEventType.KEY_NOT_FOUND_IN_VPN,
                    f"Не удалось получить ссылку ключа пробного периода. Ключ не найден. "
                    f"tg_id={tg_id}, key_id={key_id}"
                )
            return ActiveTrialErrorType.KEY_NOT_FOUND

        except VpnGatewayError as e:
            async with self._uow as uow:
                await uow.audits.add(
                    AuditLog(
                        level=AuditLevel.ERROR,
                        event_type=AuditEventType.VPN_ERROR,
                        message=f"Не удалось получить ссылку ключа пробного периода. "
                                f"tg_id={tg_id}, key_id={key_id}, Ошибка: {e}"
                    )
                )
            return ActiveTrialErrorType.UNKNOWN_ERROR

    async def _finalize(self, key_id: int, payment_id: int, now: datetime,
                        vless_link: str, need_create_vpn: bool) -> None:
        if not need_create_vpn:
            return

        async with self._uow as uow:
            key = await uow.keys.get_for_update(key_id)
            key.vless_link = vless_link
            await uow.keys.update(key)

            payment = await uow.payments.get_for_update(payment_id)
            payment.status = PaymentStatus.COMPLETED
            payment.granted_at = now
            await uow.payments.update(payment)

    async def _create_trial_key(self, uow: AbstractUnitOfWork, user: User, plan: Plan, server_id: int,
                                now: datetime, expiry_time: datetime) -> AccessKey:
        """Создаёт ключ пробного периода в БД."""
        key = AccessKey(
            user_id=user.id,
            plan_id=plan.id,
            server_id=server_id,
            end_at=expiry_time,
            start_at=now,
        )
        await uow.keys.add(key)
        return key

    async def _create_trial_payment(self, uow: AbstractUnitOfWork, user: User,
                                    plan: Plan, key: AccessKey, now: datetime) -> Payment:
        """Создаёт платеж для идемпотентности пробного периода."""
        payment = Payment(
            user_id=user.id,
            plan_id=plan.id,
            price=plan.price,
            type=PaymentType.TRIAL,
            action=PaymentAction.CREATE,
            provider=PaymentProvider.INTERNAL,
            provider_payment_id=str(uuid4()),
            status=PaymentStatus.PROCESSING,
            key_id=key.id,
            created_at=now,
            paid_at=now
        )
        await uow.payments.add(payment)
        return payment

    async def _audit(self, uow: AbstractUnitOfWork, level: AuditLevel, event: AuditEventType, message: str):
        await uow.audits.add(
            AuditLog(
                level=level,
                event_type=event,
                message=message
            )
        )