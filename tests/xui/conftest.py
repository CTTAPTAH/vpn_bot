import pytest
from unittest.mock import AsyncMock
from tests.xui.factories import make_client

@pytest.fixture
def http_mock():
    return AsyncMock()


@pytest.fixture
def xui(http_mock):
    return make_client(http_mock)