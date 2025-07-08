"""
ScioScribe Planning Agent Module.

This module contains the experiment planning and design agent system built with LangGraph.
It provides a conversational interface for researchers to develop complete experiment plans
through a multi-agent architecture.
"""

from .state import ExperimentPlanState, PLANNING_STAGES
from .validation import StateValidationError, validate_experiment_plan_state
from .factory import create_default_state, create_new_experiment_state, generate_experiment_id
# from .graph import create_planning_graph  # TODO: Create graph module

__all__ = [
    # Core state
    "ExperimentPlanState",
    "PLANNING_STAGES",
    
    # Validation
    "StateValidationError", 
    "validate_experiment_plan_state",
    
    # Factory functions
    "create_default_state",
    "create_new_experiment_state", 
    "generate_experiment_id",
    
    # Graph
    # "create_planning_graph"  # TODO: Add when graph module is created
] 