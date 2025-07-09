# 02-conversational-data-cleaning-architecture.md

## Conversational Data Cleaning Architecture Plan

### Executive Summary

This document outlines the architectural plan to transform ScioScribe's current pipeline-based data cleaning system into a conversational data cleaning assistant. The goal is to enable users to interact with their data through natural language commands while maintaining the robust data processing capabilities of the existing system.

### Current State Analysis

#### Strengths of Existing System
- **Modular Architecture**: Separate processors for files, quality analysis, transformations
- **AI-Powered Analysis**: OpenAI integration for quality issues and suggestions
- **Version Management**: Undo/redo capabilities with complete data lineage
- **Custom Transformations**: Preview functionality and user-defined transformations
- **Multiple Input Formats**: CSV, Excel, images via OCR support
- **In-Memory Storage**: Complete data artifact management

#### Architectural Components (Current)
```
FileProcessor → QualityAgent → SuggestionConverter → TransformationEngine → MemoryStore
```

#### Identified Gaps for Conversational Interface
1. **No conversation state management**
2. **No natural language understanding**
3. **No real-time progress updates**
4. **No interactive data exploration**
5. **No session persistence across page refreshes**

### Target Architecture

#### Core Vision
Transform the system into a **conversational data cleaning assistant** that:
- Accepts natural language commands ("clean the email column")
- Provides real-time progress updates via WebSocket
- Maintains conversation history tied to data sessions
- Supports human-in-the-loop confirmations for risky operations
- Enables both chat and programmatic access

#### LangGraph Integration Architecture

**Core Graph Structure:**
```
ConversationalDataCleaningGraph
├── SessionInitializer (create/recover session)
├── MessageProcessor (parse user input)
├── IntentClassifier (understand user requests)
├── DataExplorer (answer data questions)
├── OperationPlanner (plan transformations)
├── RiskAssessment (evaluate operation safety)
├── HumanConfirmation (async approval for risky ops)
├── TransformationExecutor (apply changes)
├── ProgressReporter (WebSocket updates)
└── ResponseGenerator (format chat responses)
```

#### State Management Architecture

**Enhanced State Models:**

```python
ConversationSession:
├── session_id: str
├── artifact_id: str  # Links to existing DataArtifact
├── conversation_history: List[ChatMessage]
├── current_operation: Optional[OperationStatus]
├── pending_confirmations: List[PendingConfirmation]
├── user_context: UserPreferences
└── websocket_connections: List[WebSocketConnection]

ChatMessage:
├── message_id: str
├── timestamp: datetime
├── sender: "user" | "assistant"
├── content: str
├── operation_result: Optional[OperationResult]
└── requires_confirmation: bool

OperationStatus:
├── operation_id: str
├── operation_type: str  # "clean_column", "remove_outliers", etc.
├── status: "planning" | "confirming" | "executing" | "completed" | "failed"
├── progress_message: str
├── affected_columns: List[str]
├── estimated_duration: Optional[int]
└── error_message: Optional[str]
```

#### WebSocket Communication Architecture

**Message Types:**
```python
# Client → Server
UserMessage: {type: "user_message", content: str, session_id: str}
ConfirmationResponse: {type: "confirmation", approved: bool, operation_id: str}
SessionReconnect: {type: "reconnect", session_id: str}

# Server → Client
AssistantMessage: {type: "assistant_message", content: str, timestamp: str}
OperationProgress: {type: "progress", operation_id: str, message: str, percentage: int}
ConfirmationRequest: {type: "confirmation_needed", operation: OperationDetails}
DataUpdate: {type: "data_updated", preview: DataPreview}
ErrorMessage: {type: "error", message: str, recoverable: bool}
```

**WebSocket Integration Points:**
- **FastAPI WebSocket endpoint**: `/ws/dataclean/{session_id}`
- **React WebSocket hook**: Real-time message handling
- **Progress updates**: Live operation status ("Cleaning email column")
- **Data synchronization**: Table updates during transformations

### Conversation Flow Architecture

