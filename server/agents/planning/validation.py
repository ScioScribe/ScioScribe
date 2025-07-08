"""
State validation functions for the experiment planning agent system.

This module provides comprehensive validation for ExperimentPlanState objects,
ensuring data integrity and structural consistency across all agent interactions.
"""

from typing import Dict, List, Any
from datetime import datetime
from contextlib import contextmanager
import logging
import uuid

from .state import (
    ExperimentPlanState,
    PLANNING_STAGES,
    VARIABLE_REQUIRED_FIELDS,
    GROUP_REQUIRED_FIELDS,
    METHODOLOGY_REQUIRED_FIELDS,
    CHAT_REQUIRED_FIELDS
)

logger = logging.getLogger(__name__)


class StateValidationError(Exception):
    """Exception raised for state validation errors.
    
    Args:
        message: Error description
        field: The field that failed validation
        value: The invalid value
        context: Additional error context
    """
    
    def __init__(
        self, 
        message: str, 
        field: str = None, 
        value: Any = None,
        context: Dict[str, Any] = None
    ) -> None:
        self.message = message
        self.field = field
        self.value = value
        self.context = context or {}
        super().__init__(self.message)


@contextmanager
def validation_context(operation: str):
    """Context manager for validation error handling.
    
    Args:
        operation: Description of the validation operation
        
    Raises:
        StateValidationError: Wrapped validation error
    """
    try:
        yield
    except StateValidationError:
        raise
    except Exception as e:
        logger.error(f'Validation error during {operation}: {str(e)}')
        raise StateValidationError(
            f'Validation failed during {operation}',
            context={'error_type': type(e).__name__, 'details': str(e)}
        )


def validate_experiment_id(experiment_id: str) -> bool:
    """Validate experiment ID format.
    
    Args:
        experiment_id: The experiment ID to validate
        
    Returns:
        bool: True if valid
        
    Raises:
        StateValidationError: If validation fails
    """
    if not isinstance(experiment_id, str):
        raise StateValidationError(
            "Experiment ID must be a string",
            field="experiment_id",
            value=experiment_id
        )
    
    if not experiment_id.strip():
        raise StateValidationError(
            "Experiment ID cannot be empty",
            field="experiment_id",
            value=experiment_id
        )
    
    # Check if it's a valid UUID format
    try:
        uuid.UUID(experiment_id)
    except ValueError:
        raise StateValidationError(
            "Experiment ID must be a valid UUID",
            field="experiment_id",
            value=experiment_id
        )
    
    return True


def validate_stage(stage: str) -> bool:
    """Validate current stage value.
    
    Args:
        stage: The stage to validate
        
    Returns:
        bool: True if valid
        
    Raises:
        StateValidationError: If validation fails
    """
    if not isinstance(stage, str):
        raise StateValidationError(
            "Stage must be a string",
            field="current_stage",
            value=stage
        )
    
    if stage not in PLANNING_STAGES:
        raise StateValidationError(
            f"Invalid stage. Must be one of: {', '.join(PLANNING_STAGES)}",
            field="current_stage",
            value=stage
        )
    
    return True


def validate_variable_list(variables: List[Dict[str, Any]], variable_type: str) -> bool:
    """Validate a list of variables.
    
    Args:
        variables: List of variable dictionaries to validate
        variable_type: Type of variables ('independent', 'dependent', 'control')
        
    Returns:
        bool: True if valid
        
    Raises:
        StateValidationError: If validation fails
    """
    if not isinstance(variables, list):
        raise StateValidationError(
            f"{variable_type} variables must be a list",
            field=f"{variable_type}_variables",
            value=variables
        )
    
    required_fields = VARIABLE_REQUIRED_FIELDS.get(variable_type, [])
    
    for i, variable in enumerate(variables):
        if not isinstance(variable, dict):
            raise StateValidationError(
                f"Variable at index {i} must be a dictionary",
                field=f"{variable_type}_variables[{i}]",
                value=variable
            )
        
        for field in required_fields:
            if field not in variable:
                raise StateValidationError(
                    f"Missing required field '{field}' in {variable_type} variable",
                    field=f"{variable_type}_variables[{i}].{field}",
                    value=variable
                )
    
    return True


def validate_group_list(groups: List[Dict[str, Any]], group_type: str) -> bool:
    """Validate a list of experimental groups.
    
    Args:
        groups: List of group dictionaries to validate
        group_type: Type of groups ('experimental' or 'control')
        
    Returns:
        bool: True if valid
        
    Raises:
        StateValidationError: If validation fails
    """
    if not isinstance(groups, list):
        raise StateValidationError(
            f"{group_type} groups must be a list",
            field=f"{group_type}_groups",
            value=groups
        )
    
    # Define required fields based on group type
    if group_type == 'experimental':
        required_fields = GROUP_REQUIRED_FIELDS  # ['name', 'description', 'conditions']
    elif group_type == 'control':
        required_fields = ['type', 'purpose', 'description']  # Different fields for control groups
    else:
        raise StateValidationError(
            f"Invalid group type: {group_type}. Must be 'experimental' or 'control'",
            field="group_type",
            value=group_type
        )
    
    for i, group in enumerate(groups):
        if not isinstance(group, dict):
            raise StateValidationError(
                f"Group at index {i} must be a dictionary",
                field=f"{group_type}_groups[{i}]",
                value=group
            )
        
        for field in required_fields:
            if field not in group:
                raise StateValidationError(
                    f"Missing required field '{field}' in {group_type} group",
                    field=f"{group_type}_groups[{i}].{field}",
                    value=group
                )
    
    return True


