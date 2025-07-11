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


def objective_completion_check(state: ExperimentPlanState) -> Literal["continue", "retry", "return_to_original"]:
    """
    Check if objective setting is complete with error handling.
    
    This function determines whether the objective setting agent has
    successfully helped the user define clear research objectives and
    testable hypotheses before proceeding to variable identification.
    
    Args:
        state: Current experiment plan state
        
    Returns:
        "continue" if objectives are complete, "retry" if more work needed,
        "return_to_original" if this was an edit and should return to original stage
    """
    def _check_objective_completion(state: ExperimentPlanState) -> Literal["continue", "retry", "return_to_original"]:
        # Check if this was an edit operation that should return to original stage
        return_to_stage = state.get('return_to_stage')
        current_stage = state.get('current_stage', 'unknown')
        
        # 🔍 DEBUG LOG 9: Completion check analysis
        logger.info(f"🔍 DEBUG 9 - OBJECTIVE COMPLETION CHECK:")
        logger.info(f"   Current stage: '{current_stage}'")
        logger.info(f"   Return to stage: '{return_to_stage}'")
        logger.info(f"   Is edit operation: {return_to_stage is not None}")
        logger.info(f"   Is different stage edit: {return_to_stage and return_to_stage != 'objective_setting'}")
        
        # Log current objective content
        objective = state.get('experiment_objective')
        hypothesis = state.get('hypothesis')
        research_query = state.get('research_query', '')
        
        logger.info(f"   Objective present: {bool(objective)}")
        logger.info(f"   Hypothesis present: {bool(hypothesis)}")
        logger.info(f"   Research query present: {bool(research_query)}")
        if objective:
            logger.info(f"   Objective length: {len(str(objective))}")
            logger.info(f"   Objective preview: '{str(objective)[:100]}...'")
        
        if return_to_stage and return_to_stage != "objective_setting":
            # Use the validate_objective_completeness function with 0-100 scoring
            from ..prompts.objective_prompts import validate_objective_completeness
            
            validation_results = validate_objective_completeness(objective, hypothesis, research_query)
            score = validation_results.get('score', 0)
            
            logger.info(f"🔍 DEBUG 9a - EDIT COMPLETION VALIDATION:")
            logger.info(f"   Validation score: {score}")
            logger.info(f"   Validation results: {validation_results}")
            logger.info(f"   Score threshold for edit: 70")
            logger.info(f"   Edit complete: {score >= 70}")
            
            # If edit is complete enough (≥70 for edits), return to original stage
            if score >= 70:
                logger.info(f"Objective edit complete (score: {score}), returning to {return_to_stage}")
                logger.info(f"🔍 DEBUG 9b - RETURNING TO ORIGINAL: '{return_to_stage}'")
                return "return_to_original"
            else:
                logger.info(f"Objective edit needs more work (score: {score}, need ≥70)")
                logger.info(f"🔍 DEBUG 9c - EDIT RETRY: Score too low, staying in objective")
                return "retry"
        
        # Normal flow - use higher threshold for continuing to next stage
        from ..prompts.objective_prompts import validate_objective_completeness
        
        validation_results = validate_objective_completeness(objective, hypothesis, research_query)
        score = validation_results.get('score', 0)
        
        logger.info(f"🔍 DEBUG 9d - NORMAL FLOW VALIDATION:")
        logger.info(f"   Validation score: {score}")
        logger.info(f"   Score threshold for continue: 80")
        logger.info(f"   Can continue: {score >= 80}")
        
        # Only continue if score is ≥80 as requested
        if score >= 80:
            logger.info(f"Objective completion check: CONTINUE (score: {score})")
            logger.info(f"🔍 DEBUG 9e - CONTINUE TO NEXT: Moving to variable identification")
            return "continue"
        else:
            logger.info(f"Objective completion check: RETRY (score: {score})")
            logger.info(f"🔍 DEBUG 9f - NORMAL RETRY: Score too low, staying in objective")
            return "retry"
    
    return safe_conditional_check(
        _check_objective_completion, 
        state, 
        "objective_completion", 
        "retry"  # Safe fallback to retry if check fails
    )


def variable_completion_check(state: ExperimentPlanState) -> Literal["continue", "retry", "return_to_original"]:
    """
    Check if variable identification is complete with error handling.
    
    This function determines whether the variable identification agent has
    successfully helped the user identify and define all necessary variables
    before proceeding to experimental design.
    
    Args:
        state: Current experiment plan state
        
    Returns:
        "continue" if variables are complete, "retry" if more work needed,
        "return_to_original" if this was an edit and should return to original stage
    """
    def _check_variable_completion(state: ExperimentPlanState) -> Literal["continue", "retry", "return_to_original"]:
        # Check if this was an edit operation that should return to original stage
        return_to_stage = state.get('return_to_stage')
        if return_to_stage and return_to_stage != "variable_identification":
            independent_vars = state.get('independent_variables', [])
            dependent_vars = state.get('dependent_variables', [])
            control_vars = state.get('control_variables', [])
            
            # For edits, use more lenient criteria (at least some variables defined)
            if independent_vars and dependent_vars:
                logger.info(f"Variable edit complete, returning to {return_to_stage}")
                return "return_to_original"
            else:
                logger.info("Variable edit needs more work")
                return "retry"
        
        # Normal flow - use stricter criteria for continuing to next stage
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


