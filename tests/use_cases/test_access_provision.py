"""
Тесты выдачи доступа к серверу.

Покрывают 12 тест-кейсов из таблицы 3 курсовой работы:
- выдача доступа после оплаты (TC-1, TC-2)
- продление доступа (TC-3)
- ошибки платежей и планов (TC-4, TC-5)
- ошибки серверов и VPN (TC-6, TC-7, TC-8)
- пробный период (TC-9, TC-10, TC-11)
- отмена платежа (TC-12)
"""

from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

from application.use_cases.confirm_payment import (
    ConfirmPaymentUseCase,
    ConfirmPaymentErrorType,
)
from application.use_cases.activate_trial import (
    ActiveTrialUseCase,
    ActiveTrialSuccess,
    ActiveTrialChooseKey,
)
from application.use_cases.cancel_payment import CancelPaymentUseCase
from application.errors.vpn_errors import VpnClientAlreadyExistsError, VpnGatewayError
from application.services.server_selection import NoAvailableServersError
from domain.enums import PaymentAction, PaymentStatus, PaymentProvider


# ===========================================================================
# Вспомогательные фабрики
# ===========================================================================

def make_payment(
    id: int = 1,
    user_id: int = 10,
    plan_id: int = 1,
    action: PaymentAction = PaymentAction.CREATE,
    status: PaymentStatus = PaymentStatus.PENDING,
    granted_at=None,
    key_id: int | None = None,
):
    p = MagicMock()
    p.id = id
    p.user_id = user_id
    p.plan_id = plan_id
    p.action = action
    p.status = status
    p.granted_at = granted_at
    p.key_id = key_id
    return p


def make_user(id: int = 10, tg_id: int = 999):
    u = MagicMock()
    u.id = id
    u.tg_id = tg_id
    return u


def make_plan(id: int = 1, duration_seconds: int = 2592000, price: float = 0.0):
    p = MagicMock()
    p.id = id
    p.duration_seconds = duration_seconds
    p.price = price
    return p


def make_server(id: int = 1, default_key_name: str = "vpn-key"):
    s = MagicMock()
    s.id = id
    s.default_key_name = default_key_name
    return s


def make_key(id: int = 42, user_id: int = 10, server_id: int = 1, vless_link: str = "vless://test"):
    k = MagicMock()
    k.id = id
    k.user_id = user_id
    k.server_id = server_id
    k.vless_link = vless_link
    k.end_at = datetime(2026, 12, 31, tzinfo=timezone.utc)
    return k


def make_payment_ui(tg_chat_id: int = 123, tg_message_id: int = 456):
    ui = MagicMock()
    ui.tg_chat_id = tg_chat_id
    ui.tg_message_id = tg_message_id
    return ui


def make_uow(**overrides):
    """
    Создаёт мок UoW с настроенными репозиториями.
    async with uow as uow: — работает через __aenter__/__aexit__.
    """
    uow = AsyncMock()
    uow.__aenter__.return_value = uow
    uow.__aexit__.return_value = False

    # Репозитории — AsyncMock по умолчанию
    uow.payments = AsyncMock()
    uow.users = AsyncMock()
    uow.plans = AsyncMock()
    uow.keys = AsyncMock()
    uow.servers = AsyncMock()
    uow.payment_ui_states = AsyncMock()
    uow.audits = AsyncMock()

    for attr, value in overrides.items():
        setattr(uow, attr, value)

    return uow


def make_gateway_factory(
    create_key_side_effect=None,
    update_expiry_side_effect=None,
    vless_link: str = "vless://test-link",
):
    """Создаёт мок фабрики VPN gateway."""
    gateway = AsyncMock()

    if create_key_side_effect:
        gateway.create_key.side_effect = create_key_side_effect
    else:
        gateway.create_key.return_value = None

    if update_expiry_side_effect:
        gateway.update_expiry.side_effect = update_expiry_side_effect

    gateway.get_link.return_value = vless_link

    factory = AsyncMock()
    factory.get_gateway.return_value = gateway
    return factory


def make_selector(server_id: int = 1, raise_error: bool = False):
    selector = AsyncMock()
    if raise_error:
        selector.select_server.side_effect = NoAvailableServersError()
    else:
        selector.select_server.return_value = server_id
    return selector


# ===========================================================================
# TC-1: Выдача доступа после успешной оплаты (создание)
# ===========================================================================

