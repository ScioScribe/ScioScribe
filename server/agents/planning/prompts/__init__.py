"""
Prompt templates for the experiment planning agents.

This module contains all the prompt templates used by the different agents
to maintain consistent and effective interactions with users.
"""

# Prompt imports
from .objective_prompts import (
    OBJECTIVE_SYSTEM_PROMPT,
    INITIAL_CLARIFICATION_QUESTIONS,
    SMART_OBJECTIVE_QUESTIONS,
    HYPOTHESIS_DEVELOPMENT_QUESTIONS,
    get_domain_guidance,
    format_objective_response,
    validate_objective_completeness
)

from .variable_prompts import (
    VARIABLE_SYSTEM_PROMPT,
    INDEPENDENT_VARIABLE_QUESTIONS,
    DEPENDENT_VARIABLE_QUESTIONS,
    CONTROL_VARIABLE_QUESTIONS,
    get_variable_domain_guidance,
    format_variable_response,
    validate_variable_set
)

from .design_prompts import (
    DESIGN_SYSTEM_PROMPT,
    EXPERIMENTAL_GROUP_QUESTIONS,
    CONTROL_GROUP_QUESTIONS,
    SAMPLE_SIZE_QUESTIONS,
    get_design_domain_guidance,
    format_design_response,
    validate_experimental_design
)

from .methodology_prompts import (
    METHODOLOGY_SYSTEM_PROMPT,
    METHODOLOGY_DEVELOPMENT_QUESTIONS,
    PROTOCOL_GENERATION_QUESTIONS,
    MATERIALS_EQUIPMENT_QUESTIONS,
    get_methodology_domain_guidance,
    format_methodology_response,
    validate_methodology_completeness
)

from .data_prompts import (
    DATA_SYSTEM_PROMPT,
    DATA_COLLECTION_QUESTIONS,
    STATISTICAL_ANALYSIS_QUESTIONS,
    VISUALIZATION_QUESTIONS,
    PITFALL_IDENTIFICATION_QUESTIONS,
    SUCCESS_CRITERIA_QUESTIONS,
    get_data_domain_guidance,
    format_data_response,
    validate_data_plan_completeness
)

from .review_prompts import (
    REVIEW_SYSTEM_PROMPT,
    FINAL_VALIDATION_QUESTIONS,
    PLAN_OPTIMIZATION_QUESTIONS,
    EXPORT_PREPARATION_QUESTIONS,
    USER_APPROVAL_QUESTIONS,
    REVIEW_RESPONSE_TEMPLATES,
    FINAL_VALIDATION_CRITERIA,
    EXPORT_FORMATS,
    validate_final_plan_completeness,
    generate_plan_summary,
    format_review_response,
    generate_export_metadata
)

__all__ = [
    # Objective prompts
    "OBJECTIVE_SYSTEM_PROMPT",
    "INITIAL_CLARIFICATION_QUESTIONS",
    "SMART_OBJECTIVE_QUESTIONS",
    "HYPOTHESIS_DEVELOPMENT_QUESTIONS",
    "get_domain_guidance",
    "format_objective_response",
    "validate_objective_completeness",
    
    # Variable prompts
    "VARIABLE_SYSTEM_PROMPT",
    "INDEPENDENT_VARIABLE_QUESTIONS",
    "DEPENDENT_VARIABLE_QUESTIONS",
    "CONTROL_VARIABLE_QUESTIONS",
    "get_variable_domain_guidance",
    "format_variable_response",
    "validate_variable_set",
    
    # Design prompts
    "DESIGN_SYSTEM_PROMPT",
    "EXPERIMENTAL_GROUP_QUESTIONS",
    "CONTROL_GROUP_QUESTIONS",
    "SAMPLE_SIZE_QUESTIONS",
    "get_design_domain_guidance",
    "format_design_response",
    "validate_experimental_design",
    
    # Methodology prompts
    "METHODOLOGY_SYSTEM_PROMPT",
    "METHODOLOGY_DEVELOPMENT_QUESTIONS",
    "PROTOCOL_GENERATION_QUESTIONS",
    "MATERIALS_EQUIPMENT_QUESTIONS",
    "get_methodology_domain_guidance",
    "format_methodology_response",
    "validate_methodology_completeness",
    
    # Data prompts
    "DATA_SYSTEM_PROMPT",
    "DATA_COLLECTION_QUESTIONS",
    "STATISTICAL_ANALYSIS_QUESTIONS",
    "VISUALIZATION_QUESTIONS",
    "PITFALL_IDENTIFICATION_QUESTIONS",
    "SUCCESS_CRITERIA_QUESTIONS",
    "get_data_domain_guidance",
    "format_data_response",
    "validate_data_plan_completeness",
    
    # Review prompts
    "REVIEW_SYSTEM_PROMPT",
    "FINAL_VALIDATION_QUESTIONS",
    "PLAN_OPTIMIZATION_QUESTIONS",
    "EXPORT_PREPARATION_QUESTIONS",
    "USER_APPROVAL_QUESTIONS",
    "REVIEW_RESPONSE_TEMPLATES",
    "FINAL_VALIDATION_CRITERIA",
    "EXPORT_FORMATS",
    "validate_final_plan_completeness",
    "generate_plan_summary",
    "format_review_response",
    "generate_export_metadata"
] 