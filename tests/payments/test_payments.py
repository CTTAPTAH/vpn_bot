"""
Тесты платёжной подсистемы.

Покрывают 11 тест-кейсов из таблицы 2 курсовой работы:
- создание платежа через PlategaClient (TC-1, TC-2, TC-3)
- обработка webhook-запросов (TC-4 — TC-11)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport

from infrastructure.payments.platega.client import PlategaClient
from infrastructure.http.exceptions import HttpTimeoutError


# ===========================================================================
# Вспомогательные фабрики
# ===========================================================================

def make_http_response(status_code: int = 200, json_data: dict | None = None):
    """Мок httpx.Response для PlategaClient."""
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = json_data or {}
    mock.text = str(json_data)
    return mock


def make_dto(success: bool = True, tg_chat_id: int | None = 123,
             tg_message_id: int | None = 456, error: str | None = None):
    """Мок DTO, возвращаемого use case."""
    dto = MagicMock()
    dto.success = success
    dto.tg_chat_id = tg_chat_id
    dto.tg_message_id = tg_message_id
    dto.error = error
    return dto


# ===========================================================================
# Фикстуры
# ===========================================================================

@pytest.fixture
def http_mock():
    return AsyncMock()


@pytest.fixture
def platega(http_mock):
    return PlategaClient(http_client=http_mock)


@pytest.fixture
def app():
    """FastAPI-приложение для тестирования webhook."""
    from presentation.api.main import app
    return app


# ===========================================================================
# TC-1: Успешное создание платежа
# ===========================================================================

async def test_create_payment_success(platega, http_mock):
    """TC-1: Корректные параметры — возвращается transaction_id и redirect_url."""
    from domain.enums import PaymentMethod

    http_mock.post.return_value = make_http_response(200, {
        "transactionId": "txn-001",
        "redirect": "https://pay.example.com/txn-001"
    })

    result = await platega.create_payment(
        payment_method=PaymentMethod.SBPQR,
        amount=299.0,
        currency="RUB",
        description="VPN 1 месяц"
    )

    assert result.transaction_id == "txn-001"
    assert result.redirect_url == "https://pay.example.com/txn-001"


# ===========================================================================
# TC-2: Ошибка при создании платежа (не 200)
# ===========================================================================

async def test_create_payment_non_200(platega, http_mock):
    """TC-2: API вернул 500 — выбрасывается исключение."""
    from domain.enums import PaymentMethod

    http_mock.post.return_value = make_http_response(500, {"error": "Internal Server Error"})

    with pytest.raises(Exception, match="non-200"):
        await platega.create_payment(
            payment_method=PaymentMethod.SBPQR,
            amount=299.0,
            currency="RUB",
            description="VPN 1 месяц"
        )


# ===========================================================================
# TC-3: Сетевая ошибка (timeout) — retry, затем исключение
# ===========================================================================

@patch("infrastructure.payments.platega.client.asyncio.sleep", new_callable=AsyncMock)
async def test_create_payment_timeout_retry(mock_sleep, platega, http_mock):
    """TC-3: При таймауте выполняются повторные попытки, затем выбрасывается ошибка."""
    from domain.enums import PaymentMethod

    http_mock.post.side_effect = HttpTimeoutError("timeout")

    with pytest.raises(HttpTimeoutError):
        await platega.create_payment(
            payment_method=PaymentMethod.SBPQR,
            amount=299.0,
            currency="RUB",
            description="VPN 1 месяц"
        )

    # PLATEGA_RETRY_ATTEMPTS=2, значит sleep вызван 1 раз между попытками
    assert mock_sleep.call_count == 1


# ===========================================================================
# Webhook тесты — общие патчи
# ===========================================================================
#
# payments.py тянет build_uow, get_vpn_gateway_factory, bot, keyboards, texts.
# Все они мокируются через patch, чтобы тесты не требовали БД и Telegram.
PATCHES = {
    "build_uow":             "presentation.api.routes.payments.build_uow",
    "get_factory":           "presentation.api.routes.payments.get_vpn_gateway_factory",
    "confirm_use_case":      "presentation.api.routes.payments.ConfirmPaymentUseCase",
    "failed_use_case":       "presentation.api.routes.payments.HandleFailedPaymentUseCase",
    "bot":                   "presentation.api.routes.payments.bot",
    "keyboards":             "presentation.api.routes.payments.keyboards",
    "texts":                 "presentation.api.routes.payments.texts",
    "server_selection":      "presentation.api.routes.payments.ServerSelectionService",
}

VALID_HEADERS = {
    "X-MerchantId": "test_merchant",
    "X-Secret":     "test_api_key",
}


@pytest.fixture
def webhook_mocks():
    """Запускает все патчи для webhook-тестов и возвращает словарь моков."""
    with patch(PATCHES["build_uow"]) as mock_uow, \
         patch(PATCHES["get_factory"]) as mock_factory, \
         patch(PATCHES["confirm_use_case"]) as mock_confirm_cls, \
         patch(PATCHES["failed_use_case"]) as mock_failed_cls, \
         patch(PATCHES["bot"]) as mock_bot, \
         patch(PATCHES["keyboards"]) as mock_kb, \
         patch(PATCHES["texts"]) as mock_texts, \
         patch(PATCHES["server_selection"]) as mock_ss:

        mock_bot.edit_message_text = AsyncMock()
        mock_bot.send_message = AsyncMock()
        mock_kb.kb_purchase_success.return_value = MagicMock()
        mock_kb.kb_error.return_value = MagicMock()
        mock_texts.txt_purchase_success.return_value = "Успешно!"
        mock_texts.txt_payment_cancelled.return_value = "Отменено."
        mock_texts.txt_unknown_error.return_value = "Ошибка."

        yield {
            "uow": mock_uow,
            "factory": mock_factory,
            "confirm_cls": mock_confirm_cls,
            "failed_cls": mock_failed_cls,
            "bot": mock_bot,
            "kb": mock_kb,
            "texts": mock_texts,
        }


# ===========================================================================
# TC-4: Webhook с корректными заголовками
# ===========================================================================

async def test_webhook_valid_headers(app, webhook_mocks):
    """TC-4: Валидные заголовки — запрос принимается (не 401)."""
    confirm_mock = AsyncMock()
    confirm_mock.execute.return_value = make_dto(success=True)
    webhook_mocks["confirm_cls"].return_value = confirm_mock

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/payments/platega/webhook",
            headers=VALID_HEADERS,
            json={"id": "txn-001", "status": "CONFIRMED"}
        )

    assert response.status_code == 200


# ===========================================================================
# TC-5: Webhook с неверными заголовками
# ===========================================================================

async def test_webhook_invalid_headers(app, webhook_mocks):
    """TC-5: Неверный X-Secret — возвращается 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/payments/platega/webhook",
            headers={"X-MerchantId": "test_merchant", "X-Secret": "wrong"},
            json={"id": "txn-001", "status": "CONFIRMED"}
        )

    assert response.status_code == 401


