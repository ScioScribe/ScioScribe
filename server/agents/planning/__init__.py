"""
ScioScribe Planning Agent Module.

This module contains the experiment planning and design agent system built with LangGraph.
It provides a conversational interface for researchers to develop complete experiment plans
through a multi-agent architecture.
"""

from .state import ExperimentPlanState, PLANNING_STAGES
from .validation import StateValidationError, validate_experiment_plan_state
from .factory import create_new_experiment_state, generate_experiment_id
from .serialization import (
    serialize_state_to_json,
    deserialize_json_to_state,
    serialize_state_to_dict,
    deserialize_dict_to_state,
    get_state_summary,
    validate_serialized_state
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
    performance_context,
    trace_state_changes,
    log_agent_interaction,
    create_error_report,
    save_debug_snapshot,
    get_global_debugger
)
from .llm_config import (
    LLMManager,
    LLMConfigError,
    get_llm_manager,
    create_agent_llm,
    create_standard_prompt,
    test_llm_connection,
    get_llm_usage_stats
)
from .graph import (
    create_planning_graph,
    PlanningGraphExecutor,
    start_new_experiment_planning,
    execute_planning_conversation,
    get_planning_graph_info
)
from .tools import (
    TavilySearchTool,
    TavilySearchError,
    SearchType,
    SearchResult,
    SearchResponse,
    search_for_research,
    search_for_protocol,
    search_for_safety,
    StatisticalCalculator,
    StatisticalTestType,
    EffectSize,
    PowerAnalysisResult,
    SampleSizeResult,
    calculate_sample_size_ttest,
    calculate_power_ttest,
    recommend_tests_for_design,
    validate_design_power
)

__all__ = [
    # Core state
    "ExperimentPlanState",
    "PLANNING_STAGES",
    
    # Validation
    "StateValidationError", 
    "validate_experiment_plan_state",
    
    # Factory functions
    "create_new_experiment_state", 
    "generate_experiment_id",
    
    # Serialization
    "serialize_state_to_json",
    "deserialize_json_to_state",
    "serialize_state_to_dict",
    "deserialize_dict_to_state",
    "get_state_summary",
    "validate_serialized_state",
    
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
    "performance_context",
    "trace_state_changes",
    "log_agent_interaction",
    "create_error_report",
    "save_debug_snapshot",
    "get_global_debugger",
    
    # LLM Configuration
    "LLMManager",
    "LLMConfigError",
    "get_llm_manager",
    "create_agent_llm",
    "create_standard_prompt",
    "test_llm_connection",
    "get_llm_usage_stats",
    
    # Graph & Execution
    "create_planning_graph",
    "PlanningGraphExecutor",
    "start_new_experiment_planning",
    "execute_planning_conversation",
    "get_planning_graph_info",
    
    # Tools
    "TavilySearchTool",
    "TavilySearchError",
    "SearchType",
    "SearchResult",
    "SearchResponse",
    "search_for_research",
    "search_for_protocol",
    "search_for_safety",
    
    # Statistical tools
    "StatisticalCalculator",
    "StatisticalTestType",
    "EffectSize",
    "PowerAnalysisResult",
    "SampleSizeResult",
    "calculate_sample_size_ttest",
    "calculate_power_ttest",
    "recommend_tests_for_design",
    "validate_design_power"
] 