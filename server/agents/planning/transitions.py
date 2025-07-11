"""
State transition management for the experiment planning agent system.

This module provides utilities for managing transitions between different stages
of the experiment planning process, including validation, prerequisite checking,
and conditional routing logic.
"""

from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
import logging

from .state import ExperimentPlanState, PLANNING_STAGES
from .validation import StateValidationError, validate_experiment_plan_state

logger = logging.getLogger(__name__)


class TransitionError(Exception):
    """Exception raised for invalid state transitions.
    
    Args:
        message: Error description
        current_stage: The current stage
        target_stage: The attempted target stage
        reason: Reason for transition failure
        context: Additional error context
    """
    
    def __init__(
        self,
        message: str,
        current_stage: str = None,
        target_stage: str = None,
        reason: str = None,
        context: Dict[str, Any] = None
    ) -> None:
        self.message = message
        self.current_stage = current_stage
        self.target_stage = target_stage
        self.reason = reason
        self.context = context or {}
        super().__init__(self.message)


class TransitionDirection(Enum):
    """Direction of stage transition."""
    FORWARD = "forward"
    BACKWARD = "backward"
    JUMP = "jump"


# Define valid stage transitions and their prerequisites
STAGE_TRANSITIONS = {
    "objective_setting": {
        "next": "variable_identification",
        "prerequisites": ["research_query"],
        "completion_checks": ["experiment_objective"]
    },
    "variable_identification": {
        "next": "experimental_design",
        "previous": "objective_setting",
        "prerequisites": ["experiment_objective"],
        "completion_checks": ["independent_variables", "dependent_variables"]
    },
    "experimental_design": {
        "next": "methodology_protocol",
        "previous": "variable_identification",
        "prerequisites": ["independent_variables", "dependent_variables"],
        "completion_checks": ["experimental_groups", "sample_size"]
    },
    "methodology_protocol": {
        "next": "data_planning",
        "previous": "experimental_design",
        "prerequisites": ["experimental_groups", "sample_size"],
        "completion_checks": ["methodology_steps", "materials_equipment"]
    },
    "data_planning": {
        "next": "final_review",
        "previous": "methodology_protocol",
        "prerequisites": ["methodology_steps"],
        "completion_checks": ["data_collection_plan", "data_analysis_plan"]
    },
    "final_review": {
        "previous": "data_planning",
        "prerequisites": ["data_collection_plan", "data_analysis_plan"],
        "completion_checks": ["experiment_objective", "methodology_steps", "data_collection_plan"]
    }
}


def get_stage_index(stage: str) -> int:
    """Get the index of a stage in the planning sequence.
    
    Args:
        stage: The stage name
        
    Returns:
        Index of the stage in PLANNING_STAGES
        
    Raises:
        TransitionError: If stage is invalid
    """
    try:
        return PLANNING_STAGES.index(stage)
    except ValueError:
        raise TransitionError(
            f"Invalid stage: {stage}",
            reason="stage_not_found",
            context={"valid_stages": PLANNING_STAGES}
        )


def get_transition_direction(current_stage: str, target_stage: str) -> TransitionDirection:
    """Determine the direction of a stage transition.
    
    Args:
        current_stage: Current stage name
        target_stage: Target stage name
        
    Returns:
        TransitionDirection enum value
    """
    current_index = get_stage_index(current_stage)
    target_index = get_stage_index(target_stage)
    
    if target_index == current_index + 1:
        return TransitionDirection.FORWARD
    elif target_index == current_index - 1:
        return TransitionDirection.BACKWARD
    else:
        return TransitionDirection.JUMP


def check_stage_prerequisites(state: ExperimentPlanState, stage: str) -> Tuple[bool, List[str]]:
    """Check if prerequisites for a stage are met.
    
    Args:
        state: Current experiment state
        stage: Target stage to check
        
    Returns:
        Tuple of (prerequisites_met, missing_prerequisites)
        
    Raises:
        TransitionError: If stage configuration is invalid
    """
    if stage not in STAGE_TRANSITIONS:
        raise TransitionError(
            f"No transition configuration found for stage: {stage}",
            target_stage=stage,
            reason="no_config"
        )
    
    prerequisites = STAGE_TRANSITIONS[stage].get("prerequisites", [])
    missing = []
    
    for prereq in prerequisites:
        if prereq not in state or not state[prereq]:
            missing.append(prereq)
    
    return len(missing) == 0, missing


