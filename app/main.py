"""
Точка входа в приложение.

Запускает Telegram-бота в режиме polling
и управляет жизненным циклом приложения.
"""
import asyncio
import logging
from dotenv import load_dotenv

load_dotenv()

from presentation.telegram.bot import bot, dp
from presentation.telegram.handlers.handlers import register_handlers
from app.container import init_vpn_gateway, close_vpn_gateway

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

async def main():
    # Начало работы VPN gateway один раз на всю программу
    await init_vpn_gateway()

    # Регистрация обработчиков
    router = register_handlers()
    dp.include_router(router)

    try:
        await dp.start_polling(bot)
    finally:
        logger.info("Закрытие ресурсов бота...")
        await bot.session.close()
        await close_vpn_gateway()
        logger.info("Бот остановлен.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен")