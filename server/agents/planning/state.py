"""
Core state definition for the experiment planning agent system.

This module defines the ExperimentPlanState TypedDict and related constants
that all planning agents use to collaborate and build comprehensive experiment plans.
"""

from typing import TypedDict, Optional, List, Dict, Any


class ExperimentPlanState(TypedDict):
    """
    Simplified state structure for the experiment planning agent system.
    
    This TypedDict focuses on domain data only, letting LangGraph handle
    control flow, approvals, and system state management through its
    built-in mechanisms (interrupts, checkpoints, etc.).
    """
    
    # Core Identification
    experiment_id: str
    research_query: str
    experiment_objective: Optional[str]
    hypothesis: Optional[str]
    
    # Variables
    independent_variables: List[Dict[str, Any]]  # name, type, units, levels
    dependent_variables: List[Dict[str, Any]]    # name, type, units, measurement_method
    control_variables: List[Dict[str, Any]]      # name, reason, control_method
    
    # Experimental Design
    experimental_groups: List[Dict[str, Any]]    # name, description, conditions
    control_groups: List[Dict[str, Any]]         # type, purpose, description
    sample_size: Dict[str, Any]                  # biological_replicates, technical_replicates, power_analysis
    
    # Methodology
    methodology_steps: List[Dict[str, Any]]      # step_number, description, parameters, duration
    materials_equipment: List[Dict[str, Any]]    # name, type, quantity, specifications
    
    # Data & Analysis
    data_collection_plan: Dict[str, Any]         # methods, timing, formats
    data_analysis_plan: Dict[str, Any]           # statistical_tests, visualizations, software
    expected_outcomes: Optional[str]
    potential_pitfalls: List[Dict[str, Any]]     # issue, likelihood, mitigation
    
    # Administrative (Optional)
    ethical_considerations: Optional[str]
    timeline: Optional[Dict[str, Any]]
    budget_estimate: Optional[Dict[str, Any]]
    
    # Minimal System State (LangGraph manages the rest)
    current_stage: str
    errors: List[str]
    chat_history: List[Dict[str, Any]]
    
    # Edit mode flags for conditional interrupt behavior
    edit_mode: Optional[bool]           # True when processing edit requests (skip interrupts)
    return_to_stage: Optional[str]      # Stage to return to after edit completion


# Stage constants for tracking progress
PLANNING_STAGES = [
    "objective_setting",
    "variable_identification", 
    "experimental_design",
    "methodology_protocol",
    "data_planning",
    "final_review"
]


# Required fields for each variable type
VARIABLE_REQUIRED_FIELDS = {
    'independent': ['name', 'type', 'units', 'levels'],
    'dependent': ['name', 'type', 'units', 'measurement_method'],
    'control': ['name', 'reason', 'control_method']
}

# Required fields for experimental groups
GROUP_REQUIRED_FIELDS = ['name', 'description', 'conditions']

# Required fields for methodology steps
METHODOLOGY_REQUIRED_FIELDS = ['step_number', 'description', 'parameters', 'duration']

# Required fields for materials/equipment
MATERIAL_REQUIRED_FIELDS = ['name', 'type', 'quantity', 'specifications']

# Required fields for pitfalls
PITFALL_REQUIRED_FIELDS = ['issue', 'likelihood', 'mitigation']

# Required fields for chat history
CHAT_REQUIRED_FIELDS = ['timestamp', 'role', 'content'] 