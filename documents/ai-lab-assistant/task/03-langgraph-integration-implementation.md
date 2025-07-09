# 03-langgraph-integration-implementation.md

## LangGraph Integration for Conversational Data Cleaning

### Task Overview

**Goal**: Transform ScioScribe's existing data cleaning system into a conversational AI assistant using LangGraph as the primary orchestration layer.

**Status**: 🔄 In Planning  
**Priority**: P0 (Highest)  
**Estimated Duration**: 3-4 weeks (Updated with Phase 2.5)  
**Assigned To**: Development Team  

**🆕 LATEST UPDATE**: Added **Phase 2.5: Prompt Engineering Enhancement** to replace pattern-based interactions with LLM-powered natural language understanding and response generation. This enhances the conversation quality beyond basic keyword matching.  

### Context

We have a robust, production-ready data cleaning system (~2,800 lines of working code) that processes data end-to-end. The next critical step is adding conversational capabilities through **LangGraph orchestration** to enable natural language interaction with the existing AI-powered components.

**Key Insight**: LangGraph serves as the **conversation orchestrator** that coordinates our existing backend components, not as a replacement for them.

**Implementation Focus**: Streamlined for **CSV files (primary)** and **Excel files (secondary)** to accelerate development and reduce complexity.

### Success Criteria

- [ ] Natural language conversation interface via LangGraph orchestration
- [ ] Seamless integration with existing `complete_processor.py` and components
- [ ] Stateful conversation management across multiple turns
- [ ] Context-aware data processing based on conversation history
- [ ] Safe operation handling with confirmation workflows
- [ ] Extensible architecture for additional conversation patterns
- [ ] **Primary focus**: CSV file processing with conversational interface
- [ ] **Secondary focus**: Excel file support for common use cases
- [ ] **NEW**: LLM-powered intent classification and response generation (Phase 2.5)
- [ ] **NEW**: Natural language understanding with conversation context (Phase 2.5)
- [ ] **NEW**: AI-powered risk assessment and confirmation workflows (Phase 2.5)

### Current Foundation (Assets to Leverage)

#### Existing Working Components (Keep Unchanged)
- `complete_processor.py` (454 lines) - End-to-end workflow orchestration
- `quality_agent.py` (496 lines) - AI-powered quality analysis with OpenAI
- `transformation_engine.py` (531 lines) - Data transformation with version control
- `memory_store.py` (323 lines) - In-memory data artifact management
- `file_processor.py` (213 lines) - **CSV/Excel file processing** (primary focus)
- `suggestion_converter.py` (490 lines) - AI suggestion to transformation conversion
- `models.py` (292 lines) - Comprehensive Pydantic models

#### Existing Capabilities (Fully Functional)
- ✅ AI quality analysis with OpenAI GPT-4
- ✅ **CSV and Excel data ingestion** (core focus)
- ✅ Advanced transformation engine (5 types)
- ✅ Version control and data lineage
- ✅ Error handling and recovery
- ✅ Session-based data management

**Note**: Image processing (`easyocr_processor.py`) remains available but is **not part of the initial LangGraph implementation** to maintain focus and accelerate development.

### Implementation Strategy

## Phase 1: Core LangGraph Architecture (Week 1) - **START HERE**

### 1.1 LangGraph Foundation Setup
- [ ] **Create LangGraph conversation orchestrator**
  - [ ] Install and configure LangGraph dependencies
  - [ ] Define conversation state schema
  - [ ] Create basic graph structure with nodes
  - [ ] Set up conversation flow management
  - [ ] **Focus on CSV/Excel data context** in state management

**Files to Create:**
- `server/agents/dataclean/langgraph/__init__.py`
- `server/agents/dataclean/langgraph/conversation_graph.py`
- `server/agents/dataclean/langgraph/state_schema.py`
- `server/agents/dataclean/langgraph/nodes.py`

### 1.2 Conversation State Management
- [ ] **Implement conversational state handling**
  - [ ] Link conversation state to existing `DataArtifact` model
  - [ ] Manage conversation history and context
  - [ ] Handle session recovery and persistence
  - [ ] Integrate with existing `memory_store.py`
  - [ ] **CSV/Excel specific**: Track file format, sheet names (Excel), delimiter detection