**Enhanced Message Processing Pipeline:**
```
User Input → Intent Classification → Context Enrichment → Operation Planning
    ↓
Risk Assessment → Confirmation (if needed) → Execution → Progress Updates
    ↓
Result Formatting → Data Table Update → Response Generation → Next Steps
```

**Intent Classification Categories:**
- **Data Exploration**: "show me", "what is", "how many"
- **Data Cleaning**: "clean", "remove", "standardize", "fix"
- **Data Transformation**: "convert", "change", "format", "replace"
- **Data Analysis**: "analyze", "find", "summarize", "describe"
- **Session Management**: "undo", "redo", "reset", "save"

### User Experience Specifications

#### Confirmation UX Strategy
- **Approach**: Inline chat confirmations for better conversation flow
- **Implementation**: Special message type with action buttons
- **Timeout**: 60 seconds with default action
- **Format**: 
  ```
  "I found 45 potential outliers in the 'age' column (values > 120). 
  This operation will remove these rows permanently. 
  [Confirm] [Cancel] [Show Details]"
  ```

#### Progress Tracking
- **Granularity**: Operation-level descriptions
- **Examples**: 
  - "Starting email column cleaning..."
  - "Analyzing 1,250 email entries..."
  - "Found 23 invalid emails, applying fixes..."
  - "Email column cleaning completed ✓"

#### Error Handling & Recovery
1. **Recoverable Errors**: Continue conversation, suggest alternatives
2. **Operation Failures**: Revert to previous state, explain issue
3. **System Errors**: Reconnect, recover session state

#### Session Recovery
- **Full conversation history** restored on reconnection
- **Current data state** synchronized
- **Pending operations** resumed if interrupted
- **Automatic WebSocket reconnection** with exponential backoff

### Integration Strategy

#### Reuse of Existing Components
- **Keep**: All existing models, transformation logic, quality analysis
- **Enhance**: Add conversation awareness to existing agents
- **Add**: LangGraph orchestration, WebSocket communication, session management

#### Modified Components
```python
# Enhanced DataArtifact (add conversation fields)
DataArtifact:
├── [existing fields]
├── conversation_session: Optional[ConversationSession]
├── websocket_connections: List[str]
└── last_interaction: datetime

# Enhanced TransformationEngine (add progress callbacks)
TransformationEngine:
├── [existing methods]
├── progress_callback: Optional[Callable]
├── websocket_notifier: Optional[WebSocketNotifier]
└── async_execution_mode: bool
```

### Data Storage Strategy

#### Simple Session-Based Storage

**Core Principle**: Each conversation session maintains its own isolated copy of data for simplicity and reliability.

**Storage Architecture:**
```
Session Storage (per conversation):
├── original_df: pd.DataFrame (immutable reference)
├── working_df: pd.DataFrame (current state with transformations)
├── conversation_cache: Dict[query, result] (recent "show me" requests)
└── version_history: List[pd.DataFrame] (for undo/redo)
```

**File Size Assumptions:**
- Target files: < 10MB (small to medium datasets)
- Full in-memory processing acceptable
- No need for streaming or chunking
- Session-based copies are memory-efficient enough

#### Data Lineage Management

**Three-Layer Data Flow:**
```
Original File → Working Dataset → Conversation Views
     ↓              ↓                    ↓
  Permanent    Session-scoped       Request-scoped
  Immutable    Transformable        Cached Results
```

**Implementation:**
```python
class ConversationSession:
    def __init__(self, file_path: str):
        # Load original data (immutable)
        self.original_df = pd.read_csv(file_path)
        
        # Create working copy (transformable)
        self.working_df = self.original_df.copy()
        
        # Simple caching for conversation views
        self.query_cache = {}  # {query: result}
        self.view_history = []  # Track what user has seen
```

#### Conversation Data Handling

**Query Response Strategy:**
- **"Show me top 50 rows"**: Return subset from working_df
- **"Clean email column"**: Transform working_df, preserve original_df
- **"Undo last change"**: Restore working_df from version history
- **"Show me results"**: Display subset of current working_df

**Caching Strategy:**
- Cache recent query results (last 5-10 requests)
- Cache column statistics and summaries
- Clear cache when working_df changes
- No persistence across sessions

#### Session Management

