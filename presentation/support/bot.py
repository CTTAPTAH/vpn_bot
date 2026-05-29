from aiogram import Bot, Dispatcher
from aiogram.client.bot import DefaultBotProperties
from core.config import SUPPORT_BOT_TOKEN

bot = Bot(token=SUPPORT_BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()