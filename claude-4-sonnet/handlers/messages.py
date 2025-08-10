import logging
from aiogram import Router
from aiogram.types import Message, CallbackQuery
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from utils.error_handler import handle_message_error, ErrorType
from services.state_manager import state_manager, ConversationState
from services.task_parser import task_parser
from services.clarification_service import clarification_service
from services.keyboard_service import keyboard_service
from services.datetime_processor import datetime_processor
from services.task_validator import task_validator

logger = logging.getLogger(__name__)

message_router = Router()


@message_router.message(StateFilter(None))
async def handle_text_message(message: Message, state: FSMContext):
    """Handle incoming text messages for task processing"""
    user_id = message.from_user.id if message.from_user else None
    if not user_id:
        await handle_message_error(message, ErrorType.PROCESSING_ERROR)
        return
        
    logger.info(f"Processing text message from user {user_id}")
    
    try:
        if state_manager.is_in_clarification(user_id):
            await _handle_clarification_response(message, user_id)
            return
        
        if not state_manager.can_accept_new_tasks(user_id):
            await handle_message_error(message, ErrorType.CONTEXT_CONFLICT)
            return
        
        input_validation_error = task_validator.validate_input_message(message.text)
        if input_validation_error:
            await message.answer(f"❌ {input_validation_error}")
            return
            
        text_content = task_validator.sanitize_input(message.text)
        
        if _is_unrelated_input(text_content):
            await handle_message_error(message, ErrorType.UNRELATED_INPUT)
            return
            
        logger.info(f"Valid task input received from user {user_id}: {text_content[:100]}...")
        
        user_state = state_manager.get_state(user_id)
        if not user_state:
            user_state = state_manager.create_state(user_id)
        
        state_manager.update_state(
            user_id, 
            state=ConversationState.PROCESSING,
            original_message=text_content
        )
        
        parsing_result = await task_parser.parse_tasks(text_content)
        
        if parsing_result.get("error"):
            await message.answer(f"❌ {parsing_result['error']}")
            state_manager.flush_state(user_id)
            return
        
        parsed_tasks = parsing_result.get("tasks", [])
        needs_clarification = parsing_result.get("needs_clarification", False)
        
        if not parsed_tasks:
            await message.answer("❌ I couldn't identify any tasks in your message. Please try again with clear task descriptions.")
            state_manager.flush_state(user_id)
            return
        
        validation_result = task_validator.validate_parsed_tasks(parsed_tasks)
        if not validation_result["valid"]:
            error_message = "❌ Task validation failed:\n• " + "\n• ".join(validation_result["errors"])
            await message.answer(error_message)
            state_manager.flush_state(user_id)
            return
        
        validated_tasks = validation_result["validated_tasks"]
        
        state_manager.update_state(user_id, parsed_tasks=validated_tasks)
        
        if needs_clarification:
            needs_clarification, clarifications = clarification_service.extract_clarifications(validated_tasks)
            
            if needs_clarification and clarifications:
                state_manager.update_state(
                    user_id, 
                    state=ConversationState.CLARIFICATION,
                    clarifications_needed=clarifications
                )
                
                clarification_message = clarification_service.format_clarification_message(clarifications)
                await message.answer(clarification_message)
                return
        

        await _show_tasks_for_approval(message, user_id, validated_tasks)
        
    except Exception as e:
        logger.error(f"Error processing message from user {user_id}: {e}")
        state_manager.flush_state(user_id)
        await handle_message_error(message, ErrorType.PROCESSING_ERROR)


@message_router.callback_query()
async def handle_callback_query(callback: CallbackQuery, state: FSMContext):
    """Handle inline keyboard callbacks"""
    user_id = callback.from_user.id if callback.from_user else None
    if not user_id:
        await callback.answer("Error: Unable to identify user", show_alert=True)
        return
        
    logger.info(f"Processing callback from user {user_id}: {callback.data}")
    
    try:
        if len(callback.data.encode('utf-8')) > 64:
            logger.error(f"Callback data exceeds 64 bytes: {callback.data}")
            await callback.answer("Error: Invalid callback data", show_alert=True)
            return
        
        parsed_callback = keyboard_service.parse_callback_data(callback.data)
        if not parsed_callback.get("valid"):
            await callback.answer(f"Error: {parsed_callback.get('error', 'Invalid callback')}", show_alert=True)
            return
        
        action = parsed_callback["action"]
        callback_user_id = parsed_callback["user_id"]
        
        if callback_user_id != user_id:
            await callback.answer("Error: Invalid user for this action", show_alert=True)
            return
        
        if not state_manager.is_awaiting_approval(user_id):
            await callback.answer("No active task approval found", show_alert=True)
            return
        
        user_state = state_manager.get_state(user_id)
        if not user_state or not user_state.parsed_tasks:
            await callback.answer("No tasks found for approval", show_alert=True)
            return
        
        await callback.answer()
        
        if action == "approve":
            await _handle_task_approval(callback, user_id, user_state.parsed_tasks)
        elif action == "reject":
            await _handle_task_rejection(callback, user_id)
        else:
            await callback.message.answer("❌ Unknown action received")
            
    except Exception as e:
        logger.error(f"Error processing callback from user {user_id}: {e}")
        await callback.answer("An error occurred processing your request", show_alert=True)


