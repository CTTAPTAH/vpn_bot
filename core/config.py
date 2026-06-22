"""
Конфигурация проекта.

Здесь хранятся:
- параметры Telegram-бота
- данные для подключения к XUI API
- ссылки и хосты, используемые для генерации VPN-ссылок

Файл содержит только настройки и не должен включать бизнес-логику.
"""
import os
from dotenv import load_dotenv
load_dotenv()

def _require(value: str, name: str) -> str:
    """Функция для debug. Если не существует указанной переменной в окружении, то выпадает исключение."""
    if not value:
        raise RuntimeError(f"Переменная окружения {name} не задана")
    return value

# Бот
BOT_TOKEN = _require(os.getenv("BOT_TOKEN"), "BOT_TOKEN")
MAX_DEVICE_PER_KEY = 3 # Лимит по количеству одновременно подключённых устройств у ключа
PAYMENT_EXPIRY_THRESHOLD_MINUTES = 5 # Время, через которое платёж не восстанавливается, а отменяется
# при попытке его возобновить

# Бот поддержки
SUPPORT_BOT_TOKEN = _require(os.getenv("SUPPORT_BOT_TOKEN"), "SUPPORT_BOT_TOKEN")
SUPPORT_GROUP_ID: int = int(os.getenv("SUPPORT_GROUP_ID")) # id группы админов
TICKET_TITLE_LENGTH = 40 # Сколько символов берём в title
TICKET_DISPLAY_LIMIT = 7 # Количество последних обращений, которые показываем пользователю
MESSAGE_DISPLAY_LIMIT = 20 # Количество последних сообщений в обращении, которые показываем пользователю

# Касса
PLATEGA_MERCHANT_ID = _require(os.getenv("PLATEGA_MERCHANT_ID"), "PLATEGA_MERCHANT_ID")
PLATEGA_API_KEY = _require(os.getenv("PLATEGA_API_KEY"), "PLATEGA_API_KEY")
CURRENCY = "RUB" # Валюта
PLATEGA_BASE_URL = "https://app.platega.io"

# Подписка
SUB_HOST = _require(os.getenv("SUB_HOST"), "SUB_HOST")
SUB_PROTOCOL = _require(os.getenv("SUB_PROTOCOL"), "SUB_PROTOCOL")

# Retry XUI
XUI_RETRY_ATTEMPTS = 3 # Количество попыток retry
XUI_RETRY_BASE_DELAY = 1 # Первоначальная задержка для повторного запроса
XUI_RETRY_MULTIPLIER = 2 # Множитель задержки между запросами

# Retry Platega
PLATEGA_RETRY_ATTEMPTS = 2 # Количество попыток retry
PLATEGA_RETRY_BASE_DELAY = 0.5 # Первоначальная задержка для повторного запроса
PLATEGA_RETRY_MULTIPLIER = 2 # Множитель задержки между запросами

# HTTP client
HTTP_TIMEOUT = 10.0

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