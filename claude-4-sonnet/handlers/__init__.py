from aiogram import Dispatcher
from handlers.commands import command_router
from handlers.messages import message_router


def register_handlers(dp: Dispatcher):
    """Register all handlers with the dispatcher"""
    dp.include_router(command_router)
    dp.include_router(message_router)