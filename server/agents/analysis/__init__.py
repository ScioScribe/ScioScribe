"""
Analysis Agent Package - Visualization Agent

This package contains the LangGraph-based visualization agent for processing
experiment plans and datasets to generate analytical visualizations.

The agent follows a 6-node pipeline:
1. Input Loader - Validates and loads experiment plans and datasets
2. Plan Parser - Extracts structured information from experiment plans
3. Data Profiler - Analyzes dataset structure and generates statistics
4. Chart Chooser - Selects appropriate visualization using LLM
5. Renderer - Generates Matplotlib visualizations
6. Response Composer - Creates explanatory text and manages memory
"""

from .agent import AnalysisAgent, AnalysisState, ChartSpecification, create_analysis_agent
from .config import (
    AnalysisAgentConfig,
    load_config_from_env,
    validate_environment,
    get_api_key_for_provider,
    get_default_experiment_plan,
    get_default_dataset,
    DEFAULT_CONFIG
)

__all__ = [
    # Main agent classes
    "AnalysisAgent",
    "AnalysisState", 
    "ChartSpecification",
    "create_analysis_agent",
    
    # Configuration
    "AnalysisAgentConfig",
    "load_config_from_env",
    "validate_environment",
    "get_api_key_for_provider",
    "get_default_experiment_plan",
    "get_default_dataset",
    "DEFAULT_CONFIG"
] 