import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class ConversationState(Enum):
    AWAITING_INPUT = "awaiting_input"
    PROCESSING = "processing"
    CLARIFICATION = "clarification"
    DISPLAY = "display"
    FINAL_OUTPUT = "final_output"


@dataclass
class UserState:
    user_id: int
    state: ConversationState = ConversationState.AWAITING_INPUT
    original_message: Optional[str] = None
    parsed_tasks: List[Dict[str, Any]] = field(default_factory=list)
    clarifications_needed: List[str] = field(default_factory=list)
    clarification_responses: Dict[str, str] = field(default_factory=dict)
    message_id_for_approval: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "state": self.state.value,
            "original_message": self.original_message,
            "parsed_tasks": self.parsed_tasks,
            "clarifications_needed": self.clarifications_needed,
            "clarification_responses": self.clarification_responses,
            "message_id_for_approval": self.message_id_for_approval,
            "created_at": self.created_at.isoformat()
        }


class StateManager:
    def __init__(self):
        self._states: Dict[int, UserState] = {}
        self._max_states = 1000
        
    def create_state(self, user_id: int) -> UserState:
        if len(self._states) >= self._max_states:
            self._cleanup_old_states()
        
        state = UserState(user_id=user_id)
        self._states[user_id] = state
        logger.info(f"Created new state for user {user_id}")
        return state
    
    def get_state(self, user_id: int) -> Optional[UserState]:
        return self._states.get(user_id)
    
    def update_state(self, user_id: int, **kwargs) -> bool:
        if user_id not in self._states:
            logger.warning(f"Attempted to update non-existent state for user {user_id}")
            return False
        
        state = self._states[user_id]
        for key, value in kwargs.items():
            if hasattr(state, key):
                setattr(state, key, value)
            else:
                logger.warning(f"Attempted to set invalid state attribute: {key}")
        
        logger.info(f"Updated state for user {user_id}: {kwargs}")
        return True
    
    def flush_state(self, user_id: int) -> bool:
        if user_id in self._states:
            del self._states[user_id]
            logger.info(f"Flushed state for user {user_id}")
            return True
        return False
    
    def has_active_state(self, user_id: int) -> bool:
        return user_id in self._states
    
    def is_in_clarification(self, user_id: int) -> bool:
        state = self.get_state(user_id)
        return state and state.state == ConversationState.CLARIFICATION
    
    def is_awaiting_approval(self, user_id: int) -> bool:
        state = self.get_state(user_id)
        return state and state.state == ConversationState.DISPLAY
    
    def can_accept_new_tasks(self, user_id: int) -> bool:
        state = self.get_state(user_id)
        return not state or state.state == ConversationState.AWAITING_INPUT
    
    def _cleanup_old_states(self):
        current_time = datetime.utcnow()
        old_states = []
        
        for user_id, state in self._states.items():
            time_diff = (current_time - state.created_at).total_seconds()
            if time_diff > 3600:
                old_states.append(user_id)
        
        for user_id in old_states:
            del self._states[user_id]
            logger.info(f"Cleaned up old state for user {user_id}")
    
    def get_state_count(self) -> int:
        return len(self._states)
    
    def get_states_summary(self) -> Dict[str, int]:
        summary = {}
        for state in self._states.values():
            state_name = state.state.value
            summary[state_name] = summary.get(state_name, 0) + 1
        return summary


state_manager = StateManager()