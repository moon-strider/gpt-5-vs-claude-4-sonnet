import logging
import asyncio
from typing import Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from langchain.output_parsers import PydanticOutputParser
from config.settings import get_settings

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self):
        self.settings = get_settings()
        self._primary_model = None
        self._fallback_model = None
        self._initialize_models()
    
    def _initialize_models(self):
        try:
            self._primary_model = ChatOpenAI(
                model="gpt-5",
                api_key=self.settings.openai_api_key,
                max_completion_tokens=2000,
                timeout=90,
                temperature=1.0
            )
        except Exception as e:
            logger.warning(f"GPT-5 initialization failed: {e}")
        
        try:
            self._fallback_model = ChatOpenAI(
                model="gpt-4o",
                api_key=self.settings.openai_api_key,
                max_tokens=2000,
                timeout=90,
                temperature=0.1
            )
        except Exception as e:
            logger.error(f"GPT-4o fallback initialization failed: {e}")
            raise
    
    async def _call_llm_structured(self, messages: list, parser: PydanticOutputParser, use_fallback: bool = False):
        try:
            model = self._fallback_model if use_fallback else self._primary_model
            
            if not model:
                if not use_fallback:
                    return await self._call_llm_structured(messages, parser, use_fallback=True)
                raise Exception("No available LLM models")
            
            structured_model = model.with_structured_output(parser.pydantic_object)
            
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: structured_model.invoke(messages)
                    )
                    return response
                except Exception as e:
                    logger.warning(f"Structured LLM call attempt {attempt + 1} failed: {e}")
                    if attempt == max_retries - 1:
                        if not use_fallback and self._fallback_model:
                            logger.info("Switching to fallback model for structured output")
                            return await self._call_llm_structured(messages, parser, use_fallback=True)
                        raise
                    await asyncio.sleep(2 ** attempt)
        except Exception as e:
            logger.error(f"Structured LLM processing error: {e}")
            raise
    
    async def process_tasks_structured(self, user_input: str, parser: PydanticOutputParser):
        system_prompt = f"""Parse tasks from user input. Return JSON only.

{parser.get_format_instructions()}

Key rules:
- "daily" = every day
- "weekly" = same day each week  
- "every Monday Wednesday Friday" = weekly_0_2_4
- "every Tuesday Thursday" = weekly_1_3
- Monday=0, Tuesday=1, Wednesday=2, Thursday=3, Friday=4, Saturday=5, Sunday=6

Examples:
- "brush teeth daily at 2pm" → recurrence: "daily"
- "gym every Monday Wednesday Friday at 5pm" → recurrence: "weekly_0_2_4"

Current input needs parsing:"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_input)
        ]
        
        try:
            result = await self._call_llm_structured(messages, parser)
            return result
        except Exception as e:
            logger.error(f"Structured task processing error: {e}")
            from pydantic import BaseModel, Field
            from typing import List, Optional
            
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
            
            return TaskParsingResult(
                tasks=[],
                needs_clarification=False,
                error="Failed to process tasks. Please try rephrasing your request."
            )
    
    async def update_tasks_with_clarifications(
        self, 
        clarification_response: str, 
        clarifications: list, 
        original_tasks: list
    ):
        system_prompt = """You are updating tasks with clarification responses. 
        
        The user was asked for clarifications and has provided responses. 
        Update the original tasks with the new information provided.
        
        Return the updated tasks in the same format as the original tasks, 
        but with the missing information filled in based on the clarification response.
        
        Rules:
        1. Keep all original task information unless specifically updated by clarifications
        2. Remove items from needs_clarification array once they are resolved
        3. Use GMT+0 timezone for all time processing
        4. Maintain original task classification unless clarification suggests otherwise
        5. For dates: use YYYY-MM-DD format, for times: use HH:MM format (24-hour)
        """
        
        user_message = f"""
        Original clarification questions:
        {chr(10).join(clarifications)}
        
        User's clarification response:
        {clarification_response}
        
        Original tasks to update:
        {original_tasks}
        
        Please update the tasks with the provided clarifications.
        """
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message)
        ]
        
        try:
            model = self._fallback_model or self._primary_model
            if not model:
                raise Exception("No available LLM models")
            
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: model.invoke(messages)
                    )
                    
                    content = response.content.strip()
                    
                    import json
                    import re
                    
                    json_match = re.search(r'\[.*\]', content, re.DOTALL)
                    if json_match:
                        try:
                            updated_tasks = json.loads(json_match.group())
                            return updated_tasks
                        except json.JSONDecodeError:
                            pass
                    
                    return original_tasks
                    
                except Exception as e:
                    logger.warning(f"Clarification update attempt {attempt + 1} failed: {e}")
                    if attempt == max_retries - 1:
                        raise
                    await asyncio.sleep(2 ** attempt)
                    
        except Exception as e:
            logger.error(f"Failed to update tasks with clarifications: {e}")
            return None


llm_service = LLMService()