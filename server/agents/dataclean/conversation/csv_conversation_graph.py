"""
CSV Conversation Graph for artifact-free data cleaning.

This module provides a LangGraph-based conversation flow for processing
CSV data strings with natural language interaction and HITL approval.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph

from ..models import (
    CSVMessageRequest,
    CSVProcessingResponse,
    CSVConversationState,
    CSVAnalysisResult,
    CSVTransformationRequest
)
from ..csv_processor import CSVDirectProcessor
from ..quality_agent import DataQualityAgent
from ..memory_store import get_data_store

logger = logging.getLogger(__name__)


class CSVConversationGraph:
    """
    LangGraph-based conversation system for CSV data cleaning.
    
    This system handles:
    - Natural language conversation flow
    - CSV quality analysis
    - Transformation suggestions
    - Human-in-the-loop approval
    - Direct CSV processing
    """
    
    def __init__(self, openai_client=None):
        """Initialize the CSV conversation graph."""
        self.openai_client = openai_client
        self.csv_processor = CSVDirectProcessor(openai_client)
        self.quality_agent = DataQualityAgent(openai_client) if openai_client else None
        self.data_store = get_data_store()
        self.sessions: Dict[str, Union[CSVConversationState, Dict[str, Any]]] = {}
        
        # Build and compile the graph
        self.graph = self._build_csv_graph()
        self.compiled_graph = self.graph.compile()
        
        logger.info("CSV Conversation Graph initialized successfully")
    
    def _build_csv_graph(self) -> StateGraph:
        """Build the CSV conversation graph with LangGraph."""
        # Use a dictionary-based state schema for LangGraph compatibility
        from typing_extensions import TypedDict
        
        class State(TypedDict):
            session_id: str
            user_id: str
            original_csv: str
            current_csv: str
            user_message: str
            intent: str
            response: str
            quality_issues: List[str]
            pending_transformations: List[str]
            awaiting_approval: bool
            applied_transformations: List[str]
            confidence_score: float
        
        graph = StateGraph(State)
        
        # Add nodes
        graph.add_node("parse_message", self._parse_csv_message)
        graph.add_node("classify_intent", self._classify_intent)
        graph.add_node("analyze_csv", self._analyze_csv)
        graph.add_node("generate_suggestions", self._generate_suggestions)
        graph.add_node("request_approval", self._request_approval)
        graph.add_node("apply_changes", self._apply_changes)
        graph.add_node("compose_response", self._compose_response)
        graph.add_node("handle_row_operations", self._handle_row_operations)
        
        # Define the flow
        graph.set_entry_point("parse_message")
        
        # Conditional edges based on processing flow
        graph.add_edge("parse_message", "classify_intent")
        graph.add_conditional_edges(
            "classify_intent",
            self._route_after_intent,
            {
                "analyze": "analyze_csv",
                "greeting": "analyze_csv",
                "transform": "generate_suggestions",
                "approval": "apply_changes",
                "row_operations": "handle_row_operations",
                "response": "compose_response"
            }
        )
        
        graph.add_edge("analyze_csv", "generate_suggestions")
        graph.add_conditional_edges(
            "generate_suggestions",
            self._route_after_suggestions,
            {
                "approval_needed": "request_approval",
                "apply_directly": "apply_changes",
                "direct_response": "compose_response"
            }
        )
        
        graph.add_edge("request_approval", "compose_response")
        graph.add_edge("apply_changes", "compose_response")
        graph.add_edge("handle_row_operations", "compose_response")
        graph.add_edge("compose_response", END)
        
        return graph
    
    async def process_csv_conversation(self, request: CSVMessageRequest) -> CSVProcessingResponse:
        """
        Process a CSV conversation request through the LangGraph.
        
        Args:
            request: CSV message request
            
        Returns:
            CSVProcessingResponse with processing results
        """
        try:
            # Create or update conversation state
            state = self._get_or_create_state(request)
            
            # Process through the graph
            result = await self.compiled_graph.ainvoke(state)
            
            # Convert state to response
            response = self._state_to_response(result)
            
            # Update session storage
            self.sessions[request.session_id] = result
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing CSV conversation: {str(e)}")
            return CSVProcessingResponse(
                success=False,
                original_csv=request.csv_data,
                session_id=request.session_id,
                error_message=f"Conversation processing failed: {str(e)}"
            )
    
    async def handle_approval(self, request: CSVTransformationRequest) -> CSVProcessingResponse:
        """
        Handle user approval for transformations.
        
        Args:
            request: Transformation approval request
            
        Returns:
            CSVProcessingResponse with approval result
        """
        try:
            if request.session_id not in self.sessions:
                return CSVProcessingResponse(
                    success=False,
                    original_csv="",
                    session_id=request.session_id,
                    error_message="Session not found"
                )
            
            state = self.sessions[request.session_id]
            
            # Handle both dictionary and Pydantic model states
            if isinstance(state, dict):
                # Update dictionary state with approval
                state["awaiting_approval"] = False
                
                if request.approved:
                    # Apply pending transformations
                    pending_transformations = state.get("pending_transformations", [])
                    if pending_transformations:
                        state["current_csv"] = await self.csv_processor.apply_csv_transformations(
                            state["current_csv"], pending_transformations
                        )
                        
                        # Save cleaned data to data store for persistence
                        cleaned_df = self.csv_processor._parse_csv_string(state["current_csv"])
                        if cleaned_df is not None:
                            await self.data_store.save_dataframe(state["session_id"], cleaned_df)
                            logger.info(f"Saved cleaned data to data store for session {state['session_id']}")
                        
                        applied = state.get("applied_transformations", [])
                        applied.extend(pending_transformations)
                        state["applied_transformations"] = applied
                        state["pending_transformations"] = []
                        
                        response_message = "Great! I've applied the changes to your data."
                    else:
                        response_message = "No changes were applied."
                else:
                    # Clear pending transformations
                    state["pending_transformations"] = []
                    response_message = "Understood. I won't make those changes."
                    
                    if request.user_feedback:
                        response_message += f" {request.user_feedback}"
                
                state["response"] = response_message
                
                # Store updated state
                self.sessions[request.session_id] = state
                
                return CSVProcessingResponse(
                    success=True,
                    original_csv=state["original_csv"],
                    cleaned_csv=state["current_csv"],
                    changes_made=state.get("applied_transformations", []),
                    session_id=request.session_id,
                    conversation_active=True,
                    response_message=response_message
                )
            else:
                # Legacy Pydantic model handling
                state.awaiting_approval = False
                
                if request.approved:
                    # Apply pending transformations
                    if state.pending_transformations:
                        state.current_csv = await self.csv_processor.apply_csv_transformations(
                            state.current_csv, state.pending_transformations
                        )
                        
                        # Save cleaned data to data store for persistence
                        cleaned_df = self.csv_processor._parse_csv_string(state.current_csv)
                        if cleaned_df is not None:
                            await self.data_store.save_dataframe(state.session_id, cleaned_df)
                            logger.info(f"Saved cleaned data to data store for session {state.session_id}")
                        
                        state.applied_transformations.extend(state.pending_transformations)
                        state.pending_transformations = []
                        
                        response_message = "Great! I've applied the changes to your data."
                    else:
                        response_message = "No changes were applied."
                else:
                    # Clear pending transformations
                    state.pending_transformations = []
                    response_message = "Understood. I won't make those changes."
                    
                    if request.user_feedback:
                        response_message += f" {request.user_feedback}"
                
                state.response = response_message
                state.updated_at = datetime.now()
                
                # Store updated state
                self.sessions[request.session_id] = state
                
                return CSVProcessingResponse(
                    success=True,
                    original_csv=state.original_csv,
                    cleaned_csv=state.current_csv,
                    changes_made=state.applied_transformations,
                    session_id=request.session_id,
                    conversation_active=True,
                    response_message=response_message
                )
            
        except Exception as e:
            logger.error(f"Error handling approval: {str(e)}")
            return CSVProcessingResponse(
                success=False,
                original_csv="",
                session_id=request.session_id,
                error_message=f"Approval handling failed: {str(e)}"
            )
    
    # Graph Node Functions
    
    async def _parse_csv_message(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Parse and validate the CSV message."""
        try:
            # Basic validation
            if not state["current_csv"].strip():
                state["response"] = "I need CSV data to work with. Please provide your data."
                return state
            
            logger.info(f"Parsed CSV message for session {state['session_id']}")
            return state
            
        except Exception as e:
            logger.error(f"Error parsing CSV message: {str(e)}")
            state["response"] = f"Error parsing message: {str(e)}"
            return state
    
    async def _classify_intent(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Classify user intent from message."""
        try:
            message = state["user_message"].lower().strip()
            
            # Intent classification with enhanced patterns
            if message in ["hi", "hello", "hey"]:
                state["intent"] = "greeting"
            elif any(word in message for word in ["yes", "apply", "fix it", "do it", "please apply", "go ahead"]):
                state["intent"] = "approval"
            elif any(word in message for word in ["clean", "fix", "improve", "transform", "remove duplicates", "fill missing"]):
                state["intent"] = "transform"
            elif any(word in message for word in ["no", "don't", "cancel", "reject", "skip"]):
                state["intent"] = "rejection"
            elif any(word in message for word in ["analyze", "check", "examine", "review", "show me"]):
                state["intent"] = "analyze"
            elif any(word in message for word in ["describe", "overview", "summary", "what's in"]):
                state["intent"] = "describe"
            elif any(phrase in message for phrase in ["add a new row", "add new row", "add a row", "add row", "insert row", "create row", "add entry", "add an entry"]):
                state["intent"] = "add_row"
            elif any(phrase in message for phrase in ["delete all rows", "delete the row", "delete row", "delete rows where", "remove all rows", "remove the row", "remove row", "remove rows where", "drop row", "drop rows", "delete entry", "remove entry", "delete by index", "delete by position"]):
                state["intent"] = "delete_row"
            else:
                state["intent"] = "analyze"  # Default to analysis
            
            logger.info(f"Classified intent: {state['intent']} for session {state['session_id']}")
            return state
            
        except Exception as e:
            logger.error(f"Error classifying intent: {str(e)}")
            state["intent"] = "response"
            return state
    
    async def _analyze_csv(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze CSV data quality."""
        try:
            # Check if there's cleaned data in the data store
            cleaned_df = await self.data_store.get_dataframe(state["session_id"])
            if cleaned_df is not None:
                # Use cleaned data for analysis
                csv_data = self.csv_processor._dataframe_to_csv_string(cleaned_df)
                logger.info(f"Using cleaned data from data store for analysis (session {state['session_id']})")
            else:
                # Try loading from database
                cleaned_csv_from_db = await self._load_cleaned_data_from_database(state["session_id"])
                if cleaned_csv_from_db:
                    csv_data = cleaned_csv_from_db
                    logger.info(f"Using cleaned data from database for analysis (session {state['session_id']})")
                else:
                    # Fall back to current CSV
                    csv_data = state["current_csv"]
                    logger.info(f"Using current CSV for analysis (session {state['session_id']})")
            
            analysis = await self.csv_processor.analyze_csv_quality(csv_data)
            
            # Update state with analysis results
            state["quality_issues"] = analysis.quality_issues
            state["confidence_score"] = analysis.confidence_score
            # Store any AI or rule-based suggestions from analysis for later use
            state["analysis_suggestions"] = getattr(analysis, "suggestions", [])
            
            logger.info(f"Analyzed CSV: {len(analysis.quality_issues)} issues found")
            return state
            
        except Exception as e:
            logger.error(f"Error analyzing CSV: {str(e)}")
            state["quality_issues"] = [f"Analysis failed: {str(e)}"]
            state["confidence_score"] = 0.0
            return state
    
    async def _generate_suggestions(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Generate transformation suggestions."""
        try:
            suggestions = []
            
            # Generate suggestions based on quality issues
            quality_issues = state.get("quality_issues", [])
            for issue in quality_issues:
                if "missing values" in issue.lower():
                    suggestions.append("Fill missing values")
                elif "duplicate" in issue.lower():
                    suggestions.append("Remove duplicate rows")
                elif "empty rows" in issue.lower():
                    suggestions.append("Remove empty rows")
                elif "inconsistent" in issue.lower() or "capitalization" in issue.lower() or "spelling" in issue.lower():
                    suggestions.append("Standardize categorical values")
                elif "outlier" in issue.lower():
                    suggestions.append("Handle outliers")
 
            # Merge in AI/analysis suggestions (if any) and deduplicate
            analysis_suggestions = state.get("analysis_suggestions", [])
            suggestions.extend(analysis_suggestions)

            # Deduplicate while preserving order
            seen = set()
            deduped = []
            for s in suggestions:
                if s not in seen:
                    deduped.append(s)
                    seen.add(s)

            # Store combined suggestions as pending transformations
            state["pending_transformations"] = deduped
            
            logger.info(f"Generated {len(suggestions)} suggestions for session {state['session_id']}")
            return state
            
        except Exception as e:
            logger.error(f"Error generating suggestions: {str(e)}")
            state["pending_transformations"] = []
            return state
    
    async def _request_approval(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Request user approval for transformations."""
        try:
            pending_transformations = state.get("pending_transformations", [])
            if pending_transformations:
                state["awaiting_approval"] = True
                
                response = "I suggest the following changes:\n"
                for i, transformation in enumerate(pending_transformations, 1):
                    response += f"{i}. {transformation}\n"
                response += "\nWould you like me to apply these changes?"
                
                state["response"] = response
            else:
                state["response"] = "No changes are needed for your data."
            
            logger.info(f"Requested approval for session {state['session_id']}")
            return state
            
        except Exception as e:
            logger.error(f"Error requesting approval: {str(e)}")
            state["response"] = f"Error requesting approval: {str(e)}"
            return state
    
    async def _apply_changes(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Apply approved transformations."""
        try:
            pending_transformations = state.get("pending_transformations", [])
            if pending_transformations:
                # Apply transformations
                state["current_csv"] = await self.csv_processor.apply_csv_transformations(
                    state["current_csv"], pending_transformations
                )
                
                # Save cleaned data to both data store and database for persistence
                cleaned_df = self.csv_processor._parse_csv_string(state["current_csv"])
                if cleaned_df is not None:
                    # Save to in-memory data store
                    await self.data_store.save_dataframe(state["session_id"], cleaned_df)
                    logger.info(f"Saved cleaned data to data store for session {state['session_id']}")
                    
                    # Save to database for persistent storage
                    try:
                        await self._save_cleaned_data_to_database(state["session_id"], state["current_csv"])
                        logger.info(f"Saved cleaned data to database for session {state['session_id']}")
                    except Exception as e:
                        logger.warning(f"Failed to save to database for session {state['session_id']}: {str(e)}")
                
                # Move to applied transformations
                applied = state.get("applied_transformations", [])
                applied.extend(pending_transformations)
                state["applied_transformations"] = applied
                state["pending_transformations"] = []
                
                state["response"] = "Changes have been applied to your data."
            else:
                state["response"] = "No changes to apply."
            
            logger.info(f"Applied changes for session {state['session_id']}")
            return state
            
        except Exception as e:
            logger.error(f"Error applying changes: {str(e)}")
            state["response"] = f"Error applying changes: {str(e)}"
            return state
    
    async def _compose_response(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Compose final response."""
        try:
            # If no response is set, generate one based on intent
            if not state.get("response"):
                if state.get("intent") == "greeting":
                    state["response"] = await self._generate_greeting_response(state)
                elif state.get("intent") == "analyze":
                    state["response"] = await self._generate_analysis_response(state)
                elif state.get("intent") == "describe":
                    state["response"] = await self._generate_description_response(state)
                elif state.get("intent") == "add_row":
                    state["response"] = "I've added a new row to your data."
                elif state.get("intent") == "delete_row":
                    state["response"] = "I've deleted a row from your data."
                else:
                    state["response"] = "I'm here to help with your data cleaning needs."
            
            logger.info(f"Composed response for session {state['session_id']}")
            return state
            
        except Exception as e:
            logger.error(f"Error composing response: {str(e)}")
            state["response"] = f"I encountered an error: {str(e)}"
            return state
    
    async def _handle_row_operations(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Handle row addition and deletion operations."""
        try:
            user_message = state["user_message"]
            session_id = state["session_id"]
            
            # Get current DataFrame
            cleaned_df = await self.data_store.get_dataframe(session_id)
            if cleaned_df is not None:
                current_df = cleaned_df
            else:
                current_df = self.csv_processor._parse_csv_string(state["current_csv"])
                
            if current_df is None:
                state["response"] = "I couldn't parse your CSV data. Please ensure it's properly formatted."
                return state
            
            # Use quality agent to detect and handle row operations
            if not self.quality_agent:
                state["response"] = "Row operations are not available - AI agent not configured."
                return state
            
            # Step 1: Detect if this is a row operation
            detection_result = await self.quality_agent.detect_row_operations(user_message, current_df)
            
            if not detection_result.get("operation_detected", False):
                state["response"] = "I couldn't detect a row operation in your message. Please be more specific about what you'd like to add or delete."
                return state
            
            operation_type = detection_result.get("operation_type", "none")
            
            if operation_type == "none":
                state["response"] = "I couldn't understand the specific row operation you want to perform."
                return state
            
            # Step 2: Parse operation details
            operation_details = await self.quality_agent.parse_row_operation_details(
                user_message, operation_type, current_df
            )
            
            if not operation_details.get("success", False):
                state["response"] = f"I couldn't parse the {operation_type} operation details. Please provide more specific information."
                return state
            
            # Step 3: Validate the operation
            validation_result = await self.quality_agent.validate_row_operation(
                operation_type, operation_details, current_df
            )
            
            if not validation_result.get("valid", False):
                error_msg = validation_result.get("error", "Unknown validation error")
                recommendations = validation_result.get("recommendations", [])
                
                # Build helpful error response with recommendations
                response_msg = f"I couldn't {operation_type.replace('_', ' ')} because: {error_msg}"
                
                if recommendations:
                    response_msg += "\n\n💡 Here are some suggestions:"
                    for i, rec in enumerate(recommendations[:3], 1):  # Show top 3 recommendations
                        response_msg += f"\n{i}. {rec}"
                
                state["response"] = response_msg
                return state
            
            # Step 4: Execute the operation
            execution_result = await self.quality_agent.execute_row_operation(
                operation_type, validation_result, current_df
            )
            
            if not execution_result.get("success", False):
                error_msg = execution_result.get("error", "Unknown execution error")
                state["response"] = f"Failed to execute {operation_type}: {error_msg}"
                return state
            
            # Step 5: Update state with modified data
            modified_df = execution_result.get("modified_df")
            if modified_df is not None:
                # Convert back to CSV string
                modified_csv = self.csv_processor._dataframe_to_csv_string(modified_df)
                state["current_csv"] = modified_csv
                
                # Save to data store
                await self.data_store.save_dataframe(session_id, modified_df)
                
                # Save to database for persistence
                try:
                    await self._save_cleaned_data_to_database(session_id, modified_csv)
                    logger.info(f"Saved row operation result to database for session {session_id}")
                except Exception as e:
                    logger.warning(f"Failed to save row operation result to database: {str(e)}")
                
                # Update transformation history
                changes_made = execution_result.get("changes_made", [])
                applied_transformations = state.get("applied_transformations", [])
                applied_transformations.extend(changes_made)
                state["applied_transformations"] = applied_transformations
                
                # Generate success response
                if operation_type == "add_row":
                    rows_added = execution_result.get("rows_added", 0)
                    new_shape = execution_result.get("new_shape", (0, 0))
                    state["response"] = f"✅ Successfully added {rows_added} row. Your dataset now has {new_shape[0]} rows and {new_shape[1]} columns."
                elif operation_type == "delete_row":
                    rows_deleted = execution_result.get("rows_deleted", 0)
                    new_shape = execution_result.get("new_shape", (0, 0))
                    state["response"] = f"✅ Successfully deleted {rows_deleted} row(s). Your dataset now has {new_shape[0]} rows and {new_shape[1]} columns."
                
                # Include change details
                if changes_made:
                    state["response"] += f"\n\n📝 Changes made: {'; '.join(changes_made)}"
                
                # Include helpful recommendations from validation
                recommendations = validation_result.get("recommendations", [])
                if recommendations:
                    state["response"] += f"\n\n💡 Notes:"
                    for rec in recommendations[:3]:  # Show top 3 recommendations
                        state["response"] += f"\n• {rec}"
                
                # Include warnings if any
                warnings = validation_result.get("warnings", [])
                if warnings:
                    state["response"] += f"\n\n⚠️ Warnings: {'; '.join(warnings)}"
                
            else:
                state["response"] = f"The {operation_type} operation completed but no data was modified."
            
            logger.info(f"Handled {operation_type} operation for session {session_id}")
            return state
            
        except Exception as e:
            logger.error(f"Error handling row operations: {str(e)}")
            state["response"] = f"I encountered an error while handling the row operation: {str(e)}"
            return state

    # Routing Functions
    
    def _route_after_intent(self, state: Dict[str, Any]) -> str:
        """Route after intent classification."""
        intent = state.get("intent", "")
        if intent == "approval":
            return "approval"
        elif intent == "transform":
            return "analyze"  # Analyze first, then suggest transformations
        elif intent in ["analyze", "describe"]:
            return "analyze"
        elif intent == "greeting":
            return "response"  # Greetings should go directly to response
        elif intent == "rejection":
            return "response"
        elif intent in ["add_row", "delete_row"]:
            return "row_operations"
        else:
            return "response"
    
    def _route_after_suggestions(self, state: Dict[str, Any]) -> str:
        """
        Decide what happens after we have generated suggestions.

        * transform   + suggestions  -> apply directly
        * greeting    + suggestions  -> ask for approval (legacy behaviour)
        * analyze     + suggestions  -> just report findings (NO approval yet)
        * anything else              -> direct response
        """
        pending = state.get("pending_transformations", [])
        intent = state.get("intent", "")

        # User explicitly asked to transform/clean → apply immediately
        if intent == "transform" and pending:
            return "apply_directly"

        # For a greeting (first-time help) we still ask for approval
        if intent == "greeting" and pending:
            return "approval_needed"

        # For pure analysis, show results but don't enter approval
        if intent == "analyze":
            return "direct_response"

        # For describe intent, show results but don't enter approval
        if intent == "describe":
            return "direct_response"

        # Default fall-through
        return "direct_response"
    
    # Helper Functions
    
    def _get_or_create_state(self, request: CSVMessageRequest) -> Dict[str, Any]:
        """Get or create conversation state as dictionary for LangGraph."""
        if request.session_id in self.sessions:
            # Convert existing Pydantic state to dict and update
            existing_state = self.sessions[request.session_id]
            
            # Handle both Pydantic models and dictionaries
            if isinstance(existing_state, dict):
                # It's already a dictionary
                state = existing_state.copy()
                state["user_message"] = request.user_message
                # Clear previous response to allow new response generation
                state["response"] = ""
            else:
                # It's a Pydantic model
                state = {
                    "session_id": existing_state.session_id,
                    "user_id": existing_state.user_id,
                    "original_csv": existing_state.original_csv,
                    "current_csv": existing_state.current_csv,  # Keep existing CSV if not updating
                    "user_message": request.user_message,
                    "intent": getattr(existing_state, 'intent', ''),
                    "response": getattr(existing_state, 'response', ''),
                    "quality_issues": existing_state.quality_issues,
                    "pending_transformations": existing_state.pending_transformations,
                    "awaiting_approval": existing_state.awaiting_approval,
                    "applied_transformations": existing_state.applied_transformations,
                    "confidence_score": existing_state.confidence_score
                }
        else:
            # Create new state as dictionary
            state = {
                "session_id": request.session_id,
                "user_id": request.user_id,
                "original_csv": request.csv_data,
                "current_csv": request.csv_data,
                "user_message": request.user_message,
                "intent": "",
                "response": "",
                "quality_issues": [],
                "pending_transformations": [],
                "awaiting_approval": False,
                "applied_transformations": [],
                "confidence_score": 0.0
            }
        
        return state
    
    def _state_to_response(self, state: Dict[str, Any]) -> CSVProcessingResponse:
        """Convert conversation state dictionary to response."""
        # Store state as dictionary for consistency
        self.sessions[state["session_id"]] = state.copy()
        
        # Use cleaned data from data store if available
        cleaned_csv = state["current_csv"]
        if state.get("applied_transformations"):
            # If transformations were applied, the cleaned data should be in the data store
            # For now, we'll use the current_csv which should contain the cleaned data
            cleaned_csv = state["current_csv"]
        
        return CSVProcessingResponse(
            success=True,
            original_csv=state["original_csv"],
            cleaned_csv=cleaned_csv,
            changes_made=state.get("applied_transformations", []),
            suggestions=state.get("pending_transformations", []),
            requires_approval=state.get("awaiting_approval", False),
            confidence_score=state.get("confidence_score", 0.0),
            session_id=state["session_id"],
            conversation_active=True,
            response_message=state.get("response"),
            intent=state.get("intent"),
            pending_transformations=state.get("pending_transformations", [])
        )
    
    async def _generate_greeting_response(self, state: Dict[str, Any]) -> str:
        """Generate greeting response with basic data overview."""
        try:
            # Check if there's cleaned data in the data store
            cleaned_df = await self.data_store.get_dataframe(state["session_id"])
            if cleaned_df is not None:
                df = cleaned_df
                data_status = "cleaned"
            else:
                df = self.csv_processor._parse_csv_string(state["current_csv"])
                data_status = "original"
                
            if df is not None:
                rows, cols = len(df), len(df.columns)
                response = f"Hello! I can see you have a dataset with {rows} rows and {cols} columns."
                
                if data_status == "cleaned":
                    response += " (This is your cleaned data.)"
                
                response += "\n\nI'm ready to help you with:"
                response += "\n• Data quality analysis"
                response += "\n• Cleaning and fixing issues"
                response += "\n• Removing duplicates"
                response += "\n• Handling missing values"
                response += "\n• Data transformation"
                response += "\n\nWhat would you like to do with your data?"
                return response
            else:
                return "Hello! I'd be happy to help you clean your data. Please make sure your CSV data is properly formatted."
                
        except Exception as e:
            return f"Hello! I'm here to help with data cleaning. I encountered an error reading your data: {str(e)}"
    
    async def _generate_analysis_response(self, state: Dict[str, Any]) -> str:
        """Generate analysis response without entering approval flow."""
        try:
            quality_issues = state.get("quality_issues", [])
            pending_transformations = state.get("pending_transformations", [])

            if quality_issues:
                response = f"I've analyzed your data and found {len(quality_issues)} issues:\n"
                for issue in quality_issues:
                    response += f"• {issue}\n"

                # Show top 3 suggestions (if any) so the user can decide next steps
                if pending_transformations:
                    response += "\nHere are some potential fixes you might consider:\n"
                    for suggestion in pending_transformations[:3]:
                        response += f"- {suggestion}\n"

                return response
            else:
                return "Your data looks good! I didn't find any significant quality issues."

        except Exception as e:
            return f"I encountered an error during analysis: {str(e)}"
    
    async def _generate_description_response(self, state: Dict[str, Any]) -> str:
        """Generate data overview description with semantic understanding."""
        try:
            # Check if there's cleaned data in the data store
            cleaned_df = await self.data_store.get_dataframe(state["session_id"])
            if cleaned_df is not None:
                df = cleaned_df
                data_status = "cleaned"
            else:
                df = self.csv_processor._parse_csv_string(state["current_csv"])
                data_status = "original"
                
            if df is None:
                return "I couldn't parse your CSV data. Please ensure it's properly formatted."

            rows, cols = len(df), len(df.columns)
            response = f"Your dataset has {rows} rows and {cols} columns."
            
            if data_status == "cleaned":
                response += " (This is your cleaned data.)"

            # Add semantic understanding if quality agent is available
            if self.quality_agent:
                try:
                    semantic_analysis = await self.quality_agent.understand_data_semantics(df)
                    
                    if semantic_analysis and semantic_analysis.get("success"):
                        data_understanding = semantic_analysis.get("data_understanding", "")
                        research_domain = semantic_analysis.get("research_domain", "")
                        
                        if data_understanding:
                            response += f"\n\n🔬 **Data Understanding**: {data_understanding}"
                        
                        if research_domain and research_domain != "General":
                            response += f"\n📊 **Research Domain**: {research_domain}"
                        
                        experimental_design = semantic_analysis.get("experimental_design", "")
                        if experimental_design and experimental_design != "Could not determine":
                            response += f"\n🧪 **Experimental Design**: {experimental_design}"
                        
                        key_variables = semantic_analysis.get("key_variables", [])
                        if key_variables:
                            response += f"\n🔑 **Key Variables**: {len(key_variables)} variables identified"
                            for var in key_variables[:3]:  # Show first 3 variables
                                response += f"\n   • {var.get('name', 'Unknown')}: {var.get('description', 'No description')}"
                
                except Exception as e:
                    logger.warning(f"Semantic analysis failed: {str(e)}")

            quality_issues = state.get("quality_issues", [])
            if quality_issues:
                response += f"\n\nI've also detected {len(quality_issues)} potential quality issues (not shown in detail here). You can ask me to *analyze the data* for a full list."

            return response
        except Exception as e:
            return f"I encountered an error describing your data: {str(e)}"
    
    async def _save_cleaned_data_to_database(self, session_id: str, cleaned_csv: str) -> bool:
        """Save cleaned CSV data to database via HTTP API."""
        try:
            import httpx
            
            # Use httpx to call our own API endpoint
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://localhost:8000/api/dataclean/csv-conversation/save-cleaned-data",
                    params={"session_id": session_id},
                    json={"cleaned_csv": cleaned_csv}
                )
                
                if response.status_code == 200:
                    return True
                else:
                    logger.error(f"Database save failed: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error saving to database: {str(e)}")
            return False
    
    async def _load_cleaned_data_from_database(self, session_id: str) -> Optional[str]:
        """Load cleaned CSV data from database via HTTP API."""
        try:
            import httpx
            
            # Use httpx to call our own API endpoint
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"http://localhost:8000/api/dataclean/csv-conversation/get-cleaned-data/{session_id}"
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("cleaned_csv")
                else:
                    logger.info(f"No cleaned data in database for session {session_id}")
                    return None
                    
        except Exception as e:
            logger.info(f"Could not load from database for session {session_id}: {str(e)}")
            return None
    
    def get_session_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session summary."""
        if session_id in self.sessions:
            state = self.sessions[session_id]
            
            # Handle both dictionary and Pydantic model states
            if isinstance(state, dict):
                return {
                    "session_id": session_id,
                    "user_id": state.get("user_id", "unknown"),
                    "conversation_active": True,
                    "awaiting_approval": state.get("awaiting_approval", False),
                    "applied_transformations": len(state.get("applied_transformations", [])),
                    "pending_transformations": len(state.get("pending_transformations", [])),
                    "quality_issues": len(state.get("quality_issues", [])),
                    "confidence_score": state.get("confidence_score", 0.0),
                    "last_updated": datetime.now().isoformat()  # Use current time for dict states
                }
            else:
                # Legacy Pydantic model handling
                return {
                    "session_id": session_id,
                    "user_id": state.user_id,
                    "conversation_active": True,
                    "awaiting_approval": state.awaiting_approval,
                    "applied_transformations": len(state.applied_transformations),
                    "pending_transformations": len(state.pending_transformations),
                    "quality_issues": len(state.quality_issues),
                    "confidence_score": state.confidence_score,
                    "last_updated": state.updated_at.isoformat()
                }
        return None 