@message_router.message()
async def handle_unsupported_content(message: Message):
    """Handle unsupported message types"""
    user_id = message.from_user.id if message.from_user else "unknown"
    logger.info(f"Unsupported content from user {user_id}: {message.content_type}")
    
    await handle_message_error(message, ErrorType.UNSUPPORTED_CONTENT)


async def _handle_clarification_response(message: Message, user_id: int):
    """Handle user responses to clarification questions"""
    user_state = state_manager.get_state(user_id)
    if not user_state or not user_state.clarifications_needed:
        await message.answer("❌ No active clarifications found. Use /clear to start over.")
        state_manager.flush_state(user_id)
        return
    
    if not task_validator.validate_clarification_response(message.text):
        await message.answer("❌ Please provide a valid response to the clarification question.")
        return
    
    result = await clarification_service.process_clarification_response(
        message.text,
        user_state.clarifications_needed,
        user_state.parsed_tasks
    )
    
    if not result["success"]:
        await message.answer(f"❌ {result['error']}")
        return
    
    updated_tasks = result["updated_tasks"]
    still_needs_clarification = result.get("still_needs_clarification", False)
    remaining_clarifications = result.get("remaining_clarifications", [])
    
    state_manager.update_state(user_id, parsed_tasks=updated_tasks)
    
    if still_needs_clarification and remaining_clarifications:
        state_manager.update_state(user_id, clarifications_needed=remaining_clarifications)
        clarification_message = clarification_service.format_clarification_message(remaining_clarifications)
        await message.answer(clarification_message)
        return
    
    await _show_tasks_for_approval(message, user_id, updated_tasks)


async def _show_tasks_for_approval(message: Message, user_id: int, tasks: list):
    state_manager.update_state(user_id, state=ConversationState.DISPLAY)
    
    display_text = keyboard_service.format_parsed_tasks_display(tasks)
    
    keyboard = keyboard_service.create_approval_keyboard(user_id)
    
    if not keyboard_service.validate_keyboard_limits(keyboard):
        await message.answer("❌ Error creating approval buttons. Please try again.")
        state_manager.flush_state(user_id)
        return
    
    sent_message = await message.answer(display_text, reply_markup=keyboard)
    
    state_manager.update_state(user_id, message_id_for_approval=sent_message.message_id)


async def _handle_task_approval(callback: CallbackQuery, user_id: int, tasks: list):
    try:
        final_output = await _generate_final_output(tasks)
        
        await callback.message.answer(final_output)
        
        state_manager.flush_state(user_id)
        logger.info(f"Task approval completed for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error handling task approval for user {user_id}: {e}")
        await callback.message.answer("❌ Error processing your approved tasks. Please try again.")
        state_manager.flush_state(user_id)


async def _handle_task_rejection(callback: CallbackQuery, user_id: int):
    await callback.message.answer(
        "❌ <b>Tasks Rejected</b>\n\n"
        "Your tasks have been rejected. Please send new tasks if needed."
    )
    
    state_manager.flush_state(user_id)
    logger.info(f"Task rejection completed for user {user_id}")


async def _generate_final_output(tasks: list) -> str:
    if not tasks:
        return "❌ No tasks to process."
    
    header = "📅 <b>Next Occurrences:</b>\n\n"
    
    task_outputs = []
    for i, task in enumerate(tasks, 1):
        classification = task.get("classification", "unknown")
        description = task.get("description", "No description")
        
        try:
            occurrences = await datetime_processor.get_next_occurrences(task, limit=3)
            
            task_output = f"{i}. [{classification}] {description}"
            
            if occurrences:
                for occurrence in occurrences:
                    task_output += f"\n   - Next: {occurrence}"
            else:
                task_output += "\n   - No future occurrences calculated"
            
            task_outputs.append(task_output)
            
        except Exception as e:
            logger.error(f"Error generating occurrences for task {i}: {e}")
            task_output = f"{i}. [{classification}] {description}"
            task_output += "\n   - Error calculating occurrences"
            task_outputs.append(task_output)
    
    final_message = header + "\n\n".join(task_outputs)
    
    if len(final_message) > 4000:
        logger.warning(f"Final output is {len(final_message)} chars, truncating")
        truncated_outputs = []
        for output in task_outputs:
            lines = output.split('\n')
            if len(lines[0]) > 100:
                description_line = lines[0]
                if len(description_line) > 97:
                    lines[0] = description_line[:94] + "..."
            truncated_outputs.append('\n'.join(lines))
        
        final_message = header + "\n\n".join(truncated_outputs)
    
    return final_message


def _is_unrelated_input(text: str) -> bool:
    text_lower = text.lower().strip()
    
    unrelated_patterns = [
        "hello", "hi", "hey", "good morning", "good evening",
        "how are you", "what's up", "sup", "yo",
        "test", "testing", ".", "?", "!"
    ]
    
    if text_lower in unrelated_patterns:
        return True
        
    if len(text_lower) <= 2 and not text_lower.isalpha():
        return True
        
    return False