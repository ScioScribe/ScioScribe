# 02-conversational-data-cleaning-architecture.md

## Conversational Data Cleaning Architecture Plan

### Executive Summary

This document outlines the architectural plan to transform ScioScribe's current pipeline-based data cleaning system into a conversational data cleaning assistant. The goal is to enable users to interact with their data through natural language commands while maintaining the robust data processing capabilities of the existing system.

### Current State Analysis

#### What's Actually Working (Implemented & Tested)
- **Complete End-to-End Processing**: `complete_processor.py` handles full workflow
- **AI-Powered Quality Analysis**: OpenAI GPT-4 integration for intelligent issue detection
- **Multi-Format File Support**: CSV, Excel, and image OCR processing
- **Advanced Transformation Engine**: 5 transformation types with preview capability
- **Version Control**: Complete undo/redo with data lineage tracking
- **In-Memory Data Management**: Full artifact lifecycle management
- **Production-Ready Models**: Comprehensive Pydantic models for all data structures
- **Robust Error Handling**: Graceful failure recovery throughout the pipeline

#### Demonstrated Capabilities
- **Automatic Data Quality Assessment**: Detects type mismatches, missing values, inconsistencies
- **Intelligent Suggestion Generation**: AI-powered recommendations with confidence scores
- **Custom Transformation Rules**: User-defined transformations with reusable rules
- **Multi-Modal Data Ingestion**: Handles structured files and image-based tables
- **Real-Time Processing**: Processes datasets in seconds with progress tracking

#### Strengths of Existing System
- **Modular Architecture**: Clean separation of concerns across all components
- **AI-First Design**: OpenAI integration throughout quality analysis and suggestions
- **Data Safety**: Immutable originals with full transformation history
- **Extensible Framework**: Easy to add new transformation types and processors
- **Memory Efficient**: Handles datasets up to 10MB with session-based storage

#### Architectural Components (Currently Implemented)
```
FileProcessor → QualityAgent → SuggestionConverter → TransformationEngine → MemoryStore
    ↓               ↓              ↓                    ↓                ↓
file_processor.py  quality_agent.py  suggestion_converter.py  transformation_engine.py  memory_store.py
```

**Complete Integration Available:**
- `complete_processor.py` - Orchestrates the entire workflow in one call
- `models.py` - Comprehensive Pydantic models for all data structures
- `easyocr_processor.py` - OCR support for image-based data extraction

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

#### Current File Structure (Implemented)
```
server/agents/dataclean/
├── models.py                    # Complete Pydantic models (292 lines)
├── complete_processor.py        # End-to-end workflow orchestration (454 lines)
├── file_processor.py           # Multi-format file processing (213 lines)
├── quality_agent.py            # AI-powered quality analysis (496 lines)
├── suggestion_converter.py     # Suggestion to transformation conversion (490 lines)
├── transformation_engine.py    # Data transformation engine (531 lines)
├── memory_store.py             # In-memory data storage (323 lines)
├── easyocr_processor.py        # OCR processing for images (399 lines)
└── demo/                       # Demo and test files
    ├── sample_data_messy.csv
    ├── test_*.py
    └── run_test.py
```

#### Required Additions for Conversational Interface
```
server/agents/dataclean/
├── [existing files above]
├── conversation/
│   ├── __init__.py
│   ├── session_manager.py      # Session state management
│   ├── conversation_agent.py   # LangGraph conversation orchestration
│   ├── intent_classifier.py    # Natural language understanding
│   └── websocket_handler.py    # Real-time communication
└── langgraph/
    ├── __init__.py
    ├── graph_builder.py         # LangGraph workflow definition
    ├── nodes/                   # Individual agent nodes
    │   ├── session_nodes.py
    │   ├── data_nodes.py
    │   └── transformation_nodes.py
    └── state_schema.py          # Conversation state models
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

#### Phase 1: LangGraph Integration (Weeks 1-2)
**Goal**: Add conversational orchestration to existing working system
1. **LangGraph Workflow Setup**: Create conversation graph that orchestrates existing components
2. **Session State Management**: Implement conversation sessions with data context
3. **Intent Classification**: Basic NLU for common data cleaning commands
4. **WebSocket Foundation**: Real-time communication infrastructure

**Leverage Existing**: Use `complete_processor.py` as the core execution engine

#### Phase 2: Conversational Interface (Weeks 3-4)
**Goal**: Enable natural language interaction with data
1. **Message Processing**: Handle user requests and route to appropriate processors
2. **Progress Streaming**: Real-time updates during processing via WebSocket
3. **Confirmation Workflows**: Human-in-the-loop for risky operations
4. **Data Exploration**: Natural language queries for data inspection

**Leverage Existing**: Build on `quality_agent.py` and `transformation_engine.py`

#### Phase 3: Advanced Features (Weeks 5-6)
**Goal**: Enhanced conversational capabilities
1. **Context Awareness**: Remember conversation history and user preferences
2. **Multi-Step Workflows**: Handle complex requests spanning multiple operations
3. **Smart Suggestions**: Proactive recommendations based on data patterns
4. **Error Recovery**: Graceful handling of failures with explanations

**Leverage Existing**: Extend `memory_store.py` and `suggestion_converter.py`

#### Current Foundation Advantage
- **~2,800 lines of production-ready code** already implemented
- **Working AI integration** with OpenAI for quality analysis
- **Complete data processing pipeline** from file upload to clean export
- **Robust error handling** and version control throughout

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

### Immediate Next Steps

#### Priority 1: LangGraph Integration
**Estimated Time**: 1-2 weeks
1. **Create LangGraph workflow** that orchestrates existing `complete_processor.py`
2. **Add session management** to track conversation state and data context
3. **Implement basic intent classification** for common commands
4. **Set up WebSocket endpoints** for real-time communication

#### Priority 2: Conversational Layer
**Estimated Time**: 2-3 weeks
1. **Natural language processing** for data cleaning commands
2. **Progress streaming** during processing operations
3. **Confirmation workflows** for risky transformations
4. **Error handling** with conversational explanations

#### Key Integration Points
- **`complete_processor.py`**: Already handles end-to-end processing
- **`quality_agent.py`**: AI analysis can be conversational
- **`transformation_engine.py`**: Add progress callbacks for real-time updates
- **`memory_store.py`**: Extend for conversation history storage

### Conclusion

**Current Status**: ScioScribe has a robust, production-ready data cleaning system with ~2,800 lines of working code, AI integration, and comprehensive data processing capabilities.

**Next Goal**: Add conversational capabilities to the existing system through LangGraph integration, enabling natural language interaction while leveraging all existing functionality.

**Advantage**: Unlike starting from scratch, this approach builds on a proven, working foundation with sophisticated AI analysis and transformation capabilities already in place.

The result will be a conversational data cleaning assistant that maintains the power and flexibility of the current system while providing an intuitive, chat-based interface for data manipulation and exploration. 