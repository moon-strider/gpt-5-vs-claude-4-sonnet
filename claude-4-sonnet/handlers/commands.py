import logging
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from services.state_manager import state_manager

logger = logging.getLogger(__name__)

command_router = Router()


@command_router.message(Command("start"))
async def start_command(message: Message):
    user_id = message.from_user.id if message.from_user else "unknown"
    logger.info(f"User {user_id} executed /start command")
    
    welcome_text = """🤖 <b>Telegram Task Scheduler Bot</b>

Welcome! I help you schedule tasks by processing natural language input and returning the next occurrence dates.

<b>How it works:</b>
• Send me tasks in natural language (e.g., "Team meeting every Monday at 2pm")
• I'll classify them as [work] or [personal] 
• You'll get the next 3 occurrence dates for each task

<b>Supported task types:</b>
• One-time tasks: "Call dentist tomorrow at 10am"
• Recurring tasks: "Gym every Tuesday and Thursday"
• Various date formats: "next Monday", "January 15th", etc.

<b>Commands:</b>
/help - Show this help message
/clear - Clear current context and start fresh

<b>Time zone:</b> All times are in GMT+0

Just send me your tasks to get started! 📋"""

    await message.answer(welcome_text)


@command_router.message(Command("help"))
async def help_command(message: Message):
    user_id = message.from_user.id if message.from_user else "unknown"
    logger.info(f"User {user_id} executed /help command")
    
    help_text = """📖 <b>Help & Usage Guide</b>

<b>Available Commands:</b>
/start - Show welcome message and bot introduction
/help - Display this help guide  
/clear - Clear current context and start fresh

<b>How to Schedule Tasks:</b>
1. Send me tasks in natural language
2. I'll parse and classify them as [work] or [personal]
3. Review the parsed tasks and approve or reject
4. Get the next 3 occurrence dates for each approved task

<b>Examples:</b>
• "Team standup every Monday at 9am"
• "Dentist appointment tomorrow at 2:30pm"  
• "Weekly groceries every Saturday morning"
• "Project deadline January 30th"

<b>Supported Features:</b>
• Relative dates: "tomorrow", "next Monday", "in 2 weeks"
• Absolute dates: "January 15th", "March 3, 2025"
• Recurring patterns: "daily", "weekly", "monthly", "every 2 weeks"
• Time specifications: "9am", "14:30", "morning", "afternoon"

<b>Important Notes:</b>
• All times are displayed in GMT+0 timezone
• Maximum 3 future occurrences per task
• Context is cleared after each completed session
• Use /clear if you want to abandon current tasks

Need more help? Just ask! 🤝"""

    await message.answer(help_text)


@command_router.message(Command("clear"))
async def clear_command(message: Message):
    user_id = message.from_user.id if message.from_user else None
    if not user_id:
        await message.answer("❌ Error: Unable to identify user")
        return
        
    logger.info(f"User {user_id} executed /clear command")
    
    was_flushed = state_manager.flush_state(user_id)
    
    if was_flushed:
        clear_text = """🧹 <b>Context Cleared</b>

Your current context has been cleared. You can now:

• Send new tasks to schedule
• Start a fresh conversation
• Use any of the available commands

Ready to help you with new tasks! 📋"""
    else:
        clear_text = """🧹 <b>No Active Context</b>

You don't have any active context to clear.

• Send tasks to schedule
• Use any of the available commands

Ready to help you! 📋"""

    await message.answer(clear_text)