def validate_methodology_steps(steps: List[Dict[str, Any]]) -> bool:
    """Validate methodology steps.
    
    Args:
        steps: List of methodology step dictionaries
        
    Returns:
        bool: True if valid
        
    Raises:
        StateValidationError: If validation fails
    """
    if not isinstance(steps, list):
        raise StateValidationError(
            "Methodology steps must be a list",
            field="methodology_steps",
            value=steps
        )
    
    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            raise StateValidationError(
                f"Methodology step at index {i} must be a dictionary",
                field=f"methodology_steps[{i}]",
                value=step
            )
        
        for field in METHODOLOGY_REQUIRED_FIELDS:
            if field not in step:
                raise StateValidationError(
                    f"Missing required field '{field}' in methodology step",
                    field=f"methodology_steps[{i}].{field}",
                    value=step
                )
        
        # Validate step_number is an integer
        if not isinstance(step.get('step_number'), int):
            raise StateValidationError(
                "Step number must be an integer",
                field=f"methodology_steps[{i}].step_number",
                value=step.get('step_number')
            )
    
    return True


def validate_chat_history(chat_history: List[Dict[str, Any]]) -> bool:
    """Validate chat history format.
    
    Args:
        chat_history: List of chat message dictionaries
        
    Returns:
        bool: True if valid
        
    Raises:
        StateValidationError: If validation fails
    """
    if not isinstance(chat_history, list):
        raise StateValidationError(
            "Chat history must be a list",
            field="chat_history",
            value=chat_history
        )
    
    for i, message in enumerate(chat_history):
        if not isinstance(message, dict):
            raise StateValidationError(
                f"Chat message at index {i} must be a dictionary",
                field=f"chat_history[{i}]",
                value=message
            )
        
        for field in CHAT_REQUIRED_FIELDS:
            if field not in message:
                raise StateValidationError(
                    f"Missing required field '{field}' in chat message",
                    field=f"chat_history[{i}].{field}",
                    value=message
                )
        
        # Validate role is valid
        valid_roles = ['user', 'assistant', 'system']
        if message.get('role') not in valid_roles:
            raise StateValidationError(
                f"Invalid role. Must be one of: {', '.join(valid_roles)}",
                field=f"chat_history[{i}].role",
                value=message.get('role')
            )
    
    return True


def validate_state_structure(state: Dict[str, Any]) -> bool:
    """Validate the overall state structure.
    
    Args:
        state: The state dictionary to validate
        
    Returns:
        bool: True if valid
        
    Raises:
        StateValidationError: If validation fails
    """
    with validation_context("state structure validation"):
        # Check required fields exist
        required_fields = [
            'experiment_id', 'research_query', 'current_stage', 
            'completed_stages', 'created_at', 'updated_at'
        ]
        
        for field in required_fields:
            if field not in state:
                raise StateValidationError(
                    f"Missing required field '{field}' in state",
                    field=field,
                    value=None
                )
        
        # Validate specific fields
        validate_experiment_id(state['experiment_id'])
        validate_stage(state['current_stage'])
        
        # Validate completed stages
        if not isinstance(state['completed_stages'], list):
            raise StateValidationError(
                "Completed stages must be a list",
                field="completed_stages",
                value=state['completed_stages']
            )
        
        for stage in state['completed_stages']:
            if stage not in PLANNING_STAGES:
                raise StateValidationError(
                    f"Invalid completed stage: {stage}",
                    field="completed_stages",
                    value=stage
                )
        
        # Validate datetime fields
        for field in ['created_at', 'updated_at']:
            if not isinstance(state[field], datetime):
                raise StateValidationError(
                    f"Field '{field}' must be a datetime object",
                    field=field,
                    value=state[field]
                )
        
        # Validate variable lists
        validate_variable_list(state.get('independent_variables', []), 'independent')
        validate_variable_list(state.get('dependent_variables', []), 'dependent')
        validate_variable_list(state.get('control_variables', []), 'control')
        
        # Validate group lists
        validate_group_list(state.get('experimental_groups', []), 'experimental')
        validate_group_list(state.get('control_groups', []), 'control')
        
        # Validate methodology steps
        validate_methodology_steps(state.get('methodology_steps', []))
        
        # Validate chat history
        validate_chat_history(state.get('chat_history', []))
    
    return True


def validate_experiment_plan_state(state: ExperimentPlanState) -> bool:
    """Validate a complete ExperimentPlanState.
    
    Args:
        state: The ExperimentPlanState to validate
        
    Returns:
        bool: True if valid
        
    Raises:
        StateValidationError: If validation fails
    """
    return validate_state_structure(state) 