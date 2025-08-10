import logging
from typing import Dict, Any, Optional, List
from services.datetime_processor import datetime_processor

logger = logging.getLogger(__name__)


class TaskValidator:
    def __init__(self):
        self.datetime_processor = datetime_processor
        self.error_messages = {
            "invalid_date": "Invalid date detected: {}. Please use a valid date format.",
            "invalid_time": "Invalid time detected: {}. Please use 24-hour format (HH:MM).",
            "unrelated_input": "I can only process task scheduling requests. Please send tasks you'd like me to schedule.",
            "context_conflict": "Please complete current clarifications or use /clear to start fresh.",
            "message_too_long": "Message too long. Please keep task descriptions under 4000 characters.",
            "empty_input": "Please provide task details."
        }
    
    def validate_input_message(self, user_input: str) -> Optional[str]:
        if not user_input or not user_input.strip():
            return self.error_messages["empty_input"]
        
        if len(user_input) > 4000:
            return self.error_messages["message_too_long"]
        
        return None
    
    def validate_parsed_tasks(self, tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        validation_result = {
            "valid": True,
            "errors": [],
            "validated_tasks": []
        }
        
        for i, task in enumerate(tasks):
            task_validation = self._validate_single_task(task, i + 1)
            
            if not task_validation["valid"]:
                validation_result["valid"] = False
                validation_result["errors"].extend(task_validation["errors"])
            else:
                validation_result["validated_tasks"].append(task_validation["task"])
        
        return validation_result
    
    def _validate_single_task(self, task: Dict[str, Any], task_number: int) -> Dict[str, Any]:
        result = {
            "valid": True,
            "errors": [],
            "task": task.copy()
        }
        
        date_str = task.get("date")
        time_str = task.get("time")
        
        if date_str or time_str:
            datetime_validation = self.datetime_processor.validate_date_time(date_str, time_str)
            
            if not datetime_validation["valid"]:
                result["valid"] = False
                result["errors"].append(f"Task {task_number}: {datetime_validation['error']}")
                return result
        
        classification = task.get("classification", "").lower()
        if classification not in ["work", "personal"]:
            task["classification"] = "personal"
        
        recurrence = task.get("recurrence", "").lower()
        if recurrence and recurrence not in ["none", "daily", "weekly", "monthly", "yearly"]:
            task["recurrence"] = "none"
        
        if not task.get("description", "").strip():
            result["valid"] = False
            result["errors"].append(f"Task {task_number}: Task description cannot be empty.")
            return result
        
        result["task"] = task
        return result
    
    def validate_task_content(self, task_description: str) -> bool:
        if not task_description or len(task_description.strip()) < 3:
            return False
        
        return True
    
    def get_error_message(self, error_type: str, *args) -> str:
        if error_type in self.error_messages:
            return self.error_messages[error_type].format(*args)
        return "An error occurred while processing your request."
    
    def validate_clarification_response(self, response: str) -> bool:
        return bool(response and response.strip() and len(response.strip()) > 0)
    
    def sanitize_input(self, user_input: str) -> str:
        if not user_input:
            return ""
        
        sanitized = user_input.strip()
        
        sanitized = sanitized.replace('\x00', '')
        
        if len(sanitized) > 4000:
            sanitized = sanitized[:4000]
        
        return sanitized


task_validator = TaskValidator()