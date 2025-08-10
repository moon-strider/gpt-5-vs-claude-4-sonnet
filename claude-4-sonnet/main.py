import asyncio
import sys
import signal
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from config.settings import get_settings
from utils.logger import setup_logger
from bot.telegram_bot import TelegramBot
import handlers


async def main():
    bot_instance = None
    try:
        settings = get_settings()
        logger = setup_logger("telegram_bot", settings.log_level, "bot.log")
        
        logger.info("Starting Telegram Task Scheduler Bot")
        logger.info("Environment validation successful")
        
        bot_instance = TelegramBot(settings, logger)
        bot_instance.register_handlers(handlers)
        
        logger.info("Bot initialized - Stage 2 complete")
        logger.info("All handlers registered successfully")
        
        def signal_handler():
            logger.info("Shutdown signal received")
            if bot_instance:
                asyncio.create_task(bot_instance.stop())

        if sys.platform != "win32":
            for sig in (signal.SIGTERM, signal.SIGINT):
                asyncio.get_event_loop().add_signal_handler(
                    sig, signal_handler
                )
        
        await bot_instance.start_polling()
        
    except ValueError as e:
        print(f"Configuration error: {e}")
        print("Please check your .env file and ensure all required variables are set")
        sys.exit(1)
    except Exception as e:
        print(f"Startup error: {e}")
        if bot_instance:
            await bot_instance.stop()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())