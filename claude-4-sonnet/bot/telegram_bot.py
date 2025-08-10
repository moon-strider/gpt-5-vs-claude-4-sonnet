import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramRetryAfter, TelegramServerError
from aiogram.fsm.storage.memory import MemoryStorage

from config.settings import Settings


class TelegramBot:
    def __init__(self, settings: Settings, logger: logging.Logger):
        self.settings = settings
        self.logger = logger
        self.bot = Bot(
            token=settings.telegram_bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        self.dp = Dispatcher(storage=MemoryStorage())
        self._setup_middleware()

    def _setup_middleware(self):
        @self.dp.message.middleware()
        async def logging_middleware(handler, event, data):
            user_id = event.from_user.id if event.from_user else "unknown"
            username = event.from_user.username if event.from_user else "unknown"
            self.logger.info(f"Message from user {user_id} ({username}): {event.text}")
            return await handler(event, data)

        @self.dp.callback_query.middleware()
        async def callback_logging_middleware(handler, event, data):
            user_id = event.from_user.id if event.from_user else "unknown"
            username = event.from_user.username if event.from_user else "unknown"
            self.logger.info(f"Callback from user {user_id} ({username}): {event.data}")
            return await handler(event, data)

    async def start_polling(self):
        self.logger.info("Starting bot polling...")
        try:
            await self.dp.start_polling(
                self.bot,
                skip_updates=True,
                allowed_updates=["message", "callback_query"]
            )
        except TelegramRetryAfter as e:
            self.logger.warning(f"Rate limited. Waiting {e.retry_after} seconds")
            await asyncio.sleep(e.retry_after)
            await self.start_polling()
        except TelegramServerError as e:
            self.logger.error(f"Telegram server error: {e}")
            await asyncio.sleep(5)
            await self.start_polling()
        except Exception as e:
            self.logger.error(f"Unexpected error in polling: {e}")
            raise

    async def stop(self):
        self.logger.info("Stopping bot...")
        await self.bot.session.close()

    def register_handlers(self, handlers_module):
        handlers_module.register_handlers(self.dp)