**State Integration Strategy:**
- **Session Context**: Current user, data artifact, conversation history
- **Data Context**: DataFrame state, available operations, transformation history
- **File Context**: **CSV/Excel specific** - file format, encoding, sheet selection
- **Operation Context**: User intent, confirmation status, processing results
- **Response Context**: Formatted responses, next steps, error handling

### 1.3 Basic Intent Classification
- [ ] **Natural language understanding for data operations**
  - [ ] Create intent classifier for common commands
  - [ ] Define intent categories (explore, clean, transform, analyze)
  - [ ] Implement command parsing and parameter extraction
  - [ ] Add confidence scoring and fallback handling
  - [ ] **CSV/Excel specific**: Handle column references, sheet selection, delimiter questions

**Intent Categories to Support:**
- **Data Exploration**: "show me", "what is", "how many rows", "what columns"
- **Data Cleaning**: "clean", "fix", "remove", "standardize"
- **Data Transformation**: "convert", "change", "format"
- **Quality Analysis**: "analyze", "find issues", "what's wrong"
- **Session Management**: "undo", "save", "export"
- **File-Specific**: "which sheet", "change delimiter", "encoding issues"

## Phase 2: Backend Component Integration (Week 2)

### 2.1 LangGraph Node Implementation
- [ ] **Create conversation nodes that wrap existing components**
  - [ ] Message parser node (understand user input)
  - [ ] Context loader node (get data state from `memory_store.py`)
  - [ ] Processing router node (route to existing processors)
  - [ ] Risk assessment node (evaluate operation safety)
  - [ ] Response generator node (format conversational responses)
  - [ ] **CSV/Excel handler node** (file format specific operations)

**Node Integration Strategy:**
```python
# Example: Processing Router Node (CSV/Excel focused)
async def process_data_node(state: ConversationState):
    # Route to existing components based on intent
    if intent == "clean_column":
        return await complete_processor.clean_column(df, params)
    elif intent == "show_data":
        return await dataframe_query(df, params)
    elif intent == "analyze_quality":
        return await quality_agent.analyze_data(df)
    elif intent == "select_sheet":  # Excel specific
        return await handle_excel_sheet_selection(file_path, sheet_name)
    elif intent == "detect_delimiter":  # CSV specific
        return await detect_csv_delimiter(file_path)
```

### 2.2 Conversation Flow Orchestration
- [ ] **Implement conversation workflow**
  - [ ] Message processing pipeline
  - [ ] Context enrichment with existing data artifacts
  - [ ] Route to appropriate existing processors
  - [ ] Generate contextual responses
  - [ ] Handle multi-turn conversations
  - [ ] **CSV/Excel specific**: File format detection, sheet selection, delimiter handling

**Conversation Flow:**
```
User Message → Parse Intent → Load Data Context → Handle File Format → 
Assess Risk → Process (via existing components) → Format Response → Update State
```

### 2.3 Enhanced Component Integration
- [ ] **Extend existing components with conversation awareness**
  - [ ] Add conversation context to existing method calls
  - [ ] Implement progress callbacks for status updates
  - [ ] Add confirmation hooks for risky operations
  - [ ] Enhance response formatting for conversational output
  - [ ] **Streamline file processing** to focus on CSV/Excel workflows

**Integration Points:**
- **`complete_processor.py`**: Add conversation context parameter, focus on CSV/Excel
- **`quality_agent.py`**: Add conversational response formatting
- **`transformation_engine.py`**: Add confirmation checkpoints
- **`memory_store.py`**: Extend with conversation state storage
- **`file_processor.py`**: **Prioritize CSV/Excel processing** in conversational context

## Phase 2.5: Prompt Engineering Enhancement (Week 2.5) - **RECOMMENDED ADDITION**

### 2.5.1 LLM-Based Intent Classification
- [ ] **Replace pattern-based classification with LLM understanding**
  - [ ] Design prompts for intent classification with context awareness
  - [ ] Implement structured outputs for intent + confidence + parameters
  - [ ] Add conversation history context to intent classification
  - [ ] Handle ambiguous queries with clarification prompts
  - [ ] **CSV/Excel specific**: Contextual understanding of file operations

