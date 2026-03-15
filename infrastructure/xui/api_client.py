"""
Async XUI API client.

Инкапсулирует:
- авторизацию
- работу с inbound'ами
- работу с клиентами
- преобразование ответов XUI в модели

Не содержит HTTP-деталей (их обрабатывает XuiHttpClient).
"""

import json
from uuid import uuid4

from infrastructure.xui.http_client import XuiHttpClient
from infrastructure.xui.exceptions import (
    XuiAuthenticationError,
    XuiInvalidResponseError,
    XuiClientNotFoundError,
    XuiClientAlreadyExistsError,
)

from infrastructure.xui.models import Inbound, Client
from infrastructure.xui.enums import HttpMethod

class XuiApiClient:
    """
    Высокоуровневый API-клиент XUI.

    Отвечает за:
    - вызовы XUI API
    - валидацию ответа
    - преобразование dict → модели
    """

    def __init__(self, http_client: XuiHttpClient, username: str, password: str, host: str) -> None:
        self._http = http_client
        self._username = username
        self._password = password
        self._host = host

    async def _send(self, method: HttpMethod, url: str, **kwargs):
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
        response = await self._send(method, url, **kwargs)

        # Если сессия умерла - перелогин
        if response.status_code in (401, 403, 404):
            await self.login()
            response = await self._send(method, url, **kwargs)

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

    async def login(self) -> None:
        """Выполняет авторизацию в XUI."""
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
            raise XuiInvalidResponseError("Invalid JSON response") from exc

        if not data.get("success"):
            raise XuiAuthenticationError("Authentication failed")

    # INBOUNDS
    async def get_inbounds(self) -> list[Inbound]:
        """Возвращает список inbound'ов."""
        raw = await self._request(HttpMethod.GET, "panel/api/inbounds/list")

        if not isinstance(raw, list):
            raise XuiInvalidResponseError("Expected list of inbounds")

        return [Inbound.from_dict(i) for i in raw]

    async def get_inbound_by_id(self, inbound_id: int) -> Inbound:
        """Возвращает конкретный inbound по заданному id."""
        raw = await self._request(
            HttpMethod.GET,
            f"panel/api/inbounds/get/{inbound_id}",
        )

        return Inbound.from_dict(raw)

    async def get_inbound_by_name(self, inbound_name: str) -> Inbound:
        """Возвращает конкретный inbound по его имени."""
        inbounds = await self.get_inbounds()

        for inbound in inbounds:
            if inbound.remark == inbound_name:
                if inbound.id is None:
                    raise XuiInvalidResponseError(f"Inbound '{inbound_name}' has no id")
                return inbound

        raise XuiInvalidResponseError(f"Inbound '{inbound_name}' not found")

    # CLIENTS
    async def get_clients(self, inbound_name: str) -> list[Client]:
        """Получить всех клиентов в определённом inbond'е."""
        inbound = await self.get_inbound_by_name(inbound_name)

        return inbound.clients

    async def find_client(self, email: str, inbound_name: str) -> Client | None:
        """Ищет клиента по email в заданном inbound'е."""
        clients = await self.get_clients(inbound_name)
        for client in clients:
            if client.email == email:
                return client

        return None

    async def find_client_by_uuid(self, uuid: str, inbound_name: str) -> Client | None:
        """Ищет клиента по uuid в заданном inbound'е."""
        clients = await self.get_clients(inbound_name)
        for client in clients:
            if client.uuid == uuid:
                return client
        return None

    async def is_client_exists(self, email: str, inbound_name: str) -> bool:
        """Проверяет, существует ли клиент с данным email в указанном inbound'е."""
        return (await self.find_client(email, inbound_name)) is not None

    async def is_client_enabled(self, email: str, inbound_name: str) -> bool:
        """Возвращает True, если клиент включён в указанном inbound'е."""
        client = await self.find_client(email, inbound_name)
        if client is not None:
            return client.enabled

        return False

    async def get_client_expiry(self, email: str, inbound_name: str) -> int | None:
        """
        Возвращает expiryTime клиента (timestamp в мс) в указанном inbound'е.
        Возвращает None, если клиента нет или срок не задан.
        """
        client = await self.find_client(email, inbound_name)
        if client is not None:
            return client.expiry_time
        return None

    async def is_client_expired(self, email: str, inbound_name: str) -> bool:
        """True, если срок действия истёк."""
        client = await self.find_client(email, inbound_name)
        if client is not None:
            return client.is_expired()

        return False

    async def get_client_link(self, email: str, inbound_name: str) -> str:
        """Генерирует VLESS-ссылку для клиента."""
        client = await self.find_client(email, inbound_name)
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
        spx = reality_settings.get("spiderX")
        inbound_name = inbound.remark
        client_name = client.email

        return (
            f"vless://{uuid}@{self._host}:{port}?type={type_network}&encryption={encryption}&security={security}"
            f"&pbk={pbk}&fp={fp}&sni={sni}&sid={sid}&spx={spx}#{inbound_name}-{client_name}"
        )

    # CRUD
    def _build_client_payload(self, *, inbound_id: int, uuid: str, email: str,
                              enable: bool, expiry_time: int,) -> dict:
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
                    }
                ]
            }),
        }

    async def update_client(self, email: str, inbound_name: str, *, new_email: str = None,
                            enabled: bool = None, expiry_time: int = None) -> None:
        """Универсальный метод для обновления клиента."""
        client = await self.find_client(email, inbound_name)
        if client is None:
            raise XuiClientNotFoundError(f"Client {email} not found")

        payload = self._build_client_payload(
            inbound_id=client.inbound_id,
            uuid=client.uuid,
            email=client.email if new_email is None else new_email,
            enable=client.enabled if enabled is None else enabled,
            expiry_time=client.expiry_time if expiry_time is None else expiry_time,
        )

        await self._request(HttpMethod.POST, f"panel/api/inbounds/updateClient/{client.uuid}", json=payload)

    async def add_client(self, inbound_name: str, email: str, *, uuid: str | None = None,
                         expiry_time: int = 0, enable: bool = True) -> None:
        """
        Создаёт нового клиента в указанном inbound.
        :param inbound_name: название inbound'а
        :param email: email клиента (идентификатор)
        :param uuid: UUID клиента
        :param expiry_time: timestamp в мс или None (бессрочно)
        :param enable: включён ли клиент
        """
        inbound = await self.get_inbound_by_name(inbound_name)

        if uuid is None:
            uuid = str(uuid4())
        if await self.find_client_by_uuid(uuid, inbound_name):
            raise XuiClientAlreadyExistsError(f"Client with uuid {uuid} already exists")

        if await self.is_client_exists(email, inbound_name):
            raise XuiClientAlreadyExistsError(f"Client with email {email} already exists")

        payload = self._build_client_payload(
            inbound_id=inbound.id,
            uuid=uuid,
            email=email,
            enable=enable,
            expiry_time=expiry_time,
        )

        await self._request(HttpMethod.POST, f"panel/api/inbounds/addClient", json=payload)

    async def delete_client(self, email: str, inbound_name: str):
        """Удаление клиента."""
        client = await self.find_client(email, inbound_name)
        if client is None:
            raise XuiClientNotFoundError(f"Client {email} not found")

        await self._request(HttpMethod.POST, f"panel/api/inbounds/{client.inbound_id}/delClient/{client.uuid}")