import json
from unittest.mock import MagicMock, AsyncMock
from infrastructure.xui.api_client import XuiApiClient

def make_response(status_code=200, json_data=None, raise_json=False):
    mock = MagicMock()
    mock.status_code = status_code
    if raise_json:
        mock.json.side_effect = Exception("Invalid JSON")
    else:
        mock.json.return_value = json_data or {}
    return mock

def make_inbound_response(email="test", enabled=True, expiry_time=0):
    client_data = {
        "id": "some-uuid",
        "email": email,
        "enable": enabled,
        "expiryTime": expiry_time,
    }
    settings = json.dumps({"clients": [client_data]})
    return {
        "success": True,
        "obj": {
            "id": 1,
            "remark": "test-inbound",
            "port": 443,
            "protocol": "vless",
            "enable": True,
            "settings": settings,
            "streamSettings": json.dumps({}),
        }
    }

def make_client(http_mock: AsyncMock) -> XuiApiClient:
    return XuiApiClient(
        http_client=http_mock,
        username="admin",
        password="password",
        host="1.2.3.4",
    )