def design_completion_check(state: ExperimentPlanState) -> Literal["continue", "retry", "return_to_original"]:
    """
    Check if experimental design is complete with error handling.
    
    This function determines whether the experimental design agent has
    successfully helped the user design appropriate experimental groups,
    controls, and sample sizes before proceeding to methodology.
    
    Args:
        state: Current experiment plan state
        
    Returns:
        "continue" if design is complete, "retry" if more work needed,
        "return_to_original" if this was an edit and should return to original stage
    """
    def _check_design_completion(state: ExperimentPlanState) -> Literal["continue", "retry", "return_to_original"]:
        # Check if this was an edit operation that should return to original stage
        return_to_stage = state.get('return_to_stage')
        if return_to_stage and return_to_stage != "experimental_design":
            experimental_groups = state.get('experimental_groups', [])
            control_groups = state.get('control_groups', [])
            
            # For edits, use more lenient criteria
            if experimental_groups and control_groups:
                logger.info(f"Design edit complete, returning to {return_to_stage}")
                return "return_to_original"
            else:
                logger.info("Design edit needs more work")
                return "retry"
        
        # Normal flow - use stricter criteria
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


def methodology_completion_check(state: ExperimentPlanState) -> Literal["continue", "retry", "return_to_original"]:
    """
    Check if methodology and protocol development is complete with error handling.
    
    This function determines whether the methodology agent has successfully
    helped the user develop detailed protocols and comprehensive materials
    lists before proceeding to data planning.
    
    Args:
        state: Current experiment plan state
        
    Returns:
        "continue" if methodology is complete, "retry" if more work needed,
        "return_to_original" if this was an edit and should return to original stage
    """
    def _check_methodology_completion(state: ExperimentPlanState) -> Literal["continue", "retry", "return_to_original"]:
        # Check if this was an edit operation that should return to original stage
        return_to_stage = state.get('return_to_stage')
        if return_to_stage and return_to_stage != "methodology_protocol":
            methodology_steps = state.get('methodology_steps', [])
            materials_equipment = state.get('materials_equipment', [])
            
            # For edits, use more lenient criteria
            if methodology_steps and materials_equipment:
                logger.info(f"Methodology edit complete, returning to {return_to_stage}")
                return "return_to_original"
            else:
                logger.info("Methodology edit needs more work")
                return "retry"
        
        # Normal flow - use stricter criteria
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


def data_completion_check(state: ExperimentPlanState) -> Literal["continue", "retry", "return_to_original"]:
    """
    Check if data planning is complete with error handling.
    
    This function determines whether the data planning agent has successfully
    helped the user plan data collection and analysis approaches before
    proceeding to final review.
    
    Args:
        state: Current experiment plan state
        
    Returns:
        "continue" if data planning is complete, "retry" if more work needed,
        "return_to_original" if this was an edit and should return to original stage
    """
    def _check_data_completion(state: ExperimentPlanState) -> Literal["continue", "retry", "return_to_original"]:
        # Check if this was an edit operation that should return to original stage
        return_to_stage = state.get('return_to_stage')
        if return_to_stage and return_to_stage != "data_planning":
            data_collection_plan = state.get('data_collection_plan', {})
            data_analysis_plan = state.get('data_analysis_plan', {})
            
            # For edits, use more lenient criteria
            if data_collection_plan and data_analysis_plan:
                logger.info(f"Data planning edit complete, returning to {return_to_stage}")
                return "return_to_original"
            else:
                logger.info("Data planning edit needs more work")
                return "retry"
        
        # Normal flow - use stricter criteria
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
    for completion or wants to edit a specific section. Uses enhanced NLP
    to better understand user intent.
    
    Args:
        state: Current experiment plan state
        
    Returns:
        "complete" if user approves, "edit_section" if user wants to edit
    """
    def _check_review_completion(state: ExperimentPlanState) -> Literal["complete", "edit_section"]:
        user_input = get_latest_user_input(state)
        
        # Use the enhanced helper function to extract user intent
        user_intent = extract_user_intent(user_input)
        
        # Log the decision process for debugging
        logger.info(f"Review completion check - User input: '{user_input}' -> Intent: {user_intent}")
        
        if user_intent == "approval":
            logger.info("Review completion check: COMPLETE - User approved the plan")
            return "complete"
        elif user_intent == "edit":
            logger.info("Review completion check: EDIT_SECTION - User wants to make changes")
            return "edit_section"
        else:
            # For unclear intent, check if this is the first time in review
            chat_history = state.get('chat_history', [])
            review_messages = [msg for msg in chat_history if 'review' in msg.get('content', '').lower()]
            
            if len(review_messages) <= 1:
                # First time in review, likely needs user input
                logger.info("Review completion check: EDIT_SECTION - First time in review, waiting for user decision")
                return "edit_section"
            else:
                # Multiple review interactions, be more permissive for completion
                # Check for any positive indicators
                positive_indicators = ["good", "ok", "fine", "ready", "done", "thanks"]
                if any(indicator in user_input.lower() for indicator in positive_indicators):
                    logger.info("Review completion check: COMPLETE - Positive indicators detected")
                    return "complete"
                else:
                    logger.info("Review completion check: EDIT_SECTION - Unclear intent, defaulting to edit")
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
    from ..validation import validate_stage_completion
    
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
        from ..validation import validate_stage_completion
        for i in range(from_index, to_index):
            stage = PLANNING_STAGES[i]
            if not validate_stage_completion(state, stage):
                logger.warning(f"Stage {stage} not complete, blocking transition to {to_stage}")
                return False
        
        return True
        
    except ValueError as e:
        logger.error(f"Invalid stage names in transition: {from_stage} -> {to_stage}: {str(e)}")
        return False 