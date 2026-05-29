import os
import pytest
from unittest.mock import AsyncMock
from infrastructure.http.http_client import HttpClient

# Должно быть ДО любых импортов проекта
os.environ.setdefault("BOT_TOKEN", "123456789:AABBccDDeeFFggHHiiJJkkLLmmNNooPPqq")
os.environ.setdefault("PLATEGA_MERCHANT_ID", "test_merchant")
os.environ.setdefault("PLATEGA_API_KEY", "test_api_key")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_NAME", "testdb")
os.environ.setdefault("DB_USER", "testuser")
os.environ.setdefault("DB_PASSWORD", "testpassword")

@pytest.fixture
def http_client_mock():
    return AsyncMock(spec=HttpClient)