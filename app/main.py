"""
Точка входа в приложение.

Запускает Telegram-бота в режиме polling
и управляет жизненным циклом приложения.
"""
import asyncio

from presentation.telegram.bot import bot, dp
from presentation.telegram.handlers.handlers import register_handlers
from app.container import init_vpn_gateway, close_vpn_gateway

async def main():
    # Начало работы VPN gateway один раз на всю программу
    await init_vpn_gateway()

    # Регистрация обработчиков
    router = register_handlers()
    dp.include_router(router)

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        await close_vpn_gateway()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен")