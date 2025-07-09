"""
Conditional routing logic for the experiment planning graph system.

This module provides all the conditional check functions that determine
routing decisions in the LangGraph, including completion checks for each
planning stage and user intent analysis for navigation.
"""

from typing import Literal, Dict
import logging

from ..state import ExperimentPlanState, PLANNING_STAGES
from .error_handling import safe_conditional_check
from .helpers import (
    get_latest_user_input, 
    determine_section_to_edit, 
    get_stage_routing_map,
    extract_user_intent
)

logger = logging.getLogger(__name__)


def objective_completion_check(state: ExperimentPlanState) -> Literal["continue", "retry"]:
    """
    Check if objective setting is complete with error handling.
    
    This function determines whether the objective setting agent has
    successfully helped the user define clear research objectives and
    testable hypotheses before proceeding to variable identification.
    
    Args:
        state: Current experiment plan state
        
    Returns:
        "continue" if objectives are complete, "retry" if more work needed
    """
    def _check_objective_completion(state: ExperimentPlanState) -> Literal["continue", "retry"]:
        # Check if objective and hypothesis are adequately defined
        objective = state.get('experiment_objective')
        hypothesis = state.get('hypothesis')
        
        if objective and hypothesis:
            # Additional validation for quality
            if len(objective.strip()) > 20 and len(hypothesis.strip()) > 20:
                logger.info("Objective completion check: PASS")
                return "continue"
        
        logger.info("Objective completion check: RETRY")
        return "retry"
    
    return safe_conditional_check(
        _check_objective_completion, 
        state, 
        "objective_completion", 
        "retry"  # Safe fallback to retry if check fails
    )


def variable_completion_check(state: ExperimentPlanState) -> Literal["continue", "retry"]:
    """
    Check if variable identification is complete with error handling.
    
    This function determines whether the variable identification agent has
    successfully helped the user identify and define all necessary variables
    before proceeding to experimental design.
    
    Args:
        state: Current experiment plan state
        
    Returns:
        "continue" if variables are complete, "retry" if more work needed
    """
    def _check_variable_completion(state: ExperimentPlanState) -> Literal["continue", "retry"]:
        independent_vars = state.get('independent_variables', [])
        dependent_vars = state.get('dependent_variables', [])
        control_vars = state.get('control_variables', [])
        
        # Check that all variable types are defined and non-empty
        if independent_vars and dependent_vars and control_vars:
            # Additional validation for variable structure
            if (len(independent_vars) >= 1 and 
                len(dependent_vars) >= 1 and 
                len(control_vars) >= 1):
                logger.info("Variable completion check: PASS")
                return "continue"
        
        logger.info("Variable completion check: RETRY")
        return "retry"
    
    return safe_conditional_check(
        _check_variable_completion, 
        state, 
        "variable_completion", 
        "retry"
    )


def design_completion_check(state: ExperimentPlanState) -> Literal["continue", "retry"]:
    """
    Check if experimental design is complete with error handling.
    
    This function determines whether the experimental design agent has
    successfully helped the user design appropriate experimental groups,
    controls, and sample sizes before proceeding to methodology.
    
    Args:
        state: Current experiment plan state
        
    Returns:
        "continue" if design is complete, "retry" if more work needed
    """
    def _check_design_completion(state: ExperimentPlanState) -> Literal["continue", "retry"]:
        experimental_groups = state.get('experimental_groups', [])
        control_groups = state.get('control_groups', [])
        sample_size = state.get('sample_size', {})
        
        # Check that all design components are defined
        if experimental_groups and control_groups and sample_size:
            # Additional validation for design structure
            if (len(experimental_groups) >= 1 and 
                len(control_groups) >= 1 and 
                isinstance(sample_size, dict) and sample_size):
                logger.info("Design completion check: PASS")
                return "continue"
        
        logger.info("Design completion check: RETRY")
        return "retry"
    
    return safe_conditional_check(
        _check_design_completion, 
        state, 
        "design_completion", 
        "retry"
    )


def methodology_completion_check(state: ExperimentPlanState) -> Literal["continue", "retry"]:
    """
    Check if methodology and protocol development is complete with error handling.
    
    This function determines whether the methodology agent has successfully
    helped the user develop detailed protocols and comprehensive materials
    lists before proceeding to data planning.
    
    Args:
        state: Current experiment plan state
        
    Returns:
        "continue" if methodology is complete, "retry" if more work needed
    """
    def _check_methodology_completion(state: ExperimentPlanState) -> Literal["continue", "retry"]:
        methodology_steps = state.get('methodology_steps', [])
        materials_equipment = state.get('materials_equipment', [])
        
        # Check that both methodology and materials are defined
        if methodology_steps and materials_equipment:
            # Additional validation for methodology structure
            if (len(methodology_steps) >= 3 and  # At least 3 steps for meaningful protocol
                len(materials_equipment) >= 1):
                logger.info("Methodology completion check: PASS")
                return "continue"
        
        logger.info("Methodology completion check: RETRY")
        return "retry"
    
    return safe_conditional_check(
        _check_methodology_completion, 
        state, 
        "methodology_completion", 
        "retry"
    )


def data_completion_check(state: ExperimentPlanState) -> Literal["continue", "retry"]:
    """
    Check if data planning is complete with error handling.
    
    This function determines whether the data planning agent has successfully
    helped the user plan data collection and analysis approaches before
    proceeding to final review.
    
    Args:
        state: Current experiment plan state
        
    Returns:
        "continue" if data planning is complete, "retry" if more work needed
    """
    def _check_data_completion(state: ExperimentPlanState) -> Literal["continue", "retry"]:
        data_collection_plan = state.get('data_collection_plan', {})
        data_analysis_plan = state.get('data_analysis_plan', {})
        
        # Check that both data collection and analysis plans are defined
        if data_collection_plan and data_analysis_plan:
            # Additional validation for data planning structure
            if (isinstance(data_collection_plan, dict) and data_collection_plan and
                isinstance(data_analysis_plan, dict) and data_analysis_plan):
                logger.info("Data planning completion check: PASS")
                return "continue"
        
        logger.info("Data planning completion check: RETRY")
        return "retry"
    
    return safe_conditional_check(
        _check_data_completion, 
        state, 
        "data_completion", 
        "retry"
    )


def review_completion_check(state: ExperimentPlanState) -> Literal["complete", "edit_section"]:
    """
    Check if final review is complete and user approves with error handling.
    
    This function determines whether the user has approved the final plan
    for completion or wants to edit a specific section.
    
    Args:
        state: Current experiment plan state
        
    Returns:
        "complete" if user approves, "edit_section" if user wants to edit
    """
    def _check_review_completion(state: ExperimentPlanState) -> Literal["complete", "edit_section"]:
        user_input = get_latest_user_input(state)
        
        # Use the helper function to extract user intent
        user_intent = extract_user_intent(user_input)
        
        if user_intent == "approval":
            logger.info("Review completion check: COMPLETE")
            return "complete"
        elif user_intent == "edit":
            logger.info("Review completion check: EDIT_SECTION")
            return "edit_section"
        else:
            # Default to edit_section if unclear
            logger.info("Review completion check: EDIT_SECTION (default)")
            return "edit_section"
    
    return safe_conditional_check(
        _check_review_completion, 
        state, 
        "review_completion", 
        "edit_section"  # Safe fallback to edit_section
    )


def route_to_section(state: ExperimentPlanState) -> str:
    """
    Determine which section to route to based on user input with error handling.
    
    This function analyzes the user's request and determines which
    planning stage they want to edit, returning the appropriate routing key.
    
    Args:
        state: Current experiment plan state
        
    Returns:
        Routing key for the desired section
    """
    def _determine_route_section(state: ExperimentPlanState) -> str:
        user_input = get_latest_user_input(state)
        section = determine_section_to_edit(user_input, state)
        
        # Map stages to routing keys
        stage_routing_map = get_stage_routing_map()
        
        routing_key = stage_routing_map.get(section, "objective")
        logger.info(f"Routing to section: {routing_key}")
        
        return routing_key
    
    return safe_conditional_check(
        _determine_route_section, 
        state, 
        "route_to_section", 
        "objective"  # Safe fallback to objective
    )


def validate_stage_completion(state: ExperimentPlanState, stage: str) -> bool:
    """
    Validate that a specific stage has been completed successfully.
    
    This function provides a unified way to check if any planning stage
    has been completed according to its specific requirements.
    
    Args:
        state: Current experiment plan state
        stage: Name of the stage to validate
        
    Returns:
        True if stage is complete, False otherwise
    """
    stage_validators = {
        "objective_setting": lambda s: objective_completion_check(s) == "continue",
        "variable_identification": lambda s: variable_completion_check(s) == "continue",
        "experimental_design": lambda s: design_completion_check(s) == "continue",
        "methodology_protocol": lambda s: methodology_completion_check(s) == "continue",
        "data_planning": lambda s: data_completion_check(s) == "continue",
        "final_review": lambda s: review_completion_check(s) == "complete"
    }
    
    validator = stage_validators.get(stage)
    if validator:
        try:
            return validator(state)
        except Exception as e:
            logger.error(f"Stage validation failed for {stage}: {str(e)}")
            return False
    
    logger.warning(f"No validator found for stage: {stage}")
    return False


def get_incomplete_stages(state: ExperimentPlanState) -> list[str]:
    """
    Get a list of all incomplete planning stages.
    
    This function checks all planning stages and returns a list of
    those that have not yet been completed successfully.
    
    Args:
        state: Current experiment plan state
        
    Returns:
        List of incomplete stage names
    """
    incomplete_stages = []
    
    for stage in PLANNING_STAGES:
        if not validate_stage_completion(state, stage):
            incomplete_stages.append(stage)
    
    return incomplete_stages


def get_routing_options(state: ExperimentPlanState) -> Dict[str, str]:
    """
    Get all available routing options for the current state.
    
    This function returns a mapping of routing keys to their corresponding
    stage names, useful for dynamic routing decisions.
    
    Args:
        state: Current experiment plan state
        
    Returns:
        Dictionary mapping routing keys to stage names
    """
    routing_map = get_stage_routing_map()
    
    # Reverse the mapping for routing key -> stage name
    return {v: k for k, v in routing_map.items()}


def should_allow_stage_transition(
    state: ExperimentPlanState, 
    from_stage: str, 
    to_stage: str
) -> bool:
    """
    Determine if a stage transition should be allowed.
    
    This function checks whether a transition from one stage to another
    is valid based on completion requirements and stage ordering.
    
    Args:
        state: Current experiment plan state
        from_stage: Current stage name
        to_stage: Target stage name
        
    Returns:
        True if transition is allowed, False otherwise
    """
    try:
        # Allow backward transitions for editing
        from_index = PLANNING_STAGES.index(from_stage)
        to_index = PLANNING_STAGES.index(to_stage)
        
        if to_index <= from_index:
            # Backward transitions are always allowed
            return True
        
        # Forward transitions require completion of intermediate stages
        for i in range(from_index, to_index):
            stage = PLANNING_STAGES[i]
            if not validate_stage_completion(state, stage):
                logger.warning(f"Stage {stage} not complete, blocking transition to {to_stage}")
                return False
        
        return True
        
    except ValueError as e:
        logger.error(f"Invalid stage names in transition: {from_stage} -> {to_stage}: {str(e)}")
        return False 