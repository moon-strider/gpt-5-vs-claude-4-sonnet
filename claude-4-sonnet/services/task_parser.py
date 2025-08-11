import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from pydantic import BaseModel, Field
from langchain.output_parsers import PydanticOutputParser
from services.llm_service import llm_service
from services.task_validator import task_validator

logger = logging.getLogger(__name__)


class TaskInfo(BaseModel):
    description: str = Field(description="The task description")
    classification: str = Field(description="Either 'work' or 'personal'")
    time: Optional[str] = Field(default=None, description="Time in HH:MM format or null")
    date: Optional[str] = Field(default=None, description="Date in YYYY-MM-DD format or null")
    recurrence: Optional[str] = Field(default=None, description="Recurrence pattern: none, daily, weekly, monthly, yearly, or weekly_X_Y_Z for specific weekdays")
    needs_clarification: List[str] = Field(default_factory=list, description="List of clarification questions")
    confidence: str = Field(default="high", description="Confidence level: high, medium, low")


class TaskParsingResult(BaseModel):
    tasks: List[TaskInfo] = Field(description="List of parsed tasks")
    needs_clarification: bool = Field(description="Whether clarification is needed")
    error: Optional[str] = Field(default=None, description="Error message if any")


@dataclass
class ParsedTask:
    description: str
    classification: str
    time: Optional[str] = None
    date: Optional[str] = None
    recurrence: Optional[str] = None
    needs_clarification: List[str] = None
    confidence: str = "high"
    
    def __post_init__(self):
        if self.needs_clarification is None:
            self.needs_clarification = []


class TaskParser:
    def __init__(self):
        self.current_date = datetime.utcnow()
        self.parser = PydanticOutputParser(pydantic_object=TaskParsingResult)
    
    async def parse_tasks(self, user_input: str) -> Dict[str, Any]:
        sanitized_input = task_validator.sanitize_input(user_input)
        
        validation_error = task_validator.validate_input_message(sanitized_input)
        if validation_error:
            return {
                "tasks": [],
                "needs_clarification": False,
                "error": validation_error
            }
        
        try:
            result = await llm_service.process_tasks_structured(sanitized_input, self.parser)
            
            if result.error:
                return {
                    "tasks": [],
                    "needs_clarification": False,
                    "error": result.error
                }
            
            task_dicts = []
            for task_info in result.tasks:
                task_dict = {
                    "description": task_info.description,
                    "classification": task_info.classification,
                    "time": task_info.time,
                    "date": task_info.date,
                    "recurrence": task_info.recurrence,
                    "needs_clarification": task_info.needs_clarification,
                    "confidence": task_info.confidence
                }
                task_dicts.append(task_dict)
            
            validation_result = task_validator.validate_parsed_tasks(task_dicts)
            
            if not validation_result["valid"]:
                return {
                    "tasks": [],
                    "needs_clarification": False,
                    "error": "; ".join(validation_result["errors"])
                }
            
            parsed_tasks = []
            for task_dict in validation_result["validated_tasks"]:
                parsed_task = ParsedTask(
                    description=task_dict["description"],
                    classification=task_dict["classification"],
                    time=task_dict["time"],
                    date=task_dict["date"],
                    recurrence=task_dict["recurrence"],
                    needs_clarification=task_dict["needs_clarification"],
                    confidence=task_dict["confidence"]
                )
                parsed_tasks.append(asdict(parsed_task))
            
            return {
                "tasks": parsed_tasks,
                "needs_clarification": result.needs_clarification,
                "error": None
            }
            
        except Exception as e:
            logger.error(f"Task parsing error: {e}")
            return {
                "tasks": [],
                "needs_clarification": False,
                "error": "Failed to process tasks. Please try rephrasing your request."
            }


task_parser = TaskParser()