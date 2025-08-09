# Telegram Task Scheduler Bot - Technical Specification

## 1. System Overview

A stateless Telegram bot that processes natural language task batches, auto-classifies them as [work] or [personal], and returns the next 3 occurrence dates/times for each task.

## 2. Core Functional Requirements

### 2.1 Input Processing
- **Input Format**: Single Telegram message containing one or more natural language tasks
- **Task Separation**: Natural language separation (no explicit delimiters required)
- **Batch Limitation**: Maximum tasks per batch limited by Telegram's 4096 UTF-8 character message limit
- **Task Types**: Support both one-time and recurring tasks
- **Single Message Constraint**: Only process complete batches within single messages

### 2.2 Task Classification
- **Auto-Classification**: Use GPT-5 to classify each task as [work] or [personal]
- **Classification Logic**: Common sense classification based on task content
- **No Confidence Threshold**: LLM decides autonomously whether clarification is needed
- **Output Format**: Display classification as tags (e.g., "[work]", "[personal]")

### 2.3 Date/Time Processing
- **Timezone**: Fixed GMT+0 (non-configurable)
- **Date Formats**: Support both relative ("next Monday") and absolute ("January 15th") dates
- **Occurrence Limit**: Return maximum 3 next occurrences per task
- **Recurring Patterns**: Support patterns like "every weekday", "monthly", "every 2 weeks", etc.
- **Date Range**: No maximum future date limit

### 2.4 Clarification System
- **Trigger Conditions**: Request clarifications when:
  - No time specified in task
  - Ambiguous dates
  - Multiple potential tasks in single sentence
  - Task classification uncertainty
- **Clarification Preference**: LLM should prefer immediate decision over clarification requests
- **Context Retention**: Maintain conversation context during clarification phase
- **User Response**: User must respond to clarifications before proceeding

## 3. Workflow Specification

### 3.1 Main Workflow
```
User Input → Task Parsing → Clarifications (if needed) → Parsed Task Display → 
User Approval → Final Output → Context Flush → End
```

### 3.2 Detailed State Flow

#### State 1: Awaiting User Input
- Bot waits for user message
- Accept any Telegram user (no authentication required)
- Only process complete task batches

#### State 2: Task Processing
- Parse tasks using GPT-5
- Classify each task as [work] or [personal]
- Identify missing information requiring clarification

#### State 3: Clarification (Optional)
- Send clarification questions if needed
- User must respond to clarifications
- User CANNOT send new tasks during this phase
- Use /clear command to abandon current context

#### State 4: Parsed Task Display
- Show structured natural language summary of parsed tasks
- Include classification tags for each task
- Display inline buttons: Approve ✅ / Reject ❌
- Button constraints: callback_data limited to 64 bytes

#### State 5: User Decision
- **Approve**: Proceed to final output
- **Reject**: Flush context and return to State 1

#### State 6: Final Output
- Display 3 next occurrences for each task
- Format: "Next: Jan 15, 2025 at 14:00 GMT" for each occurrence
- Context automatically flushed
- Conversation ends

## 4. Error Handling Requirements

### 4.1 Input Validation
- **Invalid Dates**: Reject impossible dates (e.g., "February 30th") with error message
- **Invalid Times**: Reject invalid times (e.g., "25:00") with error message
- **Unrelated Input**: Return error for non-task-related messages (e.g., "hello", random text)
- **Graceful Errors**: All errors must return user-friendly messages and log internally

### 4.2 System Constraints
- **Message Length**: Handle Telegram's 4096 character limit gracefully
- **Button Data**: Ensure callback_data stays within 64-byte limit
- **Rate Limiting**: Comply with Telegram Bot API rate limits

## 5. State Management

### 5.1 Context Rules
- **Stateless Between Conversations**: No memory across separate conversations
- **Context During Processing**: Maintain context only during active task processing
- **Context Flush Triggers**:
  - User approves final output
  - User rejects parsed tasks
  - Manual /clear command
  - System error

