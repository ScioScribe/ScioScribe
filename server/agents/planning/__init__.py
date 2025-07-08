"""
ScioScribe Planning Agent Module.

This module contains the experiment planning and design agent system built with LangGraph.
It provides a conversational interface for researchers to develop complete experiment plans
through a multi-agent architecture.
"""

from .state import ExperimentPlanState, PLANNING_STAGES
from .validation import StateValidationError, validate_experiment_plan_state
from .factory import create_default_state, create_new_experiment_state, generate_experiment_id
from .serialization import (
    SerializationError,
    serialize_state_to_json,
    deserialize_json_to_state,
    serialize_state_to_firestore,
    deserialize_firestore_to_state,
    create_state_backup,
    restore_state_from_backup
)
from .transitions import (
    TransitionError,
    TransitionDirection,
    transition_to_stage,
    validate_stage_transition,
    check_stage_prerequisites,
    check_stage_completion,
    get_available_transitions,
    get_stage_progress,
    reset_stage_progress
)
from .debug import (
    StateDebugger,
    setup_logging,
    performance_monitor,
    trace_state_changes,
    log_agent_interaction,
    create_error_report,
    save_debug_snapshot,
    get_global_debugger
)
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
    
    # Serialization
    "SerializationError",
    "serialize_state_to_json",
    "deserialize_json_to_state",
    "serialize_state_to_firestore",
    "deserialize_firestore_to_state",
    "create_state_backup",
    "restore_state_from_backup",
    
    # Transitions
    "TransitionError",
    "TransitionDirection",
    "transition_to_stage",
    "validate_stage_transition",
    "check_stage_prerequisites",
    "check_stage_completion",
    "get_available_transitions",
    "get_stage_progress",
    "reset_stage_progress",
    
    # Debug & Logging
    "StateDebugger",
    "setup_logging",
    "performance_monitor",
    "trace_state_changes",
    "log_agent_interaction",
    "create_error_report",
    "save_debug_snapshot",
    "get_global_debugger",
    
    # Graph
    # "create_planning_graph"  # TODO: Add when graph module is created
] 