def check_stage_completion(state: ExperimentPlanState, stage: str) -> Tuple[bool, List[str]]:
    """Check if a stage has been completed based on required fields.
    
    Args:
        state: Current experiment state
        stage: Stage to check for completion
        
    Returns:
        Tuple of (stage_completed, missing_completion_items)
        
    Raises:
        TransitionError: If stage configuration is invalid
    """
    if stage not in STAGE_TRANSITIONS:
        raise TransitionError(
            f"No transition configuration found for stage: {stage}",
            target_stage=stage,
            reason="no_config"
        )
    
    completion_checks = STAGE_TRANSITIONS[stage].get("completion_checks", [])
    missing = []
    
    for check in completion_checks:
        if check not in state or not state[check]:
            missing.append(check)
        elif isinstance(state[check], list) and len(state[check]) == 0:
            missing.append(check)
        elif isinstance(state[check], dict) and len(state[check]) == 0:
            missing.append(check)
    
    return len(missing) == 0, missing


def validate_stage_transition(
    state: ExperimentPlanState,
    target_stage: str,
    force: bool = False
) -> None:
    """Validate if a stage transition is allowed.
    
    Args:
        state: Current experiment state
        target_stage: Target stage to transition to
        force: If True, skip prerequisite checks
        
    Raises:
        TransitionError: If transition is not allowed
    """
    current_stage = state["current_stage"]
    
    # Check if target stage is valid
    if target_stage not in PLANNING_STAGES:
        raise TransitionError(
            f"Invalid target stage: {target_stage}",
            current_stage=current_stage,
            target_stage=target_stage,
            reason="invalid_stage"
        )
    
    # Allow staying in the same stage
    if current_stage == target_stage:
        return
    
    # Check prerequisites unless forced
    if not force:
        prereqs_met, missing_prereqs = check_stage_prerequisites(state, target_stage)
        if not prereqs_met:
            raise TransitionError(
                f"Prerequisites not met for stage {target_stage}",
                current_stage=current_stage,
                target_stage=target_stage,
                reason="prerequisites_not_met",
                context={"missing_prerequisites": missing_prereqs}
            )
    
    # Determine transition direction
    direction = get_transition_direction(current_stage, target_stage)
    
    # For forward transitions, check if current stage is complete
    if direction == TransitionDirection.FORWARD and not force:
        completed, missing_items = check_stage_completion(state, current_stage)
        if not completed:
            raise TransitionError(
                f"Current stage {current_stage} is not complete",
                current_stage=current_stage,
                target_stage=target_stage,
                reason="current_stage_incomplete",
                context={"missing_completion_items": missing_items}
            )
    
    # For jump transitions, validate the jump is reasonable
    if direction == TransitionDirection.JUMP and not force:
        current_index = get_stage_index(current_stage)
        target_index = get_stage_index(target_stage)
        
        # Don't allow jumping too far ahead
        if target_index > current_index + 2:
            raise TransitionError(
                f"Cannot jump from {current_stage} to {target_stage} - too many stages ahead",
                current_stage=current_stage,
                target_stage=target_stage,
                reason="jump_too_far"
            )


def transition_to_stage(
    state: ExperimentPlanState,
    target_stage: str,
    force: bool = False
) -> ExperimentPlanState:
    """Transition state to a new stage with validation.
    
    Args:
        state: Current experiment state
        target_stage: Target stage to transition to
        force: If True, skip validation checks
        
    Returns:
        Updated state with new stage
        
    Raises:
        TransitionError: If transition is not allowed
    """
    current_stage = state.get("current_stage", "unknown")
    
    
    # Check if there's a return_to_stage that should be preserved
    return_to_stage = state.get('return_to_stage')
    
    # Preserve ALL critical state before making changes
    critical_state_backup = {
        'return_to_stage': return_to_stage,
        'edit_context': state.get('edit_context'),
        'experiment_id': state.get('experiment_id'),
        'chat_history': state.get('chat_history'),
        'errors': state.get('errors'),
    }
    
    # Log current state completeness
    state_completeness = {
        'experiment_objective': bool(state.get('experiment_objective')),
        'independent_variables': bool(state.get('independent_variables')),
        'dependent_variables': bool(state.get('dependent_variables')),
        'experimental_groups': bool(state.get('experimental_groups')),
        'methodology_steps': bool(state.get('methodology_steps')),
        'data_collection_plan': bool(state.get('data_collection_plan'))
    }
    
    # Validate the transition
    try:
        validate_stage_transition(state, target_stage, force)
    except Exception as e:
        if not force:
            raise
    
    # Update stage (LangGraph manages completion tracking via checkpoints)
    old_stage = state.get("current_stage")
    state["current_stage"] = target_stage
    
    
    for key, value in critical_state_backup.items():
        if value is not None:  # Only restore non-None values
            if key not in state or state[key] != value:
                state[key] = value
    
    # Special handling for return_to_stage - this is critical for edit flows
    if return_to_stage:
        state["return_to_stage"] = return_to_stage
    
    
    
    return state