**Intent Classification Prompt Strategy:**
```
You are a data cleaning assistant. Analyze the user's message and classify their intent.

Context: {conversation_history}
Current Data: {data_context}
File Format: {file_format}
User Message: {user_message}

Classify the intent and extract parameters:
- Intent: [explore|clean|transform|analyze|session|file_operation]
- Confidence: [0.0-1.0]
- Parameters: {extracted_params}
- Reasoning: {explanation}
```

### 2.5.2 Context-Aware Response Generation
- [ ] **Enhance response generation with LLM**
  - [ ] Design prompts for natural, conversational responses
  - [ ] Add conversation context and data state awareness
  - [ ] Generate helpful next steps and suggestions
  - [ ] Handle error explanations conversationally
  - [ ] **CSV/Excel specific**: File format appropriate responses

**Response Generation Prompt Strategy:**
```
Generate a conversational response for the data cleaning assistant.

Context: {conversation_history}
User Intent: {intent}
Operation Result: {operation_result}
Data State: {data_context}
Error (if any): {error_message}

Generate a helpful, conversational response that:
- Acknowledges the user's request
- Explains what was done or what went wrong
- Suggests next steps if appropriate
- Maintains friendly, professional tone
```

### 2.5.3 Advanced Parameter Extraction
- [ ] **LLM-powered parameter extraction**
  - [ ] Design prompts for complex parameter extraction
  - [ ] Handle implicit references and context
  - [ ] Extract column names, conditions, and operations
  - [ ] **CSV/Excel specific**: Sheet names, delimiters, encoding preferences

**Parameter Extraction Prompt Strategy:**
```
Extract parameters from the user's data cleaning request.

Available Columns: {column_names}
Data Types: {column_types}
File Format: {file_format}
User Request: {user_message}

Extract:
- Target columns: [list]
- Operations: [list]
- Conditions: [list]
- File-specific params: {csv_excel_params}
```

### 2.5.4 Multi-Turn Context Understanding
- [ ] **Conversation continuity with LLM**
  - [ ] Design prompts for conversation memory
  - [ ] Handle implicit references to previous operations
  - [ ] Maintain context across multiple turns
  - [ ] Resolve pronouns and implicit references

**Context Understanding Prompt Strategy:**
```
Maintain conversation context for data cleaning operations.

Conversation History: {conversation_history}
Current Data State: {data_context}
Previous Operations: {operation_history}
User Message: {user_message}

Resolve:
- What data/columns is the user referring to?
- What operation do they want to perform?
- Are they referring to previous results?
- Do they need clarification?
```

### 2.5.5 Confirmation and Risk Assessment Prompts
- [ ] **AI-powered risk assessment**
  - [ ] Design prompts for operation risk evaluation
  - [ ] Generate clear confirmation messages
  - [ ] Explain potential impacts of operations
  - [ ] **CSV/Excel specific**: Format-specific risks

**Risk Assessment Prompt Strategy:**
```
Evaluate the risk of the requested data operation.

Operation: {operation_type}
Target Data: {target_description}
Data Size: {data_size}
Operation Details: {operation_params}

Assess:
- Risk Level: [low|medium|high]
- Potential Impact: {impact_description}
- Confirmation Message: {confirmation_text}
- Reversibility: {undo_possible}
```

## Phase 3: Advanced Conversation Features (Week 3)

### 3.1 Multi-Turn Conversation Support
- [ ] **Handle complex conversational workflows**
  - [ ] Multi-step operation planning
  - [ ] Context awareness across conversation turns
  - [ ] Follow-up question handling
  - [ ] Conversation state persistence

### 3.2 Risk Assessment and Confirmation
- [ ] **Implement safe operation handling**
  - [ ] Risk evaluation for data operations
  - [ ] Confirmation workflow for destructive actions
  - [ ] Preview generation before changes
  - [ ] Timeout and fallback handling