### 5.2 Context Constraints
- User cannot send new tasks during clarification phase
- Context contains only current task batch (no historical data)
- No cross-user data retention

## 6. Technical Constraints

### 6.1 Telegram API Limits
- **Message Length**: 4096 UTF-8 characters maximum
- **Inline Button Data**: 1-64 bytes per callback_data
- **Button Layout**: Maximum 8 buttons per row
- **API Rate Limits**: Standard Telegram Bot API limits apply

### 6.2 LLM Integration
- **Model**: GPT-5
- **Processing**: Handle both classification and parsing
- **No Confidence Scores**: Internal processing only, not exposed to users

## 7. Output Specifications

### 7.1 Parsed Task Display Format
```
📋 Parsed Tasks:

1. [work] Team meeting every Monday
   - Time: 14:00 GMT
   - Recurrence: Weekly

2. [personal] Call dentist tomorrow
   - Time: 10:00 GMT
   - Date: Jan 16, 2025

[Approve ✅] [Reject ❌]
```

### 7.2 Final Output Format
```
📅 Next Occurrences:

1. [work] Team meeting every Monday
   - Next: Jan 20, 2025 at 14:00 GMT
   - Next: Jan 27, 2025 at 14:00 GMT
   - Next: Feb 3, 2025 at 14:00 GMT

2. [personal] Call dentist tomorrow
   - Next: Jan 16, 2025 at 10:00 GMT
```

## 8. Commands

### 8.1 System Commands
- **/clear**: Manually flush current context and return to initial state
- **/start**: Display bot introduction and usage instructions
- **/help**: Display available commands and usage guide

## 9. Error Messages

### 9.1 Standard Error Responses
- **Invalid Date**: "Invalid date detected: [date]. Please use a valid date format."
- **Invalid Time**: "Invalid time detected: [time]. Please use 24-hour format (HH:MM)."
- **Unrelated Input**: "I can only process task scheduling requests. Please send tasks you'd like me to schedule."
- **Context Conflict**: "Please complete current clarifications or use /clear to start fresh."

## 10. Implementation Notes

### 10.1 Architecture Requirements
- Stateless design for horizontal scaling
- Async processing for Telegram webhook handling
- Robust error logging and monitoring
- GPT-5 API integration with retry logic

### 10.2 Security Considerations
- No user data persistence
- Secure API token management
- Input sanitization for LLM processing
- Rate limiting protection

# Step-by-step implementation plan

## Overview
This plan implements a Telegram bot that processes natural language task batches, classifies them as [work] or [personal], and returns next occurrence dates. The bot uses Python 3.11, aiogram, langchain, and runs in Docker with in-memory state management.

---

## Stage 1: Project Foundation & Environment Setup

### Objective
Establish the project structure, Docker environment, and core dependencies for the Telegram task bot.

### Key Requirements from Tech Spec
- Python 3.11 runtime
- Docker containerization
- Latest versions of aiogram and langchain
- Secure environment configuration
- Basic project architecture

### Implementation Steps
1. **Create Docker Configuration**
   - Write Dockerfile with Python 3.11 base image
   - Set up requirements.txt with aiogram, langchain, python-dotenv
   - Configure Docker environment variables for API tokens
   - Create docker-compose.yml for easy development

2. **Project Structure Setup**
   - Create modular project structure (bot/, handlers/, services/, utils/)
   - Set up configuration management for environment variables
   - Create logging configuration for monitoring and debugging
   - Initialize basic Python package structure with __init__.py files

3. **Environment Configuration**
   - Set up .env template for API keys (TELEGRAM_BOT_TOKEN, OPENAI_API_KEY)
   - Create configuration loader for secure token management
   - Implement environment validation on startup
   - Set up basic error handling for missing configurations

### Deliverables
- Working Docker container that starts without errors
- Proper project structure with all necessary directories
- Environment configuration system that securely loads API tokens
- Basic logging system ready for integration

