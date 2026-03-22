"""
Модели данных для взаимодействия с XUI API.

Содержит структуры, представляющие сущности сервера (например, VPN-клиентов),
а также связанную с ними логику.
"""
import json
import time
from dataclasses import dataclass, field
from typing import List
from infrastructure.xui.exceptions import XuiInvalidResponseError

@dataclass
class Client:
    """Модель для хранения информации о клиенте."""
    id: int | None # внутренний ID XUI
    uuid: str # VLESS UUID
    email: str
    inbound_id: int
    enabled: bool
    expiry_time: int | None = None # ms

    @classmethod
    def from_dict(cls, data: dict, inbound_id: int):
        if not isinstance(data, dict):
            raise XuiInvalidResponseError("Expected dict")

        return cls(
            id=data.get("id"),
            uuid=data.get("uuid"),
            email=data.get("email"),
            inbound_id=inbound_id,
            enabled=bool(data.get("enable", True)),
            expiry_time=data.get("expiryTime", 0),
        )

    def is_expired(self) -> bool:
        if self.expiry_time is None or self.expiry_time == 0:
            return False
        return int(time.time() * 1000) >= self.expiry_time

@dataclass
class Inbound:
    id: int
    remark: str
    port: int
    protocol: str
    enabled: bool
    stream_settings_raw: str
    clients: List[Client] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict):
        if not isinstance(data, dict):
            raise XuiInvalidResponseError("Expected dict")

        inbound_id = data["id"]

        clients_data = data.get("clientStats") or []

        clients = [
            Client.from_dict(c, inbound_id)
            for c in clients_data
        ]

        return cls(
            id=inbound_id,
            remark=data.get("remark", ""),
            port=int(data.get("port")),
            protocol=data.get("protocol"),
            enabled=data.get("enable", True),
            stream_settings_raw=data.get("streamSettings", ""),
            clients=clients,
        )

    def get_stream_settings(self) -> dict:
        if not self.stream_settings_raw:
            return {}
        try:
            return json.loads(self.stream_settings_raw)
        except Exception as e:
            raise XuiInvalidResponseError("Invalid streamSettings JSON") from e