# ===========================================================================
# TC-6: Webhook с некорректным payload
# ===========================================================================

async def test_webhook_invalid_payload(app, webhook_mocks):
    """TC-6: Отсутствует id/status — возвращается 400."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/payments/platega/webhook",
            headers=VALID_HEADERS,
            json={"unexpected_field": "value"}
        )

    assert response.status_code == 400


# ===========================================================================
# TC-7: Успешный платёж (CONFIRMED)
# ===========================================================================

async def test_webhook_confirmed(app, webhook_mocks):
    """TC-7: status=CONFIRMED — вызывается ConfirmPaymentUseCase."""
    confirm_mock = AsyncMock()
    confirm_mock.execute.return_value = make_dto(success=True)
    webhook_mocks["confirm_cls"].return_value = confirm_mock

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/payments/platega/webhook",
            headers=VALID_HEADERS,
            json={"id": "txn-001", "status": "CONFIRMED"}
        )

    assert response.status_code == 200
    confirm_mock.execute.assert_called_once()


# ===========================================================================
# TC-8: Отменённый платёж (CANCELED)
# ===========================================================================

async def test_webhook_canceled(app, webhook_mocks):
    """TC-8: status=CANCELED — вызывается HandleFailedPaymentUseCase."""
    failed_mock = AsyncMock()
    failed_mock.execute.return_value = make_dto(success=True)
    webhook_mocks["failed_cls"].return_value = failed_mock

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/payments/platega/webhook",
            headers=VALID_HEADERS,
            json={"id": "txn-002", "status": "CANCELED"}
        )

    assert response.status_code == 200
    failed_mock.execute.assert_called_once()


# ===========================================================================
# TC-9: Неизвестный статус платежа
# ===========================================================================

async def test_webhook_unknown_status(app, webhook_mocks):
    """TC-9: status=UNKNOWN — запрос игнорируется, возвращается ok=True."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/payments/platega/webhook",
            headers=VALID_HEADERS,
            json={"id": "txn-003", "status": "UNKNOWN"}
        )

    assert response.status_code == 200
    assert response.json() == {"ok": True}


# ===========================================================================
# TC-10: Ошибка use case при CONFIRMED
# ===========================================================================

async def test_webhook_confirmed_use_case_fails(app, webhook_mocks):
    """TC-10: use case вернул ошибку — пользователю отправляется сообщение об ошибке."""
    confirm_mock = AsyncMock()
    confirm_mock.execute.return_value = make_dto(
        success=False,
        error="DB error",
        tg_chat_id=123,
        tg_message_id=456
    )
    webhook_mocks["confirm_cls"].return_value = confirm_mock

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/payments/platega/webhook",
            headers=VALID_HEADERS,
            json={"id": "txn-004", "status": "CONFIRMED"}
        )

    assert response.status_code == 200
    # Пользователю отправляется сообщение об ошибке
    webhook_mocks["bot"].edit_message_text.assert_called_once()


# ===========================================================================
# TC-11: Отсутствует tg_chat_id
# ===========================================================================

async def test_webhook_no_chat_id(app, webhook_mocks):
    """TC-11: dto без tg_chat_id — сообщение не отправляется, логируется ошибка."""
    confirm_mock = AsyncMock()
    confirm_mock.execute.return_value = make_dto(
        success=True,
        tg_chat_id=None,
        tg_message_id=None
    )
    webhook_mocks["confirm_cls"].return_value = confirm_mock

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/payments/platega/webhook",
            headers=VALID_HEADERS,
            json={"id": "txn-005", "status": "CONFIRMED"}
        )

    assert response.status_code == 200
    webhook_mocks["bot"].edit_message_text.assert_not_called()
    webhook_mocks["bot"].send_message.assert_not_called()