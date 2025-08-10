import logging
from enum import Enum
from typing import Optional
from aiogram.types import Message

logger = logging.getLogger(__name__)


class ErrorType(Enum):
    INVALID_DATE = "invalid_date"
    INVALID_TIME = "invalid_time" 
    UNRELATED_INPUT = "unrelated_input"
    CONTEXT_CONFLICT = "context_conflict"
    MESSAGE_TOO_LONG = "message_too_long"
    EMPTY_MESSAGE = "empty_message"
    UNSUPPORTED_CONTENT = "unsupported_content"
    PROCESSING_ERROR = "processing_error"


async def handle_message_error(message: Message, error_type: ErrorType, context: Optional[str] = None):
    """Handle different types of message errors with appropriate responses"""
    user_id = message.from_user.id if message.from_user else "unknown"
    logger.warning(f"Error for user {user_id}: {error_type.value} - {context}")
    
    error_responses = {
        ErrorType.INVALID_DATE: _get_invalid_date_message(context),
        ErrorType.INVALID_TIME: _get_invalid_time_message(context),
        ErrorType.UNRELATED_INPUT: _get_unrelated_input_message(),
        ErrorType.CONTEXT_CONFLICT: _get_context_conflict_message(),
        ErrorType.MESSAGE_TOO_LONG: _get_message_too_long_message(),
        ErrorType.EMPTY_MESSAGE: _get_empty_message_message(),
        ErrorType.UNSUPPORTED_CONTENT: _get_unsupported_content_message(),
        ErrorType.PROCESSING_ERROR: _get_processing_error_message()
    }
    
    response = error_responses.get(error_type, _get_generic_error_message())
    
    try:
        await message.answer(response)
    except Exception as e:
        logger.error(f"Failed to send error message to user {user_id}: {e}")


def _get_invalid_date_message(date_context: Optional[str] = None) -> str:
    if date_context:
        return f"Invalid date detected: {date_context}. Please use a valid date format."
    return "Invalid date detected. Please use a valid date format."


def _get_invalid_time_message(time_context: Optional[str] = None) -> str:
    if time_context:
        return f"Invalid time detected: {time_context}. Please use 24-hour format (HH:MM)."
    return "Invalid time detected. Please use 24-hour format (HH:MM)."


def _get_unrelated_input_message() -> str:
    return "I can only process task scheduling requests. Please send tasks you'd like me to schedule."


def _get_context_conflict_message() -> str:
    return "Please complete current clarifications or use /clear to start fresh."


def _get_message_too_long_message() -> str:
    return """❌ <b>Message Too Long</b>

Your message exceeds the 4096 character limit. Please break your tasks into smaller batches or shorten your message."""


def _get_empty_message_message() -> str:
    return """❌ <b>Empty Message</b>

Please send me some tasks to schedule. 

<b>Example:</b> "Team standup tomorrow at 9am"

Use /help for more information."""


def _get_unsupported_content_message() -> str:
    return """❌ <b>Unsupported Content</b>

I can only process text messages with tasks to schedule. 

Please send your tasks as text messages.

<b>Example:</b> "Weekly team meeting every Friday at 3pm"

Use /help for more information."""


def _get_processing_error_message() -> str:
    return """❌ <b>Processing Error</b>

An error occurred while processing your request. Please try again.

If the problem persists, use /clear to reset and try with a different message format."""


def _get_generic_error_message() -> str:
    return """❌ <b>Error</b>

An unexpected error occurred. Please try again or use /clear to reset.

Use /help if you need assistance with message formatting."""