async def test_confirm_payment_create_success():
    """TC-1: Валидный payment с action=CREATE — ключ создаётся, доступ выдан."""
    payment = make_payment(action=PaymentAction.CREATE, status=PaymentStatus.PENDING)
    user = make_user()
    plan = make_plan()
    server = make_server()
    key = make_key()
    payment_ui = make_payment_ui()

    uow = make_uow()
    uow.payments.get_by_provider_and_payment_id_for_update.return_value = payment
    uow.users.get_by_id_for_update.return_value = user
    uow.plans.get_by_id.return_value = plan
    uow.servers.get_id_active_servers.return_value = [1]
    uow.servers.get_by_id.return_value = server
    uow.keys.add = AsyncMock(side_effect=lambda k: setattr(k, "id", 42))
    uow.payments.get_for_update.return_value = payment
    uow.keys.get_for_update.return_value = key
    uow.payment_ui_states.get_by_payment_for_update.return_value = payment_ui

    factory = make_gateway_factory(vless_link="vless://test-link")
    selector = make_selector(server_id=1)

    use_case = ConfirmPaymentUseCase(uow, factory, selector)
    result = await use_case.execute(PaymentProvider.PLATEGA, "txn-001")

    assert result.success is True
    assert result.tg_chat_id == 123


# ===========================================================================
# TC-2: Повторная обработка оплаты (идемпотентность)
# ===========================================================================

async def test_confirm_payment_already_granted():
    """TC-2: granted_at уже установлен — доступ повторно не выдаётся."""
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    payment = make_payment(granted_at=now, action=PaymentAction.CREATE)
    user = make_user()
    payment_ui = make_payment_ui()

    uow = make_uow()
    uow.payments.get_by_provider_and_payment_id_for_update.return_value = payment
    uow.users.get_by_id_for_update.return_value = user
    uow.payment_ui_states.get_by_payment_for_update.return_value = payment_ui

    factory = make_gateway_factory()
    selector = make_selector()

    use_case = ConfirmPaymentUseCase(uow, factory, selector)
    result = await use_case.execute(PaymentProvider.PLATEGA, "txn-001")

    assert result.success is True
    # VPN gateway не должен вызываться при повторной обработке
    factory.get_gateway.assert_not_called()


# ===========================================================================
# TC-3: Продление доступа
# ===========================================================================

async def test_confirm_payment_renew_success():
    """TC-3: action=RENEW — срок действия ключа увеличен."""
    payment = make_payment(action=PaymentAction.RENEW, status=PaymentStatus.PENDING, key_id=42)
    user = make_user()
    plan = make_plan(duration_seconds=2592000)
    key = make_key(id=42, user_id=10)
    server = make_server()
    payment_ui = make_payment_ui()

    uow = make_uow()
    uow.payments.get_by_provider_and_payment_id_for_update.return_value = payment
    uow.users.get_by_id_for_update.return_value = user
    uow.plans.get_by_id.return_value = plan
    uow.keys.get_for_update.return_value = key
    uow.servers.get_by_id.return_value = server
    uow.payments.get_for_update.return_value = payment
    uow.payment_ui_states.get_by_payment_for_update.return_value = payment_ui

    factory = make_gateway_factory()
    selector = make_selector()

    use_case = ConfirmPaymentUseCase(uow, factory, selector)
    result = await use_case.execute(PaymentProvider.PLATEGA, "txn-002")

    assert result.success is True
    factory.get_gateway.assert_called_once()


# ===========================================================================
# TC-4: Платёж не найден
# ===========================================================================

async def test_confirm_payment_not_found():
    """TC-4: Платёж не найден в БД — возвращается PAYMENT_NOT_FOUND."""
    uow = make_uow()
    uow.payments.get_by_provider_and_payment_id_for_update.return_value = None

    factory = make_gateway_factory()
    selector = make_selector()

    use_case = ConfirmPaymentUseCase(uow, factory, selector)
    result = await use_case.execute(PaymentProvider.PLATEGA, "txn-999")

    assert result.success is False
    assert result.error == ConfirmPaymentErrorType.PAYMENT_NOT_FOUND


# ===========================================================================
# TC-5: Тариф не найден
# ===========================================================================

