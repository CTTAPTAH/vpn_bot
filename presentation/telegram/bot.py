"""
Инициализация Telegram-бота и диспетчера.

Создаёт экземпляры Bot, Dispatcher и сервисные клиенты,
которые используются во всём приложении.
"""
from aiogram import Bot, Dispatcher
from aiogram.client.bot import DefaultBotProperties
from core.config import BOT_TOKEN

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()