"""
State factory functions for the experiment planning agent system.

This module provides utilities for creating, initializing, and manipulating
ExperimentPlanState objects with proper validation and default values.
"""

from typing import Optional
from datetime import datetime
import uuid

from .state import ExperimentPlanState
from .validation import StateValidationError, validate_experiment_id, validate_experiment_plan_state


def generate_experiment_id() -> str:
    """Generate a new UUID for an experiment.
    
    Returns:
        str: A new UUID string
    """
    return str(uuid.uuid4())


def create_default_state(experiment_id: str, research_query: str) -> ExperimentPlanState:
    """
    Create a default ExperimentPlanState with required fields populated.
    
    Args:
        experiment_id: Unique identifier for the experiment
        research_query: Initial research question or idea from the user
        
    Returns:
        ExperimentPlanState with default values
        
    Raises:
        StateValidationError: If validation fails
    """
    # Validate inputs
    validate_experiment_id(experiment_id)
    
    if not isinstance(research_query, str) or not research_query.strip():
        raise StateValidationError(
            "Research query must be a non-empty string",
            field="research_query",
            value=research_query
        )
    
    now = datetime.utcnow()
    
    state = ExperimentPlanState(
        # Core Identification
        experiment_id=experiment_id,
        research_query=research_query,
        experiment_objective=None,
        hypothesis=None,
        
        # Variables
        independent_variables=[],
        dependent_variables=[],
        control_variables=[],
        
        # Experimental Design
        experimental_groups=[],
        control_groups=[],
        sample_size={},
        
        # Methodology
        methodology_steps=[],
        materials_equipment=[],
        
        # Data & Analysis
        data_collection_plan={},
        data_analysis_plan={},
        expected_outcomes=None,
        potential_pitfalls=[],
        
        # Administrative
        ethical_considerations=None,
        timeline=None,
        budget_estimate=None,
        
        # System State
        current_stage="objective_setting",
        completed_stages=[],
        user_feedback=None,
        errors=[],
        chat_history=[],
        created_at=now,
        updated_at=now,
        
        # Human-in-the-loop State
        pending_approval=None,
        user_approved=None,
        review_stage=None,
        finalized_at=None,
        approvals={}  # Initialize empty approvals dictionary for tracking permanent approval flags
    )
    
    # Validate the created state
    validate_experiment_plan_state(state)
    
    return state


def create_new_experiment_state(research_query: str, experiment_id: Optional[str] = None) -> ExperimentPlanState:
    """
    Create a new ExperimentPlanState with auto-generated ID.
    
    Args:
        research_query: Initial research question or idea from the user
        experiment_id: Optional existing experiment ID to use
        
    Returns:
        ExperimentPlanState with new experiment ID
        
    Raises:
        StateValidationError: If validation fails
    """
    if experiment_id is None:
        experiment_id = generate_experiment_id()
    return create_default_state(experiment_id, research_query)


def update_state_timestamp(state: ExperimentPlanState) -> ExperimentPlanState:
    """
    Update the updated_at timestamp for a state.
    
    Args:
        state: The state to update
        
    Returns:
        ExperimentPlanState with updated timestamp
    """
    state['updated_at'] = datetime.utcnow()
    return state


def advance_stage(state: ExperimentPlanState, new_stage: str) -> ExperimentPlanState:
    """
    Advance the state to a new stage and update completed stages.
    
    Args:
        state: The current state
        new_stage: The new stage to advance to
        
    Returns:
        ExperimentPlanState with updated stage information
        
    Raises:
        StateValidationError: If the new stage is invalid
    """
    from .validation import validate_stage
    
    # Validate the new stage
    validate_stage(new_stage)
    
    # Add current stage to completed stages if not already there
    current_stage = state['current_stage']
    if current_stage not in state['completed_stages']:
        state['completed_stages'].append(current_stage)
    
    # Update to new stage
    state['current_stage'] = new_stage
    state = update_state_timestamp(state)
    
    return state


def add_chat_message(
    state: ExperimentPlanState, 
    role: str, 
    content: str,
    timestamp: Optional[datetime] = None
) -> ExperimentPlanState:
    """
    Add a chat message to the state's chat history.
    
    Args:
        state: The current state
        role: The role of the message sender ('user', 'assistant', 'system')
        content: The message content
        timestamp: Optional timestamp (defaults to current time)
        
    Returns:
        ExperimentPlanState with updated chat history
        
    Raises:
        StateValidationError: If the message format is invalid
    """
    if timestamp is None:
        timestamp = datetime.utcnow()
    
    # Validate role
    valid_roles = ['user', 'assistant', 'system']
    if role not in valid_roles:
        raise StateValidationError(
            f"Invalid role. Must be one of: {', '.join(valid_roles)}",
            field="role",
            value=role
        )
    
    # Validate content
    if not isinstance(content, str) or not content.strip():
        raise StateValidationError(
            "Message content must be a non-empty string",
            field="content",
            value=content
        )
    
    # Add message to chat history
    message = {
        'timestamp': timestamp,
        'role': role,
        'content': content.strip()
    }
    
    state['chat_history'].append(message)
    state = update_state_timestamp(state)
    
    return state


def add_error(state: ExperimentPlanState, error_message: str) -> ExperimentPlanState:
    """
    Add an error message to the state's error list.
    
    Args:
        state: The current state
        error_message: The error message to add
        
    Returns:
        ExperimentPlanState with updated error list
    """
    if isinstance(error_message, str) and error_message.strip():
        # Ensure errors field exists
        if 'errors' not in state:
            state['errors'] = []
        state['errors'].append(error_message.strip())
        
        # Only update timestamp if field exists
        if 'updated_at' in state:
            state = update_state_timestamp(state)
    
    return state


def clear_errors(state: ExperimentPlanState) -> ExperimentPlanState:
    """
    Clear all errors from the state.
    
    Args:
        state: The current state
        
    Returns:
        ExperimentPlanState with cleared errors
    """
    state['errors'] = []
    state = update_state_timestamp(state)
    
    return state 