async def test_confirm_payment_plan_not_found():
    """TC-5: Тариф не найден в БД — возвращается PLAN_NOT_FOUND."""
    payment = make_payment(action=PaymentAction.CREATE, status=PaymentStatus.PENDING)
    user = make_user()

    uow = make_uow()
    uow.payments.get_by_provider_and_payment_id_for_update.return_value = payment
    uow.users.get_by_id_for_update.return_value = user
    uow.plans.get_by_id.return_value = None
    uow.payments.get_for_update.return_value = payment

    factory = make_gateway_factory()
    selector = make_selector()

    use_case = ConfirmPaymentUseCase(uow, factory, selector)
    result = await use_case.execute(PaymentProvider.PLATEGA, "txn-003")

    assert result.success is False
    assert result.error == ConfirmPaymentErrorType.PLAN_NOT_FOUND


# ===========================================================================
# TC-6: Нет доступных серверов
# ===========================================================================

async def test_confirm_payment_no_available_servers():
    """TC-6: Нет доступных серверов — возвращается NO_AVAILABLE_SERVERS."""
    payment = make_payment(action=PaymentAction.CREATE, status=PaymentStatus.PENDING)
    user = make_user()
    plan = make_plan()

    uow = make_uow()
    uow.payments.get_by_provider_and_payment_id_for_update.return_value = payment
    uow.users.get_by_id_for_update.return_value = user
    uow.plans.get_by_id.return_value = plan
    uow.servers.get_id_active_servers.return_value = []
    uow.payments.get_for_update.return_value = payment

    factory = make_gateway_factory()
    selector = make_selector(raise_error=True)

    use_case = ConfirmPaymentUseCase(uow, factory, selector)
    result = await use_case.execute(PaymentProvider.PLATEGA, "txn-004")

    assert result.success is False
    assert result.error == ConfirmPaymentErrorType.NO_AVAILABLE_SERVERS


# ===========================================================================
# TC-7: Ошибка VPN при создании ключа
# ===========================================================================

async def test_confirm_payment_vpn_gateway_error():
    """TC-7: VpnGatewayError при создании ключа — возвращается UNKNOWN_ERROR."""
    payment = make_payment(action=PaymentAction.CREATE, status=PaymentStatus.PENDING)
    user = make_user()
    plan = make_plan()
    server = make_server()
    key = make_key()

    uow = make_uow()
    uow.payments.get_by_provider_and_payment_id_for_update.return_value = payment
    uow.users.get_by_id_for_update.return_value = user
    uow.plans.get_by_id.return_value = plan
    uow.servers.get_id_active_servers.return_value = [1]
    uow.servers.get_by_id.return_value = server
    uow.keys.add = AsyncMock(side_effect=lambda k: setattr(k, "id", 42))
    uow.payments.get_for_update.return_value = payment

    factory = make_gateway_factory(create_key_side_effect=VpnGatewayError("vpn down"))
    selector = make_selector(server_id=1)

    use_case = ConfirmPaymentUseCase(uow, factory, selector)
    result = await use_case.execute(PaymentProvider.PLATEGA, "txn-005")

    assert result.success is False
    assert result.error == ConfirmPaymentErrorType.UNKNOWN_ERROR


# ===========================================================================
# TC-8: Ключ уже существует в VPN
# ===========================================================================

async def test_confirm_payment_key_already_exists():
    """TC-8: VpnClientAlreadyExistsError — возвращается KEY_ALREADY_EXISTS."""
    payment = make_payment(action=PaymentAction.CREATE, status=PaymentStatus.PENDING)
    user = make_user()
    plan = make_plan()
    server = make_server()
    key = make_key()

    uow = make_uow()
    uow.payments.get_by_provider_and_payment_id_for_update.return_value = payment
    uow.users.get_by_id_for_update.return_value = user
    uow.plans.get_by_id.return_value = plan
    uow.servers.get_id_active_servers.return_value = [1]
    uow.servers.get_by_id.return_value = server
    uow.keys.add = AsyncMock(side_effect=lambda k: setattr(k, "id", 42))
    uow.payments.get_for_update.return_value = payment

    factory = make_gateway_factory(create_key_side_effect=VpnClientAlreadyExistsError())
    selector = make_selector(server_id=1)

    use_case = ConfirmPaymentUseCase(uow, factory, selector)
    result = await use_case.execute(PaymentProvider.PLATEGA, "txn-006")

    assert result.success is False
    assert result.error == ConfirmPaymentErrorType.KEY_ALREADY_EXISTS


# ===========================================================================
# TC-9: Выдача пробного периода (первый раз)
# ===========================================================================

