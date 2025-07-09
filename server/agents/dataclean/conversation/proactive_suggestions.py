"""
Proactive Suggestions & Next-Step Recommendations

This module generates context-aware suggestions and next steps to guide users
through their data cleaning workflow based on current conversation state and data context.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from .state_schema import ConversationState, Intent, FileFormat

logger = logging.getLogger(__name__)


class ProactiveSuggestionsEngine:
    """
    Generate proactive suggestions and next-step recommendations based on conversation context.
    """
    
    def __init__(self):
        """Initialize the proactive suggestions engine."""
        self.suggestion_templates = self._load_suggestion_templates()
    
    async def generate_proactive_suggestions(
        self, 
        state: ConversationState
    ) -> List[Dict[str, Any]]:
        """
        Generate proactive suggestions based on current conversation state.
        
        Args:
            state: Current conversation state
            
        Returns:
            List of suggestion dictionaries with text, action, and priority
        """
        try:
            suggestions = []
            
            # Analyze current context
            context_analysis = await self._analyze_conversation_context(state)
            
            # Generate suggestions based on different contexts
            suggestions.extend(await self._generate_data_state_suggestions(state, context_analysis))
            suggestions.extend(await self._generate_workflow_suggestions(state, context_analysis))
            suggestions.extend(await self._generate_quality_suggestions(state, context_analysis))
            suggestions.extend(await self._generate_next_step_suggestions(state, context_analysis))
            
            # Sort by priority and return top suggestions
            suggestions.sort(key=lambda x: x.get("priority", 5), reverse=True)
            return suggestions[:3]  # Return top 3 suggestions
            
        except Exception as e:
            logger.error(f"Error generating proactive suggestions: {str(e)}")
            return []
    
    async def generate_next_steps(
        self, 
        state: ConversationState
    ) -> List[str]:
        """
        Generate recommended next steps based on current state.
        
        Args:
            state: Current conversation state
            
        Returns:
            List of next step recommendations
        """
        try:
            intent = state.get("intent", Intent.UNKNOWN)
            operation_result = state.get("operation_result", {})
            data_context = state.get("data_context")
            
            next_steps = []
            
            # Next steps based on current intent and result
            if intent == Intent.SHOW_DATA and operation_result.get("status") == "success":
                next_steps.extend([
                    "Ask me to analyze data quality issues",
                    "Request a description of your data structure",
                    "Try cleaning specific columns or data issues"
                ])
            
            elif intent == Intent.ANALYZE and operation_result.get("status") == "success":
                issues_found = operation_result.get("issues_found", 0)
                if issues_found > 0:
                    next_steps.extend([
                        "Apply the suggested data cleaning operations",
                        "Ask for specific cleaning recommendations",
                        "Review individual data quality issues"
                    ])
                else:
                    next_steps.extend([
                        "Your data looks good! Try exploring specific columns",
                        "Export your clean data",
                        "Ask for data summary statistics"
                    ])
            
            elif intent == Intent.CLEAN and operation_result.get("status") == "confirmation_required":
                next_steps.extend([
                    "Confirm the cleaning operation with 'yes'",
                    "Cancel the operation with 'no'",
                    "Ask for more details about what will be changed"
                ])
            
            elif not data_context:
                next_steps.extend([
                    "Upload a CSV or Excel file to get started",
                    "Ask me what I can help you with",
                    "Try asking 'What can you do?'"
                ])
            
            # Add context-specific next steps
            if state.get("file_format") == FileFormat.EXCEL:
                sheet_name = state.get("sheet_name")
                if not sheet_name:
                    next_steps.append("Select which Excel sheet to work with")
            
            return next_steps[:4]  # Return top 4 next steps
            
        except Exception as e:
            logger.error(f"Error generating next steps: {str(e)}")
            return ["Ask me what I can help you with"]
    
    async def _analyze_conversation_context(
        self, 
        state: ConversationState
    ) -> Dict[str, Any]:
        """
        Analyze the current conversation context to understand user's workflow state.
        
        Args:
            state: Current conversation state
            
        Returns:
            Dictionary with context analysis
        """
        analysis = {
            "has_data": bool(state.get("data_context")),
            "data_shape": None,
            "recent_intent": state.get("intent", Intent.UNKNOWN),
            "conversation_length": len(state.get("conversation_history", [])),
            "errors_occurred": bool(state.get("error_message")),
            "confirmation_pending": state.get("confirmation_required", False),
            "file_format": state.get("file_format"),
            "workflow_stage": "initial"
        }
        
        # Determine workflow stage
        if not analysis["has_data"]:
            analysis["workflow_stage"] = "data_loading"
        elif state.get("intent") in [Intent.SHOW_DATA, Intent.DESCRIBE]:
            analysis["workflow_stage"] = "data_exploration"
        elif state.get("intent") == Intent.ANALYZE:
            analysis["workflow_stage"] = "quality_analysis"
        elif state.get("intent") in [Intent.CLEAN, Intent.REMOVE, Intent.CONVERT]:
            analysis["workflow_stage"] = "data_cleaning"
        elif state.get("intent") == Intent.SAVE:
            analysis["workflow_stage"] = "completion"
        
        # Add data shape if available
        dataframe_info = state.get("dataframe_info", {})
        if dataframe_info.get("shape"):
            analysis["data_shape"] = dataframe_info["shape"]
        
        return analysis
    
    async def _generate_data_state_suggestions(
        self, 
        state: ConversationState, 
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate suggestions based on current data state."""
        suggestions = []
        
        if not context["has_data"]:
            suggestions.append({
                "text": "Upload a CSV or Excel file to start analyzing your data",
                "action": "upload_file",
                "priority": 10,
                "category": "data_loading"
            })
        
        elif context["workflow_stage"] == "data_exploration":
            dataframe_info = state.get("dataframe_info", {})
            if dataframe_info.get("shape"):
                rows, cols = dataframe_info["shape"]
                if rows > 1000:
                    suggestions.append({
                        "text": f"Your dataset has {rows:,} rows - consider analyzing data quality for potential issues",
                        "action": "analyze_quality",
                        "priority": 8,
                        "category": "quality_check"
                    })
        
        return suggestions
    
    async def _generate_workflow_suggestions(
        self, 
        state: ConversationState, 
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate suggestions based on current workflow stage."""
        suggestions = []
        
        stage = context["workflow_stage"]
        
        if stage == "data_exploration" and not context["errors_occurred"]:
            suggestions.append({
                "text": "Run a data quality analysis to identify potential issues",
                "action": "analyze_data",
                "priority": 7,
                "category": "workflow_progression"
            })
        
        elif stage == "quality_analysis":
            operation_result = state.get("operation_result", {})
            issues_found = operation_result.get("issues_found", 0)
            
            if issues_found > 0:
                suggestions.append({
                    "text": f"Found {issues_found} data quality issues - try applying the suggested fixes",
                    "action": "apply_suggestions",
                    "priority": 9,
                    "category": "workflow_progression"
                })
            else:
                suggestions.append({
                    "text": "Your data looks clean! Consider exporting it or exploring specific columns",
                    "action": "export_or_explore",
                    "priority": 6,
                    "category": "workflow_progression"
                })
        
        return suggestions
    
    async def _generate_quality_suggestions(
        self, 
        state: ConversationState, 
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate suggestions based on data quality context."""
        suggestions = []
        
        operation_result = state.get("operation_result", {})
        
        # Check if we have quality analysis results
        if "quality_issues" in operation_result:
            quality_issues = operation_result["quality_issues"]
            
            # Suggest specific improvements based on issue types
            issue_types = [issue.get("issue_type") for issue in quality_issues]
            
            if "missing_values" in issue_types:
                suggestions.append({
                    "text": "I found missing values - would you like me to suggest how to handle them?",
                    "action": "handle_missing_values",
                    "priority": 8,
                    "category": "data_quality"
                })
            
            if "data_type_issues" in issue_types:
                suggestions.append({
                    "text": "Some columns have data type issues - I can help convert them to the right types",
                    "action": "fix_data_types",
                    "priority": 7,
                    "category": "data_quality"
                })
        
        return suggestions
    
    async def _generate_next_step_suggestions(
        self, 
        state: ConversationState, 
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate general next step suggestions."""
        suggestions = []
        
        # File format specific suggestions
        if context["file_format"] == FileFormat.EXCEL:
            if not state.get("sheet_name"):
                suggestions.append({
                    "text": "Select which Excel sheet you'd like to work with",
                    "action": "select_sheet",
                    "priority": 9,
                    "category": "file_handling"
                })
        
        elif context["file_format"] == FileFormat.CSV:
            if not state.get("delimiter"):
                suggestions.append({
                    "text": "I can detect the CSV delimiter if you're having issues",
                    "action": "detect_delimiter",
                    "priority": 6,
                    "category": "file_handling"
                })
        
        # Conversation length based suggestions
        if context["conversation_length"] > 10:
            suggestions.append({
                "text": "We've been chatting for a while - would you like a summary of what we've accomplished?",
                "action": "conversation_summary",
                "priority": 5,
                "category": "conversation_management"
            })
        
        return suggestions
    
    def _load_suggestion_templates(self) -> Dict[str, Any]:
        """Load suggestion templates for different contexts."""
        return {
            "data_loading": [
                "Upload a file to get started with data analysis",
                "Try asking 'What can you help me with?'"
            ],
            "data_exploration": [
                "Analyze your data quality to identify issues",
                "Ask me to describe your data structure",
                "Show more rows of your data"
            ],
            "quality_analysis": [
                "Apply the suggested data cleaning operations",
                "Ask for specific cleaning recommendations",
                "Review individual data quality issues"
            ],
            "data_cleaning": [
                "Confirm the proposed changes",
                "Ask for a preview before applying changes",
                "Try cleaning other columns"
            ],
            "completion": [
                "Export your cleaned data",
                "Save your current progress",
                "Start working on another dataset"
            ]
        }


# Global instance
_proactive_engine = None

def get_proactive_suggestions_engine() -> ProactiveSuggestionsEngine:
    """Get the global proactive suggestions engine instance."""
    global _proactive_engine
    if _proactive_engine is None:
        _proactive_engine = ProactiveSuggestionsEngine()
    return _proactive_engine 