### 3.3 Data Exploration Enhancement
- [ ] **Natural language data queries**
  - [ ] "Show me the first 10 rows where email is missing"
  - [ ] "What's the distribution of the age column?"
  - [ ] "Find rows with outliers in salary"
  - [ ] "Summarize the data quality issues"
  - [ ] **CSV specific**: "What's the delimiter?", "Are there encoding issues?"
  - [ ] **Excel specific**: "Which sheets are available?", "Switch to Sheet2"

### 3.4 Conversation Memory and Context
- [ ] **Advanced conversation management**
  - [ ] Conversation history tracking
  - [ ] User preference learning
  - [ ] Context-aware suggestions
  - [ ] Session recovery and continuation

## Integration Architecture

### LangGraph as Conversation Orchestrator

**Current Architecture (Linear):**
```
User Input → complete_processor.py → quality_agent.py → transformation_engine.py → Output
```

**LangGraph Architecture (Conversational):**
```
User Message → LangGraph Workflow → Route to Existing Components → LangGraph Response
```

### Component Coordination Strategy

**Existing Components (Unchanged):**
- All current processing logic remains intact
- No breaking changes to existing APIs
- Maintain current data models and storage
- **Simplified scope**: Focus on CSV/Excel processing workflows

**LangGraph Enhancements:**
- **Conversation wrapper** around existing components
- **State management** for conversation context
- **Flow control** for multi-turn interactions
- **Response formatting** for conversational output
- **File format handling** optimized for CSV/Excel workflows

### State Management Integration

**LangGraph State Schema:**
```python
class ConversationState(TypedDict):
    # Session Management
    session_id: str
    artifact_id: Optional[str]  # Links to existing DataArtifact
    user_id: str
    
    # File Context (CSV/Excel focused)
    file_format: str  # "csv" or "excel"
    sheet_name: Optional[str]  # Excel sheets
    delimiter: Optional[str]  # CSV delimiter
    encoding: Optional[str]  # File encoding
    
    # Conversation Flow
    user_message: str
    intent: str
    response: str
    
    # Data Context (from existing memory_store)
    data_context: Optional[Dict[str, Any]]
    current_dataframe: Optional[str]
    
    # Processing State
    pending_operation: Optional[Dict[str, Any]]
    confirmation_required: bool
    operation_result: Optional[Dict[str, Any]]
```

## Testing & Validation

### 3.5 LangGraph Workflow Testing
- [ ] **Unit tests for conversation nodes**
  - [ ] Intent classification accuracy
  - [ ] State management functionality
  - [ ] Component integration tests
  - [ ] Conversation flow validation

- [ ] **Integration tests with existing components**
  - [ ] End-to-end conversation workflows
  - [ ] Multi-turn conversation handling
  - [ ] Error recovery scenarios
  - [ ] State persistence testing

### 3.6 Conversation Flow Validation
- [ ] **Test conversation patterns**
  - [ ] Simple data cleaning conversation
  - [ ] Complex multi-step workflow
  - [ ] Error handling and recovery
  - [ ] Context awareness validation

## Implementation Files Structure

### Required File Creation
```
server/agents/dataclean/
├── [existing files - keep unchanged]
├── langgraph/
│   ├── __init__.py
│   ├── conversation_graph.py      # Main LangGraph workflow
│   ├── state_schema.py           # Conversation state models
│   ├── nodes.py                  # LangGraph nodes (wrap existing code)
│   └── edges.py                  # Conditional workflow routing
└── conversation/
    ├── __init__.py
    ├── intent_classifier.py      # Natural language understanding
    ├── context_manager.py        # Conversation context handling
    ├── response_formatter.py     # Conversational response generation
    └── file_handler.py          # CSV/Excel specific conversation handling
```

### Enhanced Model Extensions
- [ ] **Extend `models.py` with conversation schemas**
  - [ ] Conversation state models
  - [ ] Intent classification models
  - [ ] Response formatting models
  - [ ] Session management models
  - [ ] **CSV/Excel specific models** (file format, sheet selection, delimiter detection)

## Success Metrics

### Immediate Success Criteria
- [ ] LangGraph successfully orchestrates existing components
- [ ] Natural language commands are understood and executed
- [ ] Conversation state is maintained across multiple turns
- [ ] All existing functionality remains intact
- [ ] Context-aware responses are generated
- [ ] **CSV file processing** works conversationally
- [ ] **Excel file support** handles basic sheet selection

