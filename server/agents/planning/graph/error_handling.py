"""
Error handling utilities for the experiment planning graph system.

This module provides comprehensive error handling and recovery mechanisms
for LangGraph nodes, including context managers, safe execution wrappers,
and fallback strategies for robust agent orchestration.
"""

from typing import Any, Optional, Callable, TypeVar
import logging
import traceback
from contextlib import contextmanager

from ..state import ExperimentPlanState
from ..validation import validate_experiment_plan_state, StateValidationError
from ..transitions import transition_to_stage, TransitionError
from ..factory import add_chat_message, add_error, update_state_timestamp
from ..debug import get_global_debugger

logger = logging.getLogger(__name__)

T = TypeVar('T')


@contextmanager
def error_recovery_context(node_name: str, state: ExperimentPlanState):
    """
    Context manager for comprehensive error handling and recovery in LangGraph nodes.
    
    This context manager provides centralized error handling for all graph nodes,
    ensuring consistent error reporting, logging, and recovery strategies.
    
    Args:
        node_name: Name of the node being executed
        state: Current experiment plan state
        
    Yields:
        None
        
    Handles:
        - StateValidationError: State validation failures
        - TransitionError: Stage transition failures  
        - Exception: Any other unexpected errors
    """
    try:
        logger.info(f"Starting {node_name} execution")
        yield
        logger.info(f"Successfully completed {node_name} execution")
        
    except StateValidationError as e:
        logger.error(f"State validation error in {node_name}: {e}")
        error_message = f"State validation failed in {node_name}: {e.message}"
        add_error(state, error_message)
        add_chat_message(
            state, 
            "system", 
            f"I encountered a validation issue: {e.message}. Let me try to recover..."
        )
        
    except TransitionError as e:
        logger.error(f"State transition error in {node_name}: {e}")
        error_message = f"State transition failed in {node_name}: {str(e)}"
        add_error(state, error_message)
        add_chat_message(
            state, 
            "system", 
            f"I had trouble transitioning between stages: {str(e)}. Let me continue with the current stage..."
        )
        
    except Exception as e:
        logger.error(f"Unexpected error in {node_name}: {str(e)}\n{traceback.format_exc()}")
        error_message = f"Unexpected error in {node_name}: {str(e)}"
        add_error(state, error_message)
        add_chat_message(
            state, 
            "system", 
            f"I encountered an unexpected issue in {node_name}. Let me try to recover and continue..."
        )
        
        # Save debug snapshot for error analysis
        debugger = get_global_debugger()
        if debugger:
            debugger.save_debug_snapshot(
                state, 
                f"{node_name}_error",
                {"error": str(e), "traceback": traceback.format_exc()}
            )


def safe_agent_execution(
    agent_class: type, 
    node_name: str, 
    stage: str, 
    state: ExperimentPlanState
) -> ExperimentPlanState:
    """
    Safely execute an agent with comprehensive error handling and recovery.
    
    This function provides a standardized wrapper for agent execution that
    includes pre/post validation, error handling, and recovery mechanisms.
    
    Args:
        agent_class: The agent class to instantiate
        node_name: Name of the node for logging
        stage: The planning stage for this agent
        state: Current experiment plan state
        
    Returns:
        Updated ExperimentPlanState with results or error recovery
        
    Raises:
        RuntimeError: If agent execution fails and recovery is not possible
    """
    debugger = get_global_debugger()
    
    try:
        # Pre-execution state validation
        validate_experiment_plan_state(state)
        
        # Initialize and execute the agent
        agent = agent_class(debugger=debugger)
        user_input = _get_latest_user_input(state)
        
        # Execute the agent with error handling
        agent_output = agent.execute(state, user_input)
        
        # Merge the agent's output back into the original state
        updated_state = state.copy()
        updated_state.update(agent_output)
        
        # Post-execution validation
        validate_experiment_plan_state(updated_state)
        
        # Transition to the appropriate stage (if not already set)
        if updated_state.get('current_stage') != stage:
            updated_state = transition_to_stage(updated_state, stage)
        
        # Update timestamp
        updated_state = update_state_timestamp(updated_state)
        
        logger.info(f"Safe execution of {node_name} completed successfully")
        return updated_state
        
    except Exception as e:
        logger.error(f"Agent execution failed in {node_name}: {str(e)}")
        
        # Create recovery state
        recovery_state = state.copy() if hasattr(state, 'copy') else dict(state)
        
        # Add error information
        error_message = f"Agent execution failed in {node_name}: {str(e)}"
        recovery_state = add_error(recovery_state, error_message)
        
        # Add user-friendly message
        user_message = (
            f"I encountered an issue while processing the {stage.replace('_', ' ')} stage. "
            f"Please provide more information or try rephrasing your input."
        )
        recovery_state = add_chat_message(recovery_state, "assistant", user_message)
        
        # Ensure we're in a valid state
        try:
            recovery_state = update_state_timestamp(recovery_state)
            validate_experiment_plan_state(recovery_state)
        except Exception as validation_error:
            logger.error(f"Recovery state validation failed: {validation_error}")
            # Fallback to original state with minimal changes
            recovery_state = state
            recovery_state = add_error(recovery_state, f"Recovery failed in {node_name}")
        
        return recovery_state


def safe_conditional_check(
    check_function: Callable[[ExperimentPlanState], T], 
    state: ExperimentPlanState, 
    check_name: str, 
    fallback_result: T
) -> T:
    """
    Safely execute a conditional check function with error handling.
    
    This function provides a standardized wrapper for conditional routing
    checks that includes error handling and fallback mechanisms.
    
    Args:
        check_function: The check function to execute
        state: Current experiment plan state
        check_name: Name of the check for logging
        fallback_result: Default result if check fails
        
    Returns:
        Check result or fallback result on error
    """
    try:
        result = check_function(state)
        logger.info(f"Conditional check {check_name} completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Conditional check {check_name} failed: {str(e)}")
        logger.info(f"Using fallback result for {check_name}: {fallback_result}")
        return fallback_result


def _get_latest_user_input(state: ExperimentPlanState) -> str:
    """
    Extract the latest user input from chat history.
    
    This helper function searches through the chat history to find
    the most recent user message for processing.
    
    Args:
        state: Current experiment plan state
        
    Returns:
        Latest user input content or empty string if none found
    """
    chat_history = state.get('chat_history', [])
    
    # Find the most recent user message
    for message in reversed(chat_history):
        if message.get('role') == 'user':
            return message.get('content', '')
    
    return ''


def create_error_recovery_state(
    original_state: ExperimentPlanState,
    error_message: str,
    user_message: str,
    node_name: str
) -> ExperimentPlanState:
    """
    Create a standardized error recovery state.
    
    This function provides a consistent way to create recovery states
    when errors occur during graph execution.
    
    Args:
        original_state: The original state before error
        error_message: Technical error message for logging
        user_message: User-friendly error message
        node_name: Name of the node where error occurred
        
    Returns:
        Recovery state with error information
    """
    try:
        # Create a copy of the original state
        recovery_state = original_state.copy() if hasattr(original_state, 'copy') else dict(original_state)
        
        # Add error information
        recovery_state = add_error(recovery_state, error_message)
        
        # Add user-friendly message
        recovery_state = add_chat_message(recovery_state, "system", user_message)
        
        # Update timestamp
        recovery_state = update_state_timestamp(recovery_state)
        
        logger.info(f"Created error recovery state for {node_name}")
        return recovery_state
        
    except Exception as e:
        logger.error(f"Failed to create recovery state for {node_name}: {str(e)}")
        # Return original state as last resort
        return original_state 