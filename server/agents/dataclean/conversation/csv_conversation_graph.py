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
            analysis = await self.csv_processor.analyze_csv_quality(state["current_csv"])
            
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
                else:
                    state["response"] = "I'm here to help with your data cleaning needs."
            
            logger.info(f"Composed response for session {state['session_id']}")
            return state
            
        except Exception as e:
            logger.error(f"Error composing response: {str(e)}")
            state["response"] = f"I encountered an error: {str(e)}"
            return state
    
    # Routing Functions
    
    def _route_after_intent(self, state: Dict[str, Any]) -> str:
        """Route after intent classification."""
        intent = state.get("intent", "")
        if intent == "approval":
            return "approval"
        elif intent == "transform":
            return "analyze"  # Analyze first, then suggest transformations
        elif intent in ["greeting", "analyze", "describe"]:
            return "analyze"
        elif intent == "rejection":
            return "response"
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
        
        return CSVProcessingResponse(
            success=True,
            original_csv=state["original_csv"],
            cleaned_csv=state["current_csv"],
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
        """Generate greeting response with data overview."""
        try:
            # Parse CSV for basic info
            df = self.csv_processor._parse_csv_string(state["current_csv"])
            if df is not None:
                rows, cols = len(df), len(df.columns)
                response = f"Hello! I can see you have a dataset with {rows} rows and {cols} columns."
                
                quality_issues = state.get("quality_issues", [])
                if quality_issues:
                    response += f"\n\nI've identified {len(quality_issues)} potential issues:"
                    for issue in quality_issues[:3]:
                        response += f"\n• {issue}"
                
                response += "\n\nWhat would you like to do with your data?"
                return response
            else:
                return "Hello! I'd be happy to help you clean your data. Please make sure your CSV data is properly formatted."
                
        except Exception as e:
            return f"Hello! I encountered an error analyzing your data: {str(e)}"
    
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
        """Generate data overview description (rows, columns, sample issues)."""
        try:
            df = self.csv_processor._parse_csv_string(state["current_csv"])
            if df is None:
                return "I couldn't parse your CSV data. Please ensure it's properly formatted."

            rows, cols = len(df), len(df.columns)
            response = f"Your dataset has {rows} rows and {cols} columns."

            quality_issues = state.get("quality_issues", [])
            if quality_issues:
                response += f"\n\nI've also detected {len(quality_issues)} potential quality issues (not shown in detail here). You can ask me to *analyze the data* for a full list."

            return response
        except Exception as e:
            return f"I encountered an error describing your data: {str(e)}"
    
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