def get_next_stage(current_stage: str) -> Optional[str]:
    """Get the next stage in the planning sequence.
    
    Args:
        current_stage: Current stage name
        
    Returns:
        Next stage name or None if at the end
    """
    return STAGE_TRANSITIONS.get(current_stage, {}).get("next")


def get_previous_stage(current_stage: str) -> Optional[str]:
    """Get the previous stage in the planning sequence.
    
    Args:
        current_stage: Current stage name
        
    Returns:
        Previous stage name or None if at the beginning
    """
    return STAGE_TRANSITIONS.get(current_stage, {}).get("previous")


def get_available_transitions(state: ExperimentPlanState) -> Dict[str, Dict[str, Any]]:
    """Get all available transitions from the current stage.
    
    Args:
        state: Current experiment state
        
    Returns:
        Dictionary of available transitions with their status
    """
    current_stage = state["current_stage"]
    available = {}
    
    # Check next stage
    next_stage = get_next_stage(current_stage)
    if next_stage:
        prereqs_met, missing_prereqs = check_stage_prerequisites(state, next_stage)
        completed, missing_items = check_stage_completion(state, current_stage)
        
        available["next"] = {
            "stage": next_stage,
            "direction": TransitionDirection.FORWARD.value,
            "can_transition": prereqs_met and completed,
            "missing_prerequisites": missing_prereqs,
            "missing_completion_items": missing_items
        }
    
    # Check previous stage
    previous_stage = get_previous_stage(current_stage)
    if previous_stage:
        available["previous"] = {
            "stage": previous_stage,
            "direction": TransitionDirection.BACKWARD.value,
            "can_transition": True,  # Can always go back
            "missing_prerequisites": [],
            "missing_completion_items": []
        }
    
    # Check all other stages for jump transitions
    for stage in PLANNING_STAGES:
        if stage != current_stage and stage != next_stage and stage != previous_stage:
            prereqs_met, missing_prereqs = check_stage_prerequisites(state, stage)
            can_jump = prereqs_met and abs(get_stage_index(stage) - get_stage_index(current_stage)) <= 2
            
            available[f"jump_to_{stage}"] = {
                "stage": stage,
                "direction": TransitionDirection.JUMP.value,
                "can_transition": can_jump,
                "missing_prerequisites": missing_prereqs,
                "missing_completion_items": []
            }
    
    return available


def get_stage_progress(state: ExperimentPlanState) -> Dict[str, Any]:
    """Get overall progress through the planning stages.
    
    Args:
        state: Current experiment state
        
    Returns:
        Dictionary with progress information
    """
    current_stage = state["current_stage"]
    current_index = get_stage_index(current_stage)
    total_stages = len(PLANNING_STAGES)
    
    # Calculate completion percentage based on current stage
    # (LangGraph manages detailed completion tracking via checkpoints)
    progress_percentage = ((current_index + 1) / total_stages) * 100
    
    return {
        "current_stage": current_stage,
        "current_stage_index": current_index,
        "total_stages": total_stages,
        "progress_percentage": progress_percentage,
        "is_final_stage": current_stage == PLANNING_STAGES[-1]
    }


def reset_stage_progress(state: ExperimentPlanState, target_stage: str) -> ExperimentPlanState:
    """Reset progress to a specific stage.
    
    Args:
        state: Current experiment state
        target_stage: Stage to reset to
        
    Returns:
        Updated state with reset progress
        
    Raises:
        TransitionError: If target stage is invalid
    """
    if target_stage not in PLANNING_STAGES:
        raise TransitionError(
            f"Invalid target stage: {target_stage}",
            target_stage=target_stage,
            reason="invalid_stage"
        )
    
    # Set current stage (LangGraph manages the rest via checkpoints)
    state["current_stage"] = target_stage
    
    logger.info(f"Reset progress to stage: {target_stage}")
    
    return state 