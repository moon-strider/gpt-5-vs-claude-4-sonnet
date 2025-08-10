import asyncio
from aiogram import Bot, Dispatcher
from .settings import load_settings
from .logging import configure_logging
from .telegram.app import create_router


async def main() -> None:
    settings = load_settings()
    logger = configure_logging(settings.LOG_LEVEL)
    logger.info(f"APP_TZ={settings.APP_TZ}")
    bot = Bot(settings.TELEGRAM_BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(create_router(settings))

    logger.info("ready")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