### Validation Criteria
- Docker container builds and runs successfully
- All dependencies install correctly
- Environment variables load properly
- Project structure follows Python best practices

---

## Stage 2: Telegram Bot Core Infrastructure

### Objective
Implement the foundational Telegram bot using aiogram with polling, basic commands, and message routing structure.

### Key Requirements from Tech Spec
- aiogram framework with polling (not webhooks)
- Commands: /start, /help, /clear
- Async processing for Telegram polling
- Basic error handling structure
- Message routing foundation

### Implementation Steps
1. **aiogram Bot Initialization**
   - Set up Bot and Dispatcher with proper token management
   - Configure polling with error handling and retry logic
   - Implement graceful shutdown handling
   - Add basic middleware for logging user interactions

2. **Command Handlers Implementation**
   - `/start` command: Display bot introduction and usage instructions
   - `/help` command: Show available commands and usage guide
   - `/clear` command: Flush current context (prepare for state management)
   - Implement proper command validation and response formatting

3. **Message Routing Infrastructure**
   - Create message handler structure for text messages
   - Implement basic message validation (length, content type)
   - Set up callback query handler for inline buttons (prepare for Stage 4)
   - Add error handling for unsupported message types

4. **Core Error Handling**
   - Implement standard error response templates from tech spec
   - Create error logging system with user ID and message context
   - Add rate limiting protection structure
   - Set up graceful error recovery mechanisms

### Deliverables
- Fully functional Telegram bot that responds to commands
- Proper polling implementation with error handling
- Basic message routing system ready for task processing
- Command handlers with user-friendly responses

### Validation Criteria
- Bot connects to Telegram API successfully
- All three commands (/start, /help, /clear) work correctly
- Bot handles invalid commands gracefully
- Polling runs continuously without crashes

---

## Stage 3: LLM Integration & Task Processing Engine

### Objective
Integrate langchain with GPT-5, implement task parsing, classification system, and date/time processing according to tech spec requirements.

### Key Requirements from Tech Spec
- GPT-5 integration via langchain (with GPT-4 fallback)
- Auto-classification as [work] or [personal]
- Support both one-time and recurring tasks
- GMT+0 timezone processing
- Date/time validation with proper error handling

### Implementation Steps
1. **langchain & GPT Integration**
   - Set up langchain with OpenAI GPT-5 integration
   - Implement GPT-4 fallback mechanism for availability
   - Create LLM chain for task processing with proper prompting
   - Add retry logic and error handling for API failures

2. **Task Parsing System**
   - Design prompts for extracting tasks from natural language input
   - Implement task boundary detection for multiple tasks in single message
   - Create structured output parsing for task details (time, date, recurrence)
   - Add validation for parsed task components

3. **Classification Engine**
   - Implement [work]/[personal] classification using LLM common sense
   - Create prompt engineering for accurate classification
   - Add confidence assessment to determine when clarification is needed
   - Ensure classification tags format matches tech spec requirements

4. **Date/Time Processing**
   - Implement GMT+0 timezone handling (fixed, non-configurable)
   - Add support for relative dates ("next Monday") and absolute dates
   - Create recurring pattern recognition (daily, weekly, monthly, etc.)
   - Implement date/time validation with specific error messages for impossible dates

### Deliverables
- Working LLM integration that processes natural language tasks
- Task classification system that tags tasks as [work] or [personal]
- Date/time processing engine that handles various input formats
- Comprehensive validation system for dates, times, and task content

### Validation Criteria
- LLM successfully parses complex task inputs
- Classification accuracy meets requirements
- Date/time processing handles edge cases correctly
- All validation errors return proper error messages from tech spec

---

## Stage 4: State Management & Conversation Flow

### Objective
Implement in-memory state management, clarification workflow, inline keyboard system, and complete conversation flow according to tech spec.

### Key Requirements from Tech Spec
- In-memory state storage for conversation context
- Clarification flow when information is missing
- Inline buttons for approval/rejection (within 64-byte callback_data limit)
- State transitions: Input → Processing → Clarification → Display → Approval → Output
- Context flush on approval, rejection, or /clear command

### Implementation Steps
1. **In-Memory State Management**
   - Create user state storage system using dictionaries/dataclasses
   - Implement state lifecycle management (create, update, flush)
   - Add context validation to prevent conflicts during clarification
   - Design state structure to hold parsed tasks and clarification status

2. **Clarification Workflow**
   - Implement clarification trigger logic for missing information
   - Create clarification question generation for ambiguous inputs
   - Add clarification response processing and validation
   - Ensure users cannot send new tasks during clarification phase

3. **Inline Keyboard Implementation**
   - Create approve/reject buttons with proper emoji (✅ ❌)
   - Implement callback_data handling within 64-byte Telegram limit
   - Add callback query processing for user decisions
   - Create button state management and validation

4. **Complete Conversation Flow**
   - Integrate all stages: parsing → clarification → display → approval
   - Implement state transitions according to tech spec workflow
   - Add proper context flushing on all exit conditions
   - Ensure conversation ends properly after final output

### Deliverables
- Complete conversation flow from input to final output
- Working clarification system that handles missing information
- Functional inline keyboard system for user approval
- Robust state management that prevents context conflicts

### Validation Criteria
- State management works correctly across conversation phases
- Clarification flow prevents new tasks during active clarification
- Inline buttons work within Telegram API constraints
- Context flushes properly on all specified conditions

---

## Stage 5: Output Generation & Final Integration

### Objective
Implement output formatting, finalize error handling, complete Docker integration, and ensure all tech spec requirements are met.

### Key Requirements from Tech Spec
- Structured natural language summary for parsed tasks
- Final output format showing 3 next occurrences per task
- Complete error handling with all specified error messages
- Docker container ready for deployment
- All workflow states properly integrated

### Implementation Steps
1. **Output Formatting System**
   - Implement parsed task display format with classification tags
   - Create final occurrence output showing 3 next dates per task
   - Add proper formatting for both one-time and recurring tasks
   - Ensure output stays within Telegram's 4096 character limit

2. **Complete Error Handling**
   - Implement all error messages from tech spec (invalid date, invalid time, unrelated input, context conflict)
   - Add comprehensive input validation and sanitization
   - Create error logging system with proper context
   - Ensure graceful handling of all edge cases

3. **Final Integration & Optimization**
   - Connect all workflow stages into seamless operation
   - Optimize in-memory state management for performance
   - Add proper resource cleanup and memory management
   - Implement final validation of all tech spec requirements

4. **Docker Finalization**
   - Optimize Docker container for production deployment
   - Add health checks and proper startup/shutdown procedures
   - Finalize environment variable configuration
   - Create deployment documentation and container testing

### Deliverables
- Complete working bot that meets all tech spec requirements
- Proper output formatting for both intermediate and final results
- Comprehensive error handling covering all specified cases
- Production-ready Docker container

### Validation Criteria
- Bot handles complete workflow from start to finish
- All output formats match tech spec examples exactly
- Error handling covers all specified error cases
- Docker container is ready for production deployment
- Bot operates within all Telegram API constraints

---

## Implementation Notes

### Cross-Stage Considerations
- Maintain consistent error handling patterns across all stages
- Ensure async/await patterns are used correctly throughout
- Keep state management simple and memory-efficient
- Follow Python best practices and maintain clean code structure

### Integration Points
- Each stage builds upon previous stages' deliverables
- State management connects parsing (Stage 3) with workflow (Stage 4)
- Error handling spans all stages but is finalized in Stage 5
- Docker configuration is established in Stage 1 and finalized in Stage 5

### Success Metrics
- Bot processes task batches correctly from start to finish
- All tech spec requirements are implemented and validated
- Docker container runs reliably in production environment
- Code is maintainable and follows established patterns