**Key Benefits:**
- **Session-based data**: Each conversation has its own data copy
- **Simple state management**: No complex locking or coordination needed
- **Easy cleanup**: Session ends → memory freed
- **Session recovery**: Reconnect to existing session after page refresh

**Memory Management:**
- Acceptable for small files (< 10MB per session)
- Session timeout and cleanup (30 minutes inactivity)
- Garbage collection of unused data

#### Error Recovery & Data Integrity

**Data Safety:**
- **Original file never modified**: Always preserved
- **Working dataset**: Can be reset to original state
- **Transformation tracking**: Clear audit trail
- **Version history**: Enable undo/redo functionality

**Recovery Strategy:**
- Session disconnection → Restore from last known state
- Transformation failure → Revert to previous version
- Data corruption → Reset to original_df

### Technical Implementation

#### New File Structure
```
server/agents/dataclean/
├── [existing files]
├── conversation/
│   ├── __init__.py
│   ├── session_manager.py
│   ├── conversation_agent.py
│   ├── intent_classifier.py
│   ├── message_processor.py
│   └── websocket_handler.py
├── langgraph/
│   ├── __init__.py
│   ├── graph_builder.py
│   ├── nodes/
│   │   ├── __init__.py
│   │   ├── session_nodes.py
│   │   ├── data_nodes.py
│   │   ├── transformation_nodes.py
│   │   └── communication_nodes.py
│   └── state_schema.py
└── websocket/
    ├── __init__.py
    ├── connection_manager.py
    ├── message_router.py
    └── progress_tracker.py
```

#### Data Exploration Enhancements
```python
DataExplorationAgent:
├── query_parser: NLQueryParser  # "show me rows where age > 65"
├── data_summarizer: DataSummarizer  # "what's the distribution"
├── pattern_detector: PatternDetector  # "find anomalies"
├── suggestion_generator: SmartSuggestions  # "next steps"
└── visualization_helper: DataVizHelper  # "create chart data"
```

### Performance & Security

#### Optimization Strategy
- **Lazy Loading**: Only load data when needed
- **Chunked Processing**: Process large datasets in chunks
- **Caching**: Cache frequently accessed data summaries
- **WebSocket Throttling**: Limit update frequency

#### Security Measures
- **Input Validation**: Sanitize all data queries
- **SQL Injection Prevention**: Validate transformation parameters
- **Session Security**: Secure WebSocket connections
- **Rate Limiting**: Prevent abuse of conversation endpoints

### Implementation Roadmap

#### Phase 1: Foundation (Weeks 1-2)
1. LangGraph integration with basic conversation flow
2. WebSocket infrastructure setup
3. Enhanced state management
4. Session recovery mechanism

#### Phase 2: Core Features (Weeks 3-4)
1. Intent classification and message processing
2. Progress tracking and real-time updates
3. Human-in-the-loop confirmations
4. Error handling and recovery

#### Phase 3: Enhancement (Weeks 5-6)
1. Data exploration capabilities
2. Smart suggestions and next steps
3. Performance optimizations
4. Comprehensive testing

### Success Metrics

- **Conversation Quality**: Natural, contextual responses
- **Real-time Performance**: <500ms response times
- **Session Reliability**: 99%+ session recovery success
- **Error Recovery**: Graceful handling of all error types
- **User Experience**: Seamless chat-to-data interaction

### Dependencies

#### Required Technologies
- **LangGraph**: Conversation orchestration
- **WebSocket**: Real-time communication
- **FastAPI**: Enhanced API endpoints
- **React**: Frontend WebSocket integration

#### Existing Dependencies (Reused)
- **OpenAI**: Natural language understanding
- **pandas**: Data manipulation
- **Pydantic**: Data validation
- **In-memory storage**: Session management

### Conclusion

This architecture builds upon the existing robust data cleaning system while adding conversational capabilities. The modular design ensures that current functionality remains intact while enabling natural language interaction, real-time updates, and session persistence. The implementation follows a phased approach to minimize risk and ensure thorough testing of each component.

The result will be a conversational data cleaning assistant that maintains the power and flexibility of the current system while providing an intuitive, chat-based interface for data manipulation and exploration. 