### Quality Metrics
- [ ] Intent classification accuracy > 90%
- [ ] Zero regression in existing data processing functionality
- [ ] Conversation continuity across multiple interactions
- [ ] Safe operation handling with appropriate confirmations

## Risk Mitigation

### Technical Risks
- **LangGraph learning curve**: New framework adoption
  - *Mitigation*: Start with simple workflows, leverage existing patterns
- **State management complexity**: Conversation state synchronization
  - *Mitigation*: Build on existing `memory_store.py` patterns
- **Component integration**: Connecting conversation layer with existing code
  - *Mitigation*: Wrapper approach preserves existing functionality

### Implementation Risks
- **Scope creep**: Adding too many features too quickly
  - *Mitigation*: Phased approach focusing on core orchestration first
- **Performance impact**: Additional conversation overhead
  - *Mitigation*: Lightweight state management and efficient routing

## Dependencies

### New Technical Dependencies
- **LangGraph** (`langgraph>=0.0.40`) - Core conversation orchestration
- **CSV/Excel processing libraries** (already included in existing setup)
- **Additional NLP libraries** for intent classification (if needed)

### Existing Dependencies (Reused)
- **OpenAI API** (already integrated in `quality_agent.py`)
- **pandas** (CSV/Excel processing)
- **openpyxl** (Excel support)
- **All current dependencies** remain unchanged
- **No new infrastructure** requirements

**Note**: Removed `easyocr` and image processing dependencies from the initial implementation scope.

## Definition of Done

### Phase 1 Completion
- [ ] LangGraph conversation orchestrator is functional
- [ ] Basic conversation state management is working
- [ ] Intent classification handles common commands
- [ ] Integration with existing components is successful
- [ ] **CSV file processing** works conversationally
- [ ] **Excel file support** handles basic sheet selection

### Phase 2 Completion
- [ ] Multi-turn conversations are supported
- [ ] Risk assessment and confirmation workflows are implemented
- [ ] All existing component functionality is accessible conversationally
- [ ] Response formatting is conversational and helpful
- [ ] **CSV/Excel specific features** work seamlessly (delimiter detection, sheet selection)

### Phase 2.5 Completion (Prompt Engineering Enhancement)
- [ ] LLM-based intent classification replaces pattern matching
- [ ] Context-aware response generation produces natural conversations
- [ ] Advanced parameter extraction handles complex queries
- [ ] Multi-turn context understanding maintains conversation continuity
- [ ] AI-powered risk assessment provides intelligent confirmations
- [ ] **CSV/Excel specific**: Contextual understanding of file operations
- [ ] All prompt strategies are tested and optimized

### Phase 3 Completion
- [ ] Advanced conversation features are implemented
- [ ] Complex multi-step workflows are supported
- [ ] Error handling and recovery are robust
- [ ] System is ready for API/WebSocket integration
- [ ] **File format handling** is comprehensive for CSV/Excel use cases

## Future Phases (Post-LangGraph)

### Phase 4: API Integration (Week 4-5)
- REST API endpoints for conversation management
- Session management APIs
- Data context APIs
- **CSV/Excel upload endpoints** with conversation initiation

### Phase 5: WebSocket Integration (Week 5-6)
- Real-time conversation communication
- Progress streaming during operations
- Live status updates

### Phase 6: Extended File Format Support (Future)
- Image processing integration (`easyocr_processor.py`)
- PDF processing capabilities
- Additional structured data formats

**Next Steps**: Begin Phase 1 with LangGraph core setup focusing on CSV file processing. Excel support will be added incrementally to validate the conversation orchestration approach.

**Key Principle**: LangGraph enhances existing CSV/Excel processing capabilities through conversation orchestration while maintaining simplicity and focus.

**NEW - Phase 2.5 Addition**: After successful Phase 2 backend integration, implement prompt engineering enhancements to transform pattern-based interactions into truly natural conversations using LLM-powered understanding and response generation.

**Review Date**: Weekly progress reviews on Fridays  
**Escalation Path**: Technical challenges → Lead Developer → Product Owner 