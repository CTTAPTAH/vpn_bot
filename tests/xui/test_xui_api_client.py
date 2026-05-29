"""
Тесты для XuiApiClient.

Покрывают 14 тест-кейсов из таблицы 1 курсовой работы:
- получение inbound
- поиск, создание, обновление, удаление клиентов
- обработку ошибок авторизации
- механизм retry при сетевых ошибках
- обработку некорректных ответов API
"""

import pytest
from unittest.mock import AsyncMock, patch

from infrastructure.xui.exceptions import (
    XuiAuthenticationError,
    XuiInvalidResponseError,
    XuiClientNotFoundError,
    XuiClientAlreadyExistsError,
)
from infrastructure.http.exceptions import HttpTimeoutError
from tests.xui.factories import make_response, make_inbound_response

# ---------------------------------------------------------------------------
# TC-01: Получение inbound по корректному id
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_inbound_by_id_success(xui, http_mock):
    """TC-01: Возвращается объект Inbound с корректными данными."""
    http_mock.get.return_value = make_response(200, make_inbound_response())

    inbound = await xui.get_inbound_by_id(1)

    assert inbound.id == 1
    assert inbound.remark == "test-inbound"
    assert len(inbound.clients) == 1
    assert inbound.clients[0].email == "test"


# ---------------------------------------------------------------------------
# TC-02: Получение inbound с некорректным JSON
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_inbound_invalid_json(xui, http_mock):
    """TC-02: При невалидном JSON возникает XuiInvalidResponseError."""
    http_mock.get.return_value = make_response(200, raise_json=True)

    with pytest.raises(XuiInvalidResponseError):
        await xui.get_inbound_by_id(1)


# ---------------------------------------------------------------------------
# TC-03: Поиск существующего клиента
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_find_client_found(xui, http_mock):
    """TC-03: Клиент найден и возвращён."""
    http_mock.get.return_value = make_response(200, make_inbound_response(email="test"))

    client = await xui.find_client("test", 1)

    assert client is not None
    assert client.email == "test"


# ---------------------------------------------------------------------------
# TC-04: Поиск несуществующего клиента
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_find_client_not_found(xui, http_mock):
    """TC-04: Клиент не найден — возвращается None."""
    http_mock.get.return_value = make_response(200, make_inbound_response(email="other"))

    client = await xui.find_client("unknown", 1)

    assert client is None


# ---------------------------------------------------------------------------
# TC-05: Проверка существования клиента (is_client_exists)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_is_client_exists_true(xui, http_mock):
    """TC-05: Клиент существует — возвращается True."""
    http_mock.get.return_value = make_response(200, make_inbound_response(email="test"))

    result = await xui.is_client_exists("test", 1)

    assert result is True


# ---------------------------------------------------------------------------
# TC-06: Создание нового клиента
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_add_client_success(xui, http_mock):
    """TC-06: Новый клиент успешно создаётся."""
    # Первый GET — inbound без клиента "new"
    empty_inbound = make_inbound_response(email="existing")
    # POST — успешный ответ на добавление
    success_response = make_response(200, {"success": True, "obj": {}})

    http_mock.get.return_value = make_response(200, empty_inbound)
    http_mock.post.return_value = success_response

    # Не должно выбросить исключение
    await xui.add_client(inbound_id=1, email="new", uuid="fixed-uuid-1234")


# ---------------------------------------------------------------------------
# TC-07: Создание клиента с уже существующим UUID
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_add_client_already_exists(xui, http_mock):
    """TC-07: Попытка создать клиента с uuid, который уже есть — XuiClientAlreadyExistsError."""
    # Inbound уже содержит клиента с uuid "some-uuid"
    http_mock.get.return_value = make_response(200, make_inbound_response(email="test"))

    with pytest.raises(XuiClientAlreadyExistsError):
        # uuid "some-uuid" уже есть в make_inbound_response
        await xui.add_client(inbound_id=1, email="new", uuid="some-uuid")


# ---------------------------------------------------------------------------
# TC-08: Обновление существующего клиента
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_client_success(xui, http_mock):
    """TC-08: Данные клиента обновляются без ошибок."""
    http_mock.get.return_value = make_response(200, make_inbound_response(email="test"))
    http_mock.post.return_value = make_response(200, {"success": True, "obj": {}})

    # Не должно выбросить исключение
    await xui.update_client("test", 1, enabled=False)


# ---------------------------------------------------------------------------
# TC-09: Обновление несуществующего клиента
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_client_not_found(xui, http_mock):
    """TC-09: Клиент не найден — возникает XuiClientNotFoundError."""
    http_mock.get.return_value = make_response(200, make_inbound_response(email="other"))

    with pytest.raises(XuiClientNotFoundError):
        await xui.update_client("nonexistent", 1, enabled=False)


# ---------------------------------------------------------------------------
# TC-10: Удаление существующего клиента
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_client_success(xui, http_mock):
    """TC-10: Клиент удаляется без ошибок."""
    http_mock.get.return_value = make_response(200, make_inbound_response(email="test"))
    http_mock.post.return_value = make_response(200, {"success": True, "obj": {}})

    # Не должно выбросить исключение
    await xui.delete_client("test", 1)


# ---------------------------------------------------------------------------
# TC-11: Удаление несуществующего клиента
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_client_not_found(xui, http_mock):
    """TC-11: Клиент не найден — возникает XuiClientNotFoundError."""
    http_mock.get.return_value = make_response(200, make_inbound_response(email="other"))

    with pytest.raises(XuiClientNotFoundError):
        await xui.delete_client("nonexistent", 1)


# ---------------------------------------------------------------------------
# TC-12: Ошибка авторизации — повторный логин, при неудаче XuiAuthenticationError
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reauth_on_401_fails(xui, http_mock):
    """
    TC-12: API возвращает 401 — система пытается перелогиниться.
    Если повторный запрос снова 401 — выбрасывается XuiAuthenticationError.
    """
    # Первый GET — 401, после логина снова 401
    response_401 = make_response(401, {"success": False})
    # POST на /login — успешен (сам логин проходит)
    login_ok = make_response(200, {"success": True})

    http_mock.get.return_value = response_401
    http_mock.post.return_value = login_ok

    with pytest.raises(XuiAuthenticationError):
        await xui.get_inbound_by_id(1)


# ---------------------------------------------------------------------------
# TC-13: Сетевая ошибка (timeout) — retry, при превышении попыток — ошибка
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@patch("infrastructure.xui.api_client.asyncio.sleep", new_callable=AsyncMock)
async def test_retry_on_timeout(mock_sleep, xui, http_mock):
    """
    TC-13: При таймауте система делает повторные попытки.
    После исчерпания попыток (XUI_RETRY_ATTEMPTS=3) выбрасывается HttpTimeoutError.
    """
    http_mock.get.side_effect = HttpTimeoutError("Request timeout")

    with pytest.raises(HttpTimeoutError):
        await xui.get_inbound_by_id(1)

    # Убеждаемся, что sleep вызывался между попытками (retry работал)
    assert mock_sleep.call_count == 2  # 3 попытки = 2 паузы


# ---------------------------------------------------------------------------
# TC-14: Некорректный ответ API (success=false)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_request_success_false(xui, http_mock):
    """TC-14: API вернул success=false — возникает XuiInvalidResponseError."""
    http_mock.get.return_value = make_response(200, {"success": False, "msg": "some error"})

    with pytest.raises(XuiInvalidResponseError):
        await xui.get_inbound_by_id(1)