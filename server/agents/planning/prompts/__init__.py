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

# Additional prompts will be added as implemented
# from .variable_prompts import VARIABLE_SYSTEM_PROMPT, VARIABLE_SUGGESTION_PROMPT
# from .design_prompts import DESIGN_SYSTEM_PROMPT, DESIGN_OPTIMIZATION_PROMPT
# from .methodology_prompts import METHODOLOGY_SYSTEM_PROMPT, METHODOLOGY_GENERATION_PROMPT
# from .data_prompts import DATA_SYSTEM_PROMPT, DATA_ANALYSIS_PROMPT
# from .review_prompts import REVIEW_SYSTEM_PROMPT, REVIEW_VALIDATION_PROMPT

__all__ = [
    "OBJECTIVE_SYSTEM_PROMPT",
    "INITIAL_CLARIFICATION_QUESTIONS",
    "SMART_OBJECTIVE_QUESTIONS",
    "HYPOTHESIS_DEVELOPMENT_QUESTIONS",
    "get_domain_guidance",
    "format_objective_response",
    "validate_objective_completeness",
    # Additional exports will be added as implemented
] 