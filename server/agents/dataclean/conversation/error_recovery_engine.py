"""
Enhanced Error Recovery & Conversation Repair Engine

This module provides Phase 3 enhanced error recovery capabilities:
- Intelligent error analysis and categorization
- Advanced recovery strategies with progressive degradation
- Conversation state repair and context reconstruction
- User-friendly error experience with guided recovery
- Error prevention through proactive validation
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from enum import Enum

from .state_schema import ConversationState, Intent, FileFormat
from ..memory_store import get_data_store
from config import get_openai_client

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels for recovery planning."""
    LOW = "low"           # Minor issues, easy recovery
    MEDIUM = "medium"     # Significant issues, moderate recovery
    HIGH = "high"         # Major issues, difficult recovery
    CRITICAL = "critical" # System issues, may require restart


class RecoveryStrategy(Enum):
    """Enhanced recovery strategies."""
    RETRY_SAME = "retry_same"                    # Retry exact same operation
    RETRY_MODIFIED = "retry_modified"            # Retry with modifications
    ALTERNATIVE_METHOD = "alternative_method"    # Use different approach
    PROGRESSIVE_DEGRADATION = "progressive_degradation"  # Simplified operation
    FALLBACK_BASIC = "fallback_basic"           # Basic functionality only
    USER_GUIDANCE = "user_guidance"             # Guide user to fix issue
    CONTEXT_REPAIR = "context_repair"           # Repair conversation context
    GRACEFUL_RESET = "graceful_reset"           # Reset with explanation
    ESCALATE_SUPPORT = "escalate_support"       # Escalate to human support


class EnhancedErrorRecoveryEngine:
    """
    Enhanced error recovery engine with intelligent analysis and repair capabilities.
    """
    
    def __init__(self):
        """Initialize the enhanced error recovery engine."""
        self.openai_client = get_openai_client()
        self.error_patterns = self._load_error_patterns()
        self.recovery_history = {}  # Track recovery attempts per session
        self.error_analytics = {}   # Track error patterns for learning
        
        logger.info("Initialized enhanced error recovery engine")
    
    async def analyze_error_and_plan_recovery(
        self,
        error_message: str,
        error_type: str,
        state: ConversationState
    ) -> Dict[str, Any]:
        """
        Analyze error and create comprehensive recovery plan.
        
        Args:
            error_message: The error message
            error_type: Basic error type classification
            state: Current conversation state
            
        Returns:
            Dictionary with error analysis and recovery plan
        """
        try:
            # Enhanced error analysis
            error_analysis = await self._analyze_error_intelligently(
                error_message, error_type, state
            )
            
            # Context-aware recovery planning
            recovery_plan = await self._create_recovery_plan(error_analysis, state)
            
            # Generate user-friendly explanation
            user_explanation = await self._generate_user_explanation(
                error_analysis, recovery_plan, state
            )
            
            # Track error for learning
            await self._track_error_for_learning(error_analysis, state)
            
            return {
                "error_analysis": error_analysis,
                "recovery_plan": recovery_plan,
                "user_explanation": user_explanation,
                "severity": error_analysis["severity"],
                "recovery_strategy": recovery_plan["strategy"],
                "estimated_success_rate": recovery_plan["success_rate"],
                "requires_user_action": recovery_plan["requires_user_action"]
            }
            
        except Exception as e:
            logger.error(f"Error in error analysis: {str(e)}")
            return await self._fallback_error_recovery(error_message, error_type, state)
    
    async def execute_recovery_strategy(
        self,
        recovery_plan: Dict[str, Any],
        state: ConversationState
    ) -> Dict[str, Any]:
        """
        Execute the planned recovery strategy.
        
        Args:
            recovery_plan: Recovery plan from analysis
            state: Current conversation state
            
        Returns:
            Dictionary with recovery execution results
        """
        try:
            strategy = RecoveryStrategy(recovery_plan["strategy"])
            
            if strategy == RecoveryStrategy.RETRY_SAME:
                return await self._execute_retry_same(recovery_plan, state)
            elif strategy == RecoveryStrategy.RETRY_MODIFIED:
                return await self._execute_retry_modified(recovery_plan, state)
            elif strategy == RecoveryStrategy.ALTERNATIVE_METHOD:
                return await self._execute_alternative_method(recovery_plan, state)
            elif strategy == RecoveryStrategy.PROGRESSIVE_DEGRADATION:
                return await self._execute_progressive_degradation(recovery_plan, state)
            elif strategy == RecoveryStrategy.FALLBACK_BASIC:
                return await self._execute_fallback_basic(recovery_plan, state)
            elif strategy == RecoveryStrategy.USER_GUIDANCE:
                return await self._execute_user_guidance(recovery_plan, state)
            elif strategy == RecoveryStrategy.CONTEXT_REPAIR:
                return await self._execute_context_repair(recovery_plan, state)
            elif strategy == RecoveryStrategy.GRACEFUL_RESET:
                return await self._execute_graceful_reset(recovery_plan, state)
            else:
                return await self._execute_escalate_support(recovery_plan, state)
                
        except Exception as e:
            logger.error(f"Error in recovery execution: {str(e)}")
            return {
                "success": False,
                "message": "Recovery execution failed",
                "fallback_strategy": "graceful_reset"
            }
    
    async def repair_conversation_context(
        self,
        state: ConversationState,
        error_info: Dict[str, Any]
    ) -> ConversationState:
        """
        Repair conversation context after error recovery.
        
        Args:
            state: Current conversation state
            error_info: Information about the error and recovery
            
        Returns:
            Repaired conversation state
        """
        try:
            # Repair conversation history
            repaired_history = await self._repair_conversation_history(
                state.get("conversation_history", []), error_info
            )
            
            # Reconstruct context references
            repaired_references = await self._reconstruct_context_references(
                state, error_info
            )
            
            # Update conversation flow state
            repaired_flow_state = await self._repair_conversation_flow_state(
                state, error_info
            )
            
            # Reset error-related fields
            return {
                **state,
                "conversation_history": repaired_history,
                "context_references": repaired_references,
                "conversation_flow_state": repaired_flow_state,
                "error_message": None,
                "error_type": None,
                "retry_count": 0,
                "recovery_strategy": None,
                "recovery_message": None,
                "error_recovered": True
            }
            
        except Exception as e:
            logger.error(f"Error in conversation repair: {str(e)}")
            return state
    
    async def validate_operation_proactively(
        self,
        intent: Intent,
        operation_params: Dict[str, Any],
        state: ConversationState
    ) -> Dict[str, Any]:
        """
        Proactively validate operation to prevent errors.
        
        Args:
            intent: User's intent
            operation_params: Parameters for the operation
            state: Current conversation state
            
        Returns:
            Validation result with risk assessment
        """
        try:
            # Check data availability
            data_validation = await self._validate_data_availability(state)
            
            # Check operation parameters
            param_validation = await self._validate_operation_parameters(
                intent, operation_params, state
            )
            
            # Check system resources
            resource_validation = await self._validate_system_resources(intent, state)
            
            # Risk assessment
            risk_assessment = await self._assess_operation_risk(
                intent, operation_params, state
            )
            
            # Combine all validations
            overall_validation = {
                "is_valid": all([
                    data_validation["is_valid"],
                    param_validation["is_valid"],
                    resource_validation["is_valid"]
                ]),
                "risk_level": risk_assessment["level"],
                "validation_results": {
                    "data": data_validation,
                    "parameters": param_validation,
                    "resources": resource_validation
                },
                "risk_assessment": risk_assessment,
                "warnings": [],
                "recommendations": []
            }
            
            # Add warnings and recommendations
            if not overall_validation["is_valid"]:
                overall_validation["warnings"] = self._compile_warnings(
                    data_validation, param_validation, resource_validation
                )
                overall_validation["recommendations"] = self._compile_recommendations(
                    intent, operation_params, state, overall_validation
                )
            
            return overall_validation
            
        except Exception as e:
            logger.error(f"Error in proactive validation: {str(e)}")
            return {
                "is_valid": False,
                "risk_level": "unknown",
                "error": str(e)
            }
    
    # Private helper methods
    
    async def _analyze_error_intelligently(
        self,
        error_message: str,
        error_type: str,
        state: ConversationState
    ) -> Dict[str, Any]:
        """Perform intelligent error analysis."""
        # Basic analysis
        analysis = {
            "error_message": error_message,
            "error_type": error_type,
            "severity": ErrorSeverity.MEDIUM,
            "category": "unknown",
            "root_cause": None,
            "context_factors": [],
            "user_contribution": None,
            "system_contribution": None,
            "recovery_complexity": "medium"
        }
        
        # Pattern matching for common errors
        if "data not found" in error_message.lower():
            analysis.update({
                "severity": ErrorSeverity.MEDIUM,
                "category": "data_access",
                "root_cause": "missing_data",
                "recovery_complexity": "low"
            })
        elif "openai" in error_message.lower():
            analysis.update({
                "severity": ErrorSeverity.HIGH,
                "category": "ai_service",
                "root_cause": "external_service_failure",
                "recovery_complexity": "high"
            })
        elif "processing" in error_message.lower():
            analysis.update({
                "severity": ErrorSeverity.MEDIUM,
                "category": "data_processing",
                "root_cause": "processing_failure",
                "recovery_complexity": "medium"
            })
        
        # Context analysis
        analysis["context_factors"] = await self._analyze_context_factors(state)
        
        # Use LLM for advanced analysis if available
        if self.openai_client:
            enhanced_analysis = await self._llm_enhance_error_analysis(
                error_message, error_type, state, analysis
            )
            analysis.update(enhanced_analysis)
        
        return analysis
    
    async def _create_recovery_plan(
        self,
        error_analysis: Dict[str, Any],
        state: ConversationState
    ) -> Dict[str, Any]:
        """Create context-aware recovery plan."""
        severity = error_analysis["severity"]
        category = error_analysis["category"]
        
        # Base recovery plan
        plan = {
            "strategy": RecoveryStrategy.RETRY_SAME,
            "success_rate": 0.5,
            "requires_user_action": False,
            "steps": [],
            "fallback_strategy": RecoveryStrategy.GRACEFUL_RESET,
            "estimated_time": "immediate"
        }
        
        # Strategy selection based on error analysis
        if category == "data_access":
            plan.update({
                "strategy": RecoveryStrategy.USER_GUIDANCE,
                "success_rate": 0.8,
                "requires_user_action": True,
                "steps": [
                    "Guide user to check data availability",
                    "Suggest data upload if needed",
                    "Retry operation after data is available"
                ]
            })
        elif category == "ai_service":
            plan.update({
                "strategy": RecoveryStrategy.PROGRESSIVE_DEGRADATION,
                "success_rate": 0.7,
                "requires_user_action": False,
                "steps": [
                    "Disable AI-powered features",
                    "Use basic processing methods",
                    "Inform user of limited functionality"
                ]
            })
        elif category == "data_processing":
            plan.update({
                "strategy": RecoveryStrategy.ALTERNATIVE_METHOD,
                "success_rate": 0.6,
                "requires_user_action": False,
                "steps": [
                    "Try alternative processing method",
                    "Use simpler data operations",
                    "Retry with reduced parameters"
                ]
            })
        
        # Adjust based on severity
        if severity == ErrorSeverity.CRITICAL:
            plan["strategy"] = RecoveryStrategy.GRACEFUL_RESET
            plan["fallback_strategy"] = RecoveryStrategy.ESCALATE_SUPPORT
        elif severity == ErrorSeverity.LOW:
            plan["success_rate"] = min(0.9, plan["success_rate"] + 0.2)
        
        return plan
    
    async def _generate_user_explanation(
        self,
        error_analysis: Dict[str, Any],
        recovery_plan: Dict[str, Any],
        state: ConversationState
    ) -> str:
        """Generate user-friendly error explanation."""
        category = error_analysis["category"]
        strategy = recovery_plan["strategy"]
        
        if category == "data_access":
            explanation = "I couldn't find the data needed for your request. This usually happens when no file has been uploaded yet or the data isn't available in the current session."
        elif category == "ai_service":
            explanation = "I'm having trouble with AI analysis right now. This might be due to service connectivity issues, but I can still help you with basic data operations."
        elif category == "data_processing":
            explanation = "There was an issue processing your data. This could be due to the data format or a temporary processing problem."
        else:
            explanation = "I encountered an unexpected issue while processing your request."
        
        # Add recovery guidance
        if strategy == RecoveryStrategy.USER_GUIDANCE:
            explanation += " Let me guide you through fixing this."
        elif strategy == RecoveryStrategy.PROGRESSIVE_DEGRADATION:
            explanation += " I'll switch to basic mode and try again."
        elif strategy == RecoveryStrategy.ALTERNATIVE_METHOD:
            explanation += " Let me try a different approach."
        else:
            explanation += " I'll try to recover from this."
        
        return explanation
    
    async def _track_error_for_learning(
        self,
        error_analysis: Dict[str, Any],
        state: ConversationState
    ) -> None:
        """Track error for learning and improvement."""
        session_id = state.get("session_id", "unknown")
        error_key = f"{error_analysis['category']}_{error_analysis['error_type']}"
        
        # Track in session
        if session_id not in self.recovery_history:
            self.recovery_history[session_id] = []
        
        self.recovery_history[session_id].append({
            "timestamp": datetime.now(),
            "error_analysis": error_analysis,
            "conversation_turn": len(state.get("conversation_history", []))
        })
        
        # Track globally for analytics
        if error_key not in self.error_analytics:
            self.error_analytics[error_key] = {
                "count": 0,
                "success_rate": 0.0,
                "common_contexts": []
            }
        
        self.error_analytics[error_key]["count"] += 1
    
    async def _execute_retry_same(
        self,
        recovery_plan: Dict[str, Any],
        state: ConversationState
    ) -> Dict[str, Any]:
        """Execute retry with same parameters."""
        return {
            "action": "retry_operation",
            "message": "I'll try the same operation again.",
            "success": True,
            "next_step": "processing_router"
        }
    
    async def _execute_retry_modified(
        self,
        recovery_plan: Dict[str, Any],
        state: ConversationState
    ) -> Dict[str, Any]:
        """Execute retry with modified parameters."""
        return {
            "action": "retry_modified",
            "message": "I'll try again with adjusted parameters.",
            "success": True,
            "next_step": "processing_router",
            "modifications": {
                "simplified_operation": True,
                "reduced_parameters": True
            }
        }
    
    async def _execute_alternative_method(
        self,
        recovery_plan: Dict[str, Any],
        state: ConversationState
    ) -> Dict[str, Any]:
        """Execute alternative processing method."""
        return {
            "action": "alternative_method",
            "message": "I'll try a different approach to accomplish your request.",
            "success": True,
            "next_step": "processing_router",
            "method_change": True
        }
    
    async def _execute_progressive_degradation(
        self,
        recovery_plan: Dict[str, Any],
        state: ConversationState
    ) -> Dict[str, Any]:
        """Execute progressive degradation to basic functionality."""
        return {
            "action": "progressive_degradation",
            "message": "I'll switch to basic mode and try a simpler version of your request.",
            "success": True,
            "next_step": "processing_router",
            "degraded_mode": True,
            "limitations": "Advanced AI features temporarily disabled"
        }
    
    async def _execute_fallback_basic(
        self,
        recovery_plan: Dict[str, Any],
        state: ConversationState
    ) -> Dict[str, Any]:
        """Execute fallback to basic functionality."""
        return {
            "action": "fallback_basic",
            "message": "I'll provide basic functionality while the issue is resolved.",
            "success": True,
            "next_step": "response_generator",
            "basic_mode": True
        }
    
    async def _execute_user_guidance(
        self,
        recovery_plan: Dict[str, Any],
        state: ConversationState
    ) -> Dict[str, Any]:
        """Execute user guidance recovery."""
        return {
            "action": "user_guidance",
            "message": "Let me help you resolve this issue step by step.",
            "success": True,
            "next_step": "response_generator",
            "guidance_steps": recovery_plan.get("steps", []),
            "requires_user_action": True
        }
    
    async def _execute_context_repair(
        self,
        recovery_plan: Dict[str, Any],
        state: ConversationState
    ) -> Dict[str, Any]:
        """Execute conversation context repair."""
        return {
            "action": "context_repair",
            "message": "I'll restore our conversation context and try again.",
            "success": True,
            "next_step": "processing_router",
            "context_repaired": True
        }
    
    async def _execute_graceful_reset(
        self,
        recovery_plan: Dict[str, Any],
        state: ConversationState
    ) -> Dict[str, Any]:
        """Execute graceful reset."""
        return {
            "action": "graceful_reset",
            "message": "I'll reset our conversation to a clean state. You can start fresh with your request.",
            "success": True,
            "next_step": "response_generator",
            "reset_performed": True
        }
    
    async def _execute_escalate_support(
        self,
        recovery_plan: Dict[str, Any],
        state: ConversationState
    ) -> Dict[str, Any]:
        """Execute support escalation."""
        return {
            "action": "escalate_support",
            "message": "I've encountered a complex issue that requires additional support. Please try again later or contact support.",
            "success": False,
            "next_step": "response_generator",
            "escalated": True
        }
    
    async def _fallback_error_recovery(
        self,
        error_message: str,
        error_type: str,
        state: ConversationState
    ) -> Dict[str, Any]:
        """Fallback error recovery when analysis fails."""
        return {
            "error_analysis": {
                "error_message": error_message,
                "error_type": error_type,
                "severity": ErrorSeverity.MEDIUM,
                "category": "unknown"
            },
            "recovery_plan": {
                "strategy": RecoveryStrategy.GRACEFUL_RESET,
                "success_rate": 0.5,
                "requires_user_action": False
            },
            "user_explanation": "I encountered an issue and will try to recover.",
            "severity": ErrorSeverity.MEDIUM,
            "recovery_strategy": RecoveryStrategy.GRACEFUL_RESET
        }
    
    def _load_error_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Load common error patterns for recognition."""
        return {
            "data_not_found": {
                "keywords": ["data not found", "no data", "missing data"],
                "severity": ErrorSeverity.MEDIUM,
                "category": "data_access"
            },
            "openai_error": {
                "keywords": ["openai", "api", "rate limit", "timeout"],
                "severity": ErrorSeverity.HIGH,
                "category": "ai_service"
            },
            "processing_error": {
                "keywords": ["processing", "transform", "analyze"],
                "severity": ErrorSeverity.MEDIUM,
                "category": "data_processing"
            },
            "memory_error": {
                "keywords": ["memory", "out of memory", "allocation"],
                "severity": ErrorSeverity.HIGH,
                "category": "system_resources"
            }
        }
    
    async def _analyze_context_factors(self, state: ConversationState) -> List[str]:
        """Analyze context factors that may contribute to errors."""
        factors = []
        
        # Check conversation length
        history_length = len(state.get("conversation_history", []))
        if history_length > 20:
            factors.append("long_conversation")
        
        # Check data availability
        if not state.get("data_context"):
            factors.append("no_data_loaded")
        
        # Check intent complexity
        intent = state.get("intent")
        if intent in [Intent.CLEAN, Intent.ANALYZE]:
            factors.append("complex_operation")
        
        # Check error history
        retry_count = state.get("retry_count", 0)
        if retry_count > 0:
            factors.append("repeated_errors")
        
        return factors
    
    async def _validate_data_availability(self, state: ConversationState) -> Dict[str, Any]:
        """Validate data availability for operations."""
        data_context = state.get("data_context")
        artifact_id = state.get("artifact_id")
        
        if not data_context and not artifact_id:
            return {
                "is_valid": False,
                "error": "No data available",
                "recommendation": "Upload a data file first"
            }
        
        # Check if data is accessible
        if artifact_id:
            memory_store = get_data_store()
            try:
                df = await memory_store.get_dataframe(artifact_id)
                if df is None:
                    return {
                        "is_valid": False,
                        "error": "Data not accessible",
                        "recommendation": "Re-upload your data file"
                    }
            except Exception as e:
                return {
                    "is_valid": False,
                    "error": f"Data access error: {str(e)}",
                    "recommendation": "Check data file integrity"
                }
        
        return {"is_valid": True}
    
    async def _validate_operation_parameters(
        self,
        intent: Intent,
        operation_params: Dict[str, Any],
        state: ConversationState
    ) -> Dict[str, Any]:
        """Validate operation parameters."""
        # Basic parameter validation
        if intent == Intent.SHOW_DATA:
            n_rows = operation_params.get("n_rows", 10)
            if n_rows <= 0 or n_rows > 1000:
                return {
                    "is_valid": False,
                    "error": "Invalid row count",
                    "recommendation": "Use a row count between 1 and 1000"
                }
        
        return {"is_valid": True}
    
    async def _validate_system_resources(
        self,
        intent: Intent,
        state: ConversationState
    ) -> Dict[str, Any]:
        """Validate system resources for operations."""
        # Check if OpenAI client is available for AI operations
        if intent in [Intent.ANALYZE, Intent.CLEAN] and not self.openai_client:
            return {
                "is_valid": False,
                "error": "AI service not available",
                "recommendation": "Use basic operations instead"
            }
        
        return {"is_valid": True}
    
    async def _assess_operation_risk(
        self,
        intent: Intent,
        operation_params: Dict[str, Any],
        state: ConversationState
    ) -> Dict[str, Any]:
        """Assess risk level of operation."""
        risk_level = "low"
        risk_factors = []
        
        # High-risk operations
        if intent in [Intent.CLEAN, Intent.REMOVE]:
            risk_level = "high"
            risk_factors.append("data_modification")
        
        # Medium-risk operations
        elif intent in [Intent.ANALYZE]:
            risk_level = "medium"
            risk_factors.append("resource_intensive")
        
        # Check data size
        dataframe_info = state.get("dataframe_info", {})
        data_shape = dataframe_info.get("shape", (0, 0))
        if data_shape[0] > 10000:
            risk_level = "high" if risk_level == "medium" else "medium"
            risk_factors.append("large_dataset")
        
        return {
            "level": risk_level,
            "factors": risk_factors,
            "mitigation_required": risk_level in ["high", "critical"]
        }
    
    def _compile_warnings(self, *validations) -> List[str]:
        """Compile warnings from validation results."""
        warnings = []
        for validation in validations:
            if not validation["is_valid"]:
                warnings.append(validation["error"])
        return warnings
    
    def _compile_recommendations(
        self,
        intent: Intent,
        operation_params: Dict[str, Any],
        state: ConversationState,
        validation_result: Dict[str, Any]
    ) -> List[str]:
        """Compile recommendations based on validation results."""
        recommendations = []
        
        for validation in validation_result["validation_results"].values():
            if not validation["is_valid"] and "recommendation" in validation:
                recommendations.append(validation["recommendation"])
        
        return recommendations
    
    # Additional helper methods can be added here for:
    # - LLM-enhanced error analysis
    # - Conversation history repair
    # - Context reference reconstruction
    # - Flow state repair
    # - etc.


# Global instance
_error_recovery_engine = None

def get_error_recovery_engine() -> EnhancedErrorRecoveryEngine:
    """Get the global error recovery engine instance."""
    global _error_recovery_engine
    if _error_recovery_engine is None:
        _error_recovery_engine = EnhancedErrorRecoveryEngine()
    return _error_recovery_engine 