import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.bot import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from dotenv import load_dotenv

from app.bot import bot_router
from app.config import load_settings

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)


def create_bot(settings) -> Bot:
    session_kwargs: dict = {}
    if settings.worker_url:
        api_server = TelegramAPIServer.from_base(settings.worker_url)
        session_kwargs["api"] = api_server
        logger.info("Бот через прокси: %s", settings.worker_url)

    session = AiohttpSession(**session_kwargs)
    return Bot(
        token=settings.bot_token,
        session=session,
        default=DefaultBotProperties(),
    )


async def main() -> None:
    load_dotenv()
    settings = load_settings()
    bot = create_bot(settings)
    dp = Dispatcher()
    dp.include_router(bot_router)

    logger.info("Jobber запущен")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