async def test_active_trial_first_time():
    """TC-9: Новый пользователь — создаётся ключ и выдаётся пробный доступ."""
    user = make_user()
    plan = make_plan(duration_seconds=604800)  # 7 дней
    server = make_server()
    key = make_key()
    payment = MagicMock()
    payment.id = 1
    payment.user_id = user.id
    payment.status = PaymentStatus.PROCESSING
    payment.key_id = key.id

    uow = make_uow()
    uow.users.get_or_create.return_value = user
    uow.payments.get_user_trial_for_update.return_value = None  # первый раз
    uow.plans.get_trial.return_value = plan
    uow.keys.count_all_keys.return_value = 0
    uow.servers.get_id_active_servers.return_value = [1]
    uow.servers.get_by_id.return_value = server
    uow.keys.add = AsyncMock(side_effect=lambda k: setattr(k, "id", 42))
    uow.payments.add = AsyncMock(side_effect=lambda p: setattr(p, "id", 1) or setattr(p, "user_id", user.id))
    uow.keys.get_for_update.return_value = key
    uow.payments.get_for_update.return_value = payment

    factory = make_gateway_factory(vless_link="vless://trial-link")
    selector = make_selector(server_id=1)

    use_case = ActiveTrialUseCase(uow, factory, selector)
    result = await use_case.execute(tg_id=999, username="testuser")

    assert isinstance(result, ActiveTrialSuccess)
    assert result.vless_link == "vless://trial-link"
    assert result.num_days == 7


# ===========================================================================
# TC-10: Повторный запрос пробного периода
# ===========================================================================

async def test_active_trial_repeat_request():
    """TC-10: Пользователь уже получал trial — возвращаются существующие данные."""
    user = make_user()
    plan = make_plan(duration_seconds=604800)
    server = make_server()
    key = make_key()

    existing_payment = MagicMock()
    existing_payment.id = 1
    existing_payment.user_id = user.id
    existing_payment.status = PaymentStatus.CONFIRMED  # уже завершён
    existing_payment.key_id = key.id

    uow = make_uow()
    uow.users.get_or_create.return_value = user
    uow.payments.get_user_trial_for_update.return_value = existing_payment  # уже есть
    uow.plans.get_trial.return_value = plan
    uow.keys.get_by_id.return_value = key
    uow.servers.get_by_id.return_value = server

    factory = make_gateway_factory(vless_link="vless://existing-link")
    selector = make_selector()

    use_case = ActiveTrialUseCase(uow, factory, selector)
    result = await use_case.execute(tg_id=999, username="testuser")

    assert isinstance(result, ActiveTrialSuccess)
    assert result.vless_link == "vless://existing-link"


# ===========================================================================
# TC-11: Превышен лимит ключей
# ===========================================================================

async def test_active_trial_key_limit_exceeded():
    """TC-11: Количество ключей >= 5 — предлагается выбрать ключ для продления."""
    user = make_user()
    plan = make_plan(duration_seconds=604800)

    # Мок view-объектов ключей
    key_views = []
    for i in range(5):
        v = MagicMock()
        v.id = i + 1
        v.plan_name = "Базовый"
        v.end_at = datetime(2026, 6, 1, tzinfo=timezone.utc)
        key_views.append(v)

    uow = make_uow()
    uow.users.get_or_create.return_value = user
    uow.payments.get_user_trial_for_update.return_value = None
    uow.plans.get_trial.return_value = plan
    uow.keys.count_all_keys.return_value = 5
    uow.keys.list_view_by_user.return_value = key_views

    factory = make_gateway_factory()
    selector = make_selector()

    use_case = ActiveTrialUseCase(uow, factory, selector)
    result = await use_case.execute(tg_id=999, username="testuser")

    assert isinstance(result, ActiveTrialChooseKey)
    assert result.count_keys == 5
    assert len(result.keys) == 5


# ===========================================================================
# TC-12: Отмена платежа пользователем
# ===========================================================================

async def test_cancel_payment_success():
    """TC-12: Pending payment найден — статус меняется на FAILED."""
    user = make_user()
    payment = make_payment(status=PaymentStatus.PENDING)

    uow = make_uow()
    uow.users.get_or_create.return_value = user
    uow.payments.get_user_pending_payment_for_update.return_value = payment

    use_case = CancelPaymentUseCase(uow)
    result = await use_case.execute(tg_id=999, username="testuser")

    assert result.success is True
    assert payment.status == PaymentStatus.FAILED