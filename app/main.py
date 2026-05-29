"""
Точка входа в приложение.

Запускает Telegram-бота в режиме polling
и управляет жизненным циклом приложения.
"""
import asyncio
import logging
import uvicorn

from app.container import get_vpn_gateway_factory, get_platega_client, close_platega_client
from presentation.telegram.bot import bot, dp
from presentation.telegram.handlers.handlers import register_handlers
from presentation.support.bot import bot as support_bot, dp as support_dp
from presentation.support.handlers import register_handlers as support_register_handlers
from presentation.api.main import app as fastapi_app

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

async def main():
    # Регистрация обработчиков основного бота
    router = register_handlers()
    dp.include_router(router)

    # Регистрация обработчиков бота поддержки
    support_router = support_register_handlers()
    support_dp.include_router(support_router)

    # FastAPI сервер
    config = uvicorn.Config(fastapi_app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)

    try:
        await asyncio.gather(
            dp.start_polling(bot, handle_signals=False),
            support_dp.start_polling(support_bot, handle_signals=False),
            server.serve()
        )
    finally:
        logger.info("Закрытие ресурсов бота...")

        await bot.session.close()
        await support_bot.session.close()
        await get_vpn_gateway_factory().close()
        await close_platega_client()

        logger.info("Бот остановлен.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен")