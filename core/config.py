"""
Конфигурация проекта.

Здесь хранятся:
- параметры Telegram-бота
- данные для подключения к XUI API
- ссылки и хосты, используемые для генерации VPN-ссылок

Файл содержит только настройки и не должен включать бизнес-логику.
"""
from dotenv import load_dotenv
import os

load_dotenv()

def _require(value: str, name: str) -> str:
    """Функция для debug. Если не существует указанной переменной в окружении, то выпадает исключение."""
    if not value:
        raise RuntimeError(f"Переменная окружения {name} не задана")
    return value

# Бот
BOT_TOKEN = _require(os.getenv("BOT_TOKEN"), "BOT_TOKEN")
MAX_KEYS_PER_USER = 5
MAX_DEVICE_PER_KEY = 3

# XUI
XUI_BASE_URL = _require(os.getenv("XUI_BASE_URL"), "XUI_BASE_URL")
XUI_USERNAME = _require(os.getenv("XUI_USERNAME"), "XUI_USERNAME")
XUI_PASSWORD = _require(os.getenv("XUI_PASSWORD"), "XUI_PASSWORD")
VPN_HOST = _require(os.getenv("VPN_HOST"), "VPN_HOST")
INBOUND_NAME = _require(os.getenv("INBOUND_NAME"), "INBOUND_NAME")

# Retry XUI
XUI_RETRY_ATTEMPTS = 3
XUI_RETRY_BASE_DELAY = 1
XUI_RETRY_MULTIPLIER = 2

# HTTP client
TIMEOUT = 10.0

# База данных
DB_HOST = _require(os.getenv("DB_HOST"), "DB_HOST")
DB_PORT = _require(os.getenv("DB_PORT"), "DB_PORT")
DB_NAME = _require(os.getenv("DB_NAME"), "DB_NAME")
DB_USER = _require(os.getenv("DB_USER"), "DB_USER")
DB_PASSWORD = _require(os.getenv("DB_PASSWORD"), "DB_PASSWORD")

DATABASE_URL = (
    f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)