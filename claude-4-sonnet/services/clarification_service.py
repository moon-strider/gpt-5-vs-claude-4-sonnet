import logging
from typing import List, Dict, Any, Optional, Tuple
from services.llm_service import llm_service
from services.task_validator import task_validator

logger = logging.getLogger(__name__)


class ClarificationService:
    def __init__(self):
        pass
    
    def extract_clarifications(self, parsed_tasks: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
        all_clarifications = []
        needs_clarification = False
        
        for i, task in enumerate(parsed_tasks):
            task_clarifications = task.get("needs_clarification", [])
            if task_clarifications:
                needs_clarification = True
                for clarification in task_clarifications:
                    formatted_clarification = f"Task {i+1}: {clarification}"
                    all_clarifications.append(formatted_clarification)
        
        return needs_clarification, all_clarifications
    
    def format_clarification_message(self, clarifications: List[str]) -> str:
        if not clarifications:
            return ""
        
        header = "❓ <b>I need some clarifications:</b>\n\n"
        
        clarification_text = ""
        for i, clarification in enumerate(clarifications, 1):
            clarification_text += f"{i}. {clarification}\n"
        
        footer = (
            "\nPlease provide the missing information so I can process your tasks correctly.\n"
            "Use /clear to cancel and start over."
        )
        
        return header + clarification_text + footer
    
    async def process_clarification_response(
        self, 
        response: str, 
        clarifications: List[str],
        original_tasks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        try:
            updated_tasks = []
            
            for task in original_tasks:
                updated_task = task.copy()
                updated_task["needs_clarification"] = []
                updated_tasks.append(updated_task)
            
            validation_result = task_validator.validate_parsed_tasks(updated_tasks)
            
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "error": "Invalid information provided. " + "; ".join(validation_result["errors"]),
                    "updated_tasks": []
                }
            
            return {
                "success": True,
                "error": None,
                "updated_tasks": validation_result["validated_tasks"],
                "still_needs_clarification": False,
                "remaining_clarifications": []
            }
            
        except Exception as e:
            logger.error(f"Error processing clarification response: {e}")
            return {
                "success": False,
                "error": "Failed to process clarification. Please try again or use /clear to start over.",
                "updated_tasks": []
            }
    
    def validate_clarification_response(self, response: str) -> Optional[str]:
        if not response or not response.strip():
            return "Please provide the requested information."
        
        if len(response) > 1000:
            return "Response too long. Please provide concise answers to the clarification questions."
        
        sanitized = task_validator.sanitize_input(response)
        if not sanitized:
            return "Invalid characters in response. Please use standard text."
        
        return None


clarification_service = ClarificationService()