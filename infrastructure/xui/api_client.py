"""
Async XUI API client.

Инкапсулирует:
- авторизацию
- работу с inbound'ами
- работу с клиентами
- преобразование ответов XUI в модели

Не содержит HTTP-деталей (их обрабатывает XuiHttpClient).
"""

import json, asyncio, httpx, logging
from uuid import uuid4
from httpx import Response

from infrastructure.http.http_client import HttpClient
from infrastructure.xui.exceptions import (
    XuiAuthenticationError,
    XuiInvalidResponseError,
    XuiClientNotFoundError,
    XuiClientAlreadyExistsError,
)

from infrastructure.xui.models import Inbound, Client
from infrastructure.xui.enums import HttpMethod
from infrastructure.http.exceptions import HttpConnectionError, HttpTimeoutError
import core.config as config

logger = logging.getLogger(__name__)

class XuiApiClient:
    """
    Высокоуровневый API-клиент XUI.

    Отвечает за:
    - вызовы XUI API
    - валидацию ответа
    - преобразование dict → модели
    """

    def __init__(self, http_client: HttpClient, username: str, password: str, host: str) -> None:
        self._http = http_client
        self._username = username
        self._password = password
        self._host = host
        self._inbound_cache: Inbound | None = None

    async def _send(self, method: HttpMethod, url: str, **kwargs) -> Response:
        """Отправка api запроса."""
        if method is HttpMethod.GET:
            return await self._http.get(url, **kwargs)

        if method is HttpMethod.POST:
            return await self._http.post(url, **kwargs)

        raise ValueError(f"Unsupported HTTP method: {method}")

    async def _request(self, method: HttpMethod, url: str, **kwargs) -> dict | list:
        """
        Универсальный метод для вызова XUI API.
        Обрабатывает success-флаг и возвращает obj.
        """
        attempt = 0
        delay = config.XUI_RETRY_BASE_DELAY

        while attempt < config.XUI_RETRY_ATTEMPTS:
            try:
                response = await self._send(method, url, **kwargs)

                # Если сессия умерла - перелогин
                if response.status_code in (401, 403, 404):
                    await self.login()
                    response: httpx.Response = await self._send(method, url, **kwargs)

                    if response.status_code in (401, 403, 404):
                        raise XuiAuthenticationError("Re-authentication failed")

                try:
                    data = response.json()
                except Exception as exc:
                    raise XuiInvalidResponseError("Invalid JSON response") from exc

                if not data.get("success", False):
                    raise XuiInvalidResponseError(f"XUI returned error: {data}")

                if "obj" not in data:
                    raise XuiInvalidResponseError("Missing 'obj' in response")

                return data.get("obj")

            except (HttpConnectionError, HttpTimeoutError) as e:
                logger.warning("Ошибка соединения с XUI: %s. Попытка %d/%d", e, attempt, config.XUI_RETRY_ATTEMPTS)
                attempt += 1
                if attempt >= config.XUI_RETRY_ATTEMPTS:
                    logger.error("Превышено количество попыток соединения")
                    raise
                await asyncio.sleep(delay)
                delay *= config.XUI_RETRY_MULTIPLIER

        # На всякий случай, IDE поймёт, что функция всегда либо вернёт, либо выбросит исключение
        raise RuntimeError("Unexpected error in _request")

    async def login(self) -> None:
        """Выполняет авторизацию в XUI."""
        logger.info("Попытка авторизации в XUI...")
        response = await self._http.post(
            "login",
            data={
                "username": self._username,
                "password": self._password
            },
        )

        try:
            data = response.json()
        except Exception as exc:
            logger.error("Ошибка разбора JSON при авторизации")
            raise XuiInvalidResponseError("Invalid JSON response") from exc

        if not data.get("success"):
            logger.error("Авторизация не удалась")
            raise XuiAuthenticationError("Authentication failed")

        logger.info("Авторизация успешна")

    # INBOUNDS
    async def get_inbound_by_id(self, inbound_id: int) -> Inbound:
        """Возвращает конкретный inbound по заданному id."""
        if self._inbound_cache is not None:
            return self._inbound_cache

        raw = await self._request(
            HttpMethod.GET,
            f"panel/api/inbounds/get/{inbound_id}",
        )

        self._inbound_cache = Inbound.from_dict(raw)
        return self._inbound_cache

    # CLIENTS
    async def get_clients(self, inbound_id: int) -> list[Client]:
        """Получить всех клиентов в определённом inbond'е."""
        inbound = await self.get_inbound_by_id(inbound_id)

        return inbound.clients

    async def find_client(self, email: str, inbound_id: int) -> Client | None:
        """Ищет клиента по email в заданном inbound'е."""
        clients = await self.get_clients(inbound_id)

        for client in clients:
            if client.email == email:
                return client

        return None

    async def find_client_by_uuid(self, uuid: str, inbound_id: int) -> Client | None:
        """Ищет клиента по uuid в заданном inbound'е."""
        clients = await self.get_clients(inbound_id)
        for client in clients:
            if client.uuid == uuid:
                return client
        return None

    async def is_client_exists(self, email: str, inbound_id: int) -> bool:
        """Проверяет, существует ли клиент с данным email в указанном inbound'е."""
        return (await self.find_client(email, inbound_id)) is not None

    async def is_client_enabled(self, email: str, inbound_id: int) -> bool:
        """Возвращает True, если клиент включён в указанном inbound'е."""
        client = await self.find_client(email, inbound_id)
        if client is not None:
            return client.enabled

        return False

    async def get_client_expiry(self, email: str, inbound_id: int) -> int | None:
        """
        Возвращает expiryTime клиента (timestamp в мс) в указанном inbound'е.
        Возвращает None, если клиента нет или срок не задан.
        """
        client = await self.find_client(email, inbound_id)
        if client is not None:
            return client.expiry_time
        return None

    async def is_client_expired(self, email: str, inbound_id: int) -> bool:
        """True, если срок действия истёк."""
        client = await self.find_client(email, inbound_id)
        if client is not None:
            return client.is_expired()

        return False

    async def get_client_link(self, email: str, inbound_id: int, key_name: str) -> str:
        """Генерирует VLESS-ссылку для клиента."""
        client = await self.find_client(email, inbound_id)
        if client is None:
            raise XuiInvalidResponseError(f"Client {email} not found")

        inbound = await self.get_inbound_by_id(client.inbound_id)
        if inbound is None:
            raise RuntimeError(f"Inbound {client.inbound_id} not found")

        stream = inbound.get_stream_settings()
        reality = stream.get("realitySettings", {})
        reality_settings = reality.get("settings", {})

        uuid = client.uuid
        port = inbound.port
        type_network = stream.get("network", "tcp")
        encryption = "none"
        security = stream.get("security", "reality")
        pbk = reality_settings.get("publicKey", None)
        fp = "chrome"
        sni = reality.get("serverNames", [None])[0]
        short_ids = reality.get("shortIds", [])
        sid = short_ids[0] if short_ids else None
        spx = reality_settings.get("spiderX", "/")

        return (
            f"vless://{uuid}@{self._host}:{port}?type={type_network}&encryption={encryption}&security={security}"
            f"&pbk={pbk}&fp={fp}&sni={sni}&sid={sid}&spx={spx}#{key_name}"
        )

    # CRUD
    def _build_client_payload(self, *, inbound_id: int, uuid: str, email: str,
                              enable: bool, expiry_time: int) -> dict:
        """Формирует payload для add/update клиента."""
        return {
            "id": inbound_id,
            "settings": json.dumps({
                "clients": [
                    {
                        "id": uuid,
                        "email": email,
                        "enable": enable,
                        "expiryTime": expiry_time,
                        "limitIp": config.MAX_DEVICE_PER_KEY
                    }
                ]
            }),
        }

    async def update_client(self, email: str, inbound_id: int, *, new_email: str = None,
                            enabled: bool = None, expiry_time: int = None) -> None:
        """Универсальный метод для обновления клиента."""
        logger.info("Обновляется клиент %s в inbound '%s'", email, inbound_id)

        client = await self.find_client(email, inbound_id)
        if client is None:
            raise XuiClientNotFoundError(f"Client {email} not found")

        payload = self._build_client_payload(
            inbound_id=client.inbound_id,
            uuid=client.uuid,
            email=client.email if new_email is None else new_email,
            enable=client.enabled if enabled is None else enabled,
            expiry_time=client.expiry_time if expiry_time is None else expiry_time,
        )

        self._inbound_cache = None
        await self._request(HttpMethod.POST, f"panel/api/inbounds/updateClient/{client.uuid}", json=payload)

    async def add_client(self, inbound_id: int, email: str, *, uuid: str | None = None,
                         expiry_time: int = 0, enable: bool = True) -> None:
        """
        Создаёт нового клиента в указанном inbound.
        :param inbound_id: название inbound'а
        :param email: email клиента (идентификатор)
        :param uuid: UUID клиента
        :param expiry_time: timestamp в мс или None (бессрочно)
        :param enable: включён ли клиент
        """
        logger.info("Создаётся клиент %s в inbound '%s'", email, inbound_id)
        inbound = await self.get_inbound_by_id(inbound_id)

        if uuid is None:
            uuid = str(uuid4())
        if await self.find_client_by_uuid(uuid, inbound_id):
            raise XuiClientAlreadyExistsError(f"Client with uuid {uuid} already exists")

        payload = self._build_client_payload(
            inbound_id=inbound.id,
            uuid=uuid,
            email=email,
            enable=enable,
            expiry_time=expiry_time,
        )

        self._inbound_cache = None
        await self._request(HttpMethod.POST, f"panel/api/inbounds/addClient", json=payload)

    async def delete_client(self, email: str, inbound_id: int):
        """Удаление клиента."""
        logger.info("Удаляется клиент %s из inbound '%s'", email, inbound_id)

        client = await self.find_client(email, inbound_id)
        if client is None:
            raise XuiClientNotFoundError(f"Client {email} not found")

        self._inbound_cache = None
        await self._request(HttpMethod.POST, f"panel/api/inbounds/{client.inbound_id}/delClient/{client.uuid}")