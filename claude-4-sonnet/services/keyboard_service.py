import logging
from typing import List, Dict, Any
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import json

logger = logging.getLogger(__name__)


class KeyboardService:
    def __init__(self):
        self._max_callback_data_length = 64
    
    def create_approval_keyboard(self, user_id: int) -> InlineKeyboardMarkup:
        approve_data = self._create_callback_data("approve", user_id)
        reject_data = self._create_callback_data("reject", user_id)
        
        if len(approve_data.encode('utf-8')) > self._max_callback_data_length:
            logger.error(f"Approve callback data too long: {len(approve_data.encode('utf-8'))} bytes")
            approve_data = f"app_{user_id}"[:self._max_callback_data_length-5]
        
        if len(reject_data.encode('utf-8')) > self._max_callback_data_length:
            logger.error(f"Reject callback data too long: {len(reject_data.encode('utf-8'))} bytes")
            reject_data = f"rej_{user_id}"[:self._max_callback_data_length-5]
        
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="Approve ✅", callback_data=approve_data),
                    InlineKeyboardButton(text="Reject ❌", callback_data=reject_data)
                ]
            ]
        )
        
        logger.info(f"Created approval keyboard for user {user_id}")
        return keyboard
    
    def _create_callback_data(self, action: str, user_id: int) -> str:
        data = f"{action}_{user_id}"
        
        if len(data.encode('utf-8')) <= self._max_callback_data_length:
            return data
        
        short_action = action[:3]
        return f"{short_action}_{user_id}"
    
    def parse_callback_data(self, callback_data: str) -> Dict[str, Any]:
        try:
            parts = callback_data.split('_')
            
            if len(parts) < 2:
                return {"valid": False, "error": "Invalid callback format"}
            
            action_part = parts[0]
            user_id_part = parts[1]
            
            action_mapping = {
                "approve": "approve",
                "reject": "reject",
                "app": "approve",
                "rej": "reject"
            }
            
            action = action_mapping.get(action_part)
            if not action:
                return {"valid": False, "error": f"Unknown action: {action_part}"}
            
            try:
                user_id = int(user_id_part)
            except ValueError:
                return {"valid": False, "error": "Invalid user ID"}
            
            return {
                "valid": True,
                "action": action,
                "user_id": user_id
            }
            
        except Exception as e:
            logger.error(f"Error parsing callback data '{callback_data}': {e}")
            return {"valid": False, "error": "Callback parsing error"}
    
    def format_parsed_tasks_display(self, tasks: List[Dict[str, Any]]) -> str:
        if not tasks:
            return "❌ No tasks found to display."
        
        header = "📋 <b>Parsed Tasks:</b>\n\n"
        
        task_lines = []
        for i, task in enumerate(tasks, 1):
            classification = task.get("classification", "unknown")
            description = task.get("description", "No description")
            time_str = task.get("time", "not specified")
            date_str = task.get("date", "not specified")
            recurrence = task.get("recurrence", "none")
            
            task_line = f"{i}. [{classification}] {description}"
            
            if time_str and time_str != "not specified":
                task_line += f"\n   - Time: {time_str} GMT"
            
            if date_str and date_str != "not specified":
                task_line += f"\n   - Date: {date_str}"
                
            if recurrence and recurrence != "none":
                recurrence_display = recurrence.title() if recurrence != "none" else "One-time"
                task_line += f"\n   - Recurrence: {recurrence_display}"
            
            task_lines.append(task_line)
        
        footer = "\n\nPlease review the tasks above and choose an action:"
        
        full_message = header + "\n\n".join(task_lines) + footer
        
        if len(full_message) > 4000:
            logger.warning(f"Parsed tasks display is {len(full_message)} chars, truncating")
            truncated_lines = []
            for line in task_lines:
                if len(line) > 200:
                    parts = line.split('\n')
                    description_part = parts[0]
                    if len(description_part) > 150:
                        truncated_desc = description_part[:147] + "..."
                        parts[0] = truncated_desc
                    line = '\n'.join(parts)
                truncated_lines.append(line)
            
            full_message = header + "\n\n".join(truncated_lines) + footer
        
        return full_message
    
    def validate_keyboard_limits(self, keyboard: InlineKeyboardMarkup) -> bool:
        for row in keyboard.inline_keyboard:
            if len(row) > 8:
                logger.error("Too many buttons in keyboard row")
                return False
            
            for button in row:
                if len(button.callback_data.encode('utf-8')) > self._max_callback_data_length:
                    logger.error(f"Button callback data too long: {len(button.callback_data.encode('utf-8'))} bytes")
                    return False
        
        return True


keyboard_service = KeyboardService()