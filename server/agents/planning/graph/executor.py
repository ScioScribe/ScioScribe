"""
Graph execution manager for the experiment planning system.

This module provides the PlanningGraphExecutor class that handles high-level
execution utilities, session management, and monitoring capabilities for
the planning graph with comprehensive error handling and recovery.
"""

from typing import Dict, Any, List, Optional, Callable
import logging
from datetime import datetime

from ..state import ExperimentPlanState, PLANNING_STAGES
from .graph_builder import create_planning_graph
from ..factory import create_new_experiment_state, add_chat_message, add_error, update_state_timestamp
from ..debug import StateDebugger, get_global_debugger
from .helpers import extract_user_intent, get_completion_keywords

logger = logging.getLogger(__name__)


class PlanningGraphExecutor:
    """
    Comprehensive execution manager for the planning graph.
    
    This class provides high-level execution utilities, session management,
    and monitoring capabilities for the planning graph with comprehensive
    error handling and state management.
    """
    
    def __init__(self, debugger: Optional[StateDebugger] = None, log_level: str = "INFO"):
        """
        Initialize the graph executor.
        
        Args:
            debugger: Optional StateDebugger instance
            log_level: Logging level for execution
        """
        self.debugger = debugger or get_global_debugger()
        self.log_level = log_level
        self.graph = None
        self.logger = logging.getLogger(f"planning.executor")
        self.logger.setLevel(getattr(logging, log_level.upper()))
        
    def initialize_graph(self) -> None:
        """
        Initialize and compile the planning graph.
        
        Raises:
            RuntimeError: If graph initialization fails
        """
        try:
            self.graph = create_planning_graph(
                debugger=self.debugger,
                log_level=self.log_level
            )
            self.logger.info("Planning graph initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize planning graph: {str(e)}")
            raise RuntimeError(f"Graph initialization failed: {str(e)}") from e
    
    def create_initial_state(
        self, 
        research_query: str, 
        experiment_id: Optional[str] = None
    ) -> ExperimentPlanState:
        """
        Create an initial state for a new experiment planning session.
        
        Args:
            research_query: User's initial research question
            experiment_id: Optional experiment ID (auto-generated if not provided)
            
        Returns:
            Initialized ExperimentPlanState
            
        Raises:
            RuntimeError: If state creation fails
        """
        try:
            # Create new state
            state = create_new_experiment_state(research_query)
            
            # Add initial user message
            state = add_chat_message(state, "user", research_query)
            
            # Add welcome message
            welcome_message = (
                "Hello! I'm your experiment planning assistant. I'll help you develop a comprehensive "
                "experiment plan from your research idea. Let's start by clarifying your research objective."
            )
            state = add_chat_message(state, "assistant", welcome_message)
            
            self.logger.info(f"Created initial state for experiment: {state['experiment_id']}")
            return state
            
        except Exception as e:
            self.logger.error(f"Failed to create initial state: {str(e)}")
            raise RuntimeError(f"State creation failed: {str(e)}") from e
    
    def execute_step(
        self, 
        state: ExperimentPlanState, 
        user_input: Optional[str] = None
    ) -> ExperimentPlanState:
        """
        Execute a single step in the planning graph.
        
        Args:
            state: Current experiment plan state
            user_input: Optional user input for this step
            
        Returns:
            Updated ExperimentPlanState after execution
            
        Raises:
            RuntimeError: If graph is not initialized
        """
        if not self.graph:
            raise RuntimeError("Graph not initialized. Call initialize_graph() first.")
        
        try:
            # Add user input to state if provided
            if user_input and user_input.strip():
                state = add_chat_message(state, "user", user_input)
                self.logger.info(f"Added user input to state: {user_input[:100]}...")
            
            # Execute one step of the graph
            result = self.graph.invoke(state)
            
            self.logger.info(f"Graph step executed successfully for experiment: {result.get('experiment_id')}")
            return result
            
        except Exception as e:
            self.logger.error(f"Graph execution step failed: {str(e)}")
            
            # Create error recovery state
            error_state = state.copy() if hasattr(state, 'copy') else dict(state)
            error_state = add_error(error_state, f"Execution step failed: {str(e)}")
            error_state = add_chat_message(
                error_state, 
                "system", 
                "I encountered an issue during execution. Let me try to recover..."
            )
            error_state = update_state_timestamp(error_state)
            
            return error_state
    
    def execute_until_completion(
        self, 
        state: ExperimentPlanState, 
        max_steps: int = 50,
        step_callback: Optional[Callable[[ExperimentPlanState, int], None]] = None
    ) -> ExperimentPlanState:
        """
        Execute the graph until completion or max steps reached.
        
        Args:
            state: Starting experiment plan state
            max_steps: Maximum number of execution steps
            step_callback: Optional callback function called after each step
            
        Returns:
            Final ExperimentPlanState
            
        Raises:
            RuntimeError: If graph is not initialized
        """
        if not self.graph:
            raise RuntimeError("Graph not initialized. Call initialize_graph() first.")
        
        current_state = state
        step_count = 0
        
        try:
            self.logger.info(f"Starting graph execution for experiment: {state.get('experiment_id')}")
            
            while step_count < max_steps:
                # Check if we've reached a terminal state
                if self._is_terminal_state(current_state):
                    self.logger.info(f"Reached terminal state after {step_count} steps")
                    break
                
                # Execute one step
                previous_state = current_state
                current_state = self.execute_step(current_state)
                
                step_count += 1
                
                # Call step callback if provided
                if step_callback:
                    try:
                        step_callback(current_state, step_count)
                    except Exception as callback_error:
                        self.logger.warning(f"Step callback failed: {callback_error}")
                
                # Check if state hasn't changed (potential infinite loop)
                if self._states_equivalent(previous_state, current_state):
                    self.logger.warning(f"State unchanged after step {step_count}, may be stuck")
                    break
            
            if step_count >= max_steps:
                self.logger.warning(f"Execution stopped at max steps ({max_steps})")
                current_state = add_chat_message(
                    current_state,
                    "system", 
                    "I've reached the maximum number of processing steps. Let me know if you'd like to continue."
                )
            
            self.logger.info(f"Graph execution completed after {step_count} steps")
            return current_state
            
        except Exception as e:
            self.logger.error(f"Graph execution failed: {str(e)}")
            return add_error(current_state, f"Execution failed: {str(e)}")
    
    def get_execution_status(self, state: ExperimentPlanState) -> Dict[str, Any]:
        """
        Get detailed execution status and progress information.
        
        Args:
            state: Current experiment plan state
            
        Returns:
            Status information dictionary
        """
        try:
            current_stage = state.get('current_stage', 'unknown')
            completed_stages = state.get('completed_stages', [])
            errors = state.get('errors', [])
            
            # Calculate progress
            total_stages = len(PLANNING_STAGES)
            completed_count = len(completed_stages)
            progress_percentage = (completed_count / total_stages) * 100 if total_stages > 0 else 0
            
            # Determine next stage
            current_stage_index = PLANNING_STAGES.index(current_stage) if current_stage in PLANNING_STAGES else -1
            next_stage = None
            if 0 <= current_stage_index < len(PLANNING_STAGES) - 1:
                next_stage = PLANNING_STAGES[current_stage_index + 1]
            
            status = {
                "experiment_id": state.get('experiment_id'),
                "current_stage": current_stage,
                "completed_stages": completed_stages,
                "next_stage": next_stage,
                "progress": {
                    "completed_count": completed_count,
                    "total_stages": total_stages,
                    "percentage": progress_percentage,
                    "is_complete": progress_percentage >= 100
                },
                "errors": errors,
                "has_errors": len(errors) > 0,
                "last_updated": state.get('updated_at'),
                "created_at": state.get('created_at'),
                "chat_message_count": len(state.get('chat_history', []))
            }
            
            return status
            
        except Exception as e:
            self.logger.error(f"Failed to get execution status: {str(e)}")
            return {
                "error": str(e),
                "experiment_id": state.get('experiment_id', 'unknown')
            }
    
    def _is_terminal_state(self, state: ExperimentPlanState) -> bool:
        """
        Check if the state represents a terminal (completed) state.
        
        Args:
            state: Current experiment plan state
            
        Returns:
            True if state is terminal, False otherwise
        """
        try:
            # Check if all stages are completed
            completed_stages = state.get('completed_stages', [])
            if len(completed_stages) >= len(PLANNING_STAGES):
                return True
            
            # Check if we're in final review and approved
            current_stage = state.get('current_stage', '')
            if current_stage == 'final_review':
                # Look for approval in recent chat messages
                chat_history = state.get('chat_history', [])
                recent_messages = chat_history[-5:] if len(chat_history) >= 5 else chat_history
                
                for message in reversed(recent_messages):
                    if message.get('role') == 'user':
                        content = message.get('content', '').lower()
                        keywords = get_completion_keywords()
                        approval_keywords = keywords["approval"]
                        if any(keyword in content for keyword in approval_keywords):
                            return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking terminal state: {str(e)}")
            return False
    
    def _states_equivalent(self, state1: ExperimentPlanState, state2: ExperimentPlanState) -> bool:
        """
        Check if two states are equivalent (for loop detection).
        
        Args:
            state1: First state to compare
            state2: Second state to compare
            
        Returns:
            True if states are equivalent, False otherwise
        """
        try:
            # Compare key fields that should change between steps
            comparison_fields = ['current_stage', 'completed_stages', 'chat_history', 'errors']
            
            for field in comparison_fields:
                if state1.get(field) != state2.get(field):
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error comparing states: {str(e)}")
            return False
    
    def get_graph_info(self) -> Dict[str, Any]:
        """
        Get information about the current graph configuration.
        
        Returns:
            Dictionary with graph information
        """
        from .graph_builder import get_graph_metadata
        
        base_info = get_graph_metadata()
        
        # Add executor-specific information
        executor_info = {
            "executor_initialized": self.graph is not None,
            "log_level": self.log_level,
            "debugger_active": self.debugger is not None
        }
        
        return {**base_info, **executor_info}
    
    def reset_graph(self) -> None:
        """
        Reset the graph executor to its initial state.
        
        This method reinitializes the graph and clears any cached state.
        """
        try:
            self.graph = None
            self.initialize_graph()
            self.logger.info("Graph executor reset successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to reset graph executor: {str(e)}")
            raise RuntimeError(f"Graph reset failed: {str(e)}") from e
    
    def validate_state_consistency(self, state: ExperimentPlanState) -> bool:
        """
        Validate the consistency of an experiment plan state.
        
        Args:
            state: State to validate
            
        Returns:
            True if state is consistent, False otherwise
        """
        try:
            # Check required fields
            required_fields = ['experiment_id', 'current_stage', 'chat_history']
            for field in required_fields:
                if field not in state:
                    self.logger.error(f"Missing required field: {field}")
                    return False
            
            # Check stage consistency
            current_stage = state.get('current_stage')
            if current_stage not in PLANNING_STAGES:
                self.logger.error(f"Invalid current stage: {current_stage}")
                return False
            
            # Check chat history format
            chat_history = state.get('chat_history', [])
            if not isinstance(chat_history, list):
                self.logger.error("Chat history must be a list")
                return False
            
            for message in chat_history:
                if not isinstance(message, dict) or 'role' not in message or 'content' not in message:
                    self.logger.error("Invalid chat message format")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"State validation failed: {str(e)}")
            return False
    
    def get_execution_metrics(self, state: ExperimentPlanState) -> Dict[str, Any]:
        """
        Get detailed metrics about the execution progress.
        
        Args:
            state: Current experiment plan state
            
        Returns:
            Dictionary with execution metrics
        """
        try:
            chat_history = state.get('chat_history', [])
            errors = state.get('errors', [])
            
            # Count message types
            user_messages = len([m for m in chat_history if m.get('role') == 'user'])
            assistant_messages = len([m for m in chat_history if m.get('role') == 'assistant'])
            system_messages = len([m for m in chat_history if m.get('role') == 'system'])
            
            # Calculate timing if available
            created_at = state.get('created_at')
            updated_at = state.get('updated_at')
            
            duration = None
            if created_at and updated_at:
                if isinstance(created_at, str):
                    created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                if isinstance(updated_at, str):
                    updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                
                duration = (updated_at - created_at).total_seconds()
            
            metrics = {
                "total_messages": len(chat_history),
                "user_messages": user_messages,
                "assistant_messages": assistant_messages,
                "system_messages": system_messages,
                "error_count": len(errors),
                "duration_seconds": duration,
                "stages_completed": len(state.get('completed_stages', [])),
                "total_stages": len(PLANNING_STAGES),
                "current_stage": state.get('current_stage'),
                "experiment_id": state.get('experiment_id')
            }
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Failed to get execution metrics: {str(e)}")
            return {"error": str(e)} 