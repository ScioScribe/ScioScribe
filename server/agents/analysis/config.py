"""
Configuration for the Analysis Agent - Visualization Agent

This module contains configuration settings and environment variable handling
for the LangGraph-based visualization agent.
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '..', '.env'))


@dataclass
class AnalysisAgentConfig:
    """Configuration class for the Analysis Agent"""
    
    # Model settings
    model_provider: str = "openai"
    model_name: str = "gpt-4.1"
    temperature: float = 0.1
    max_tokens: Optional[int] = None
    
    # Agent settings
    max_iterations: int = 10
    enable_streaming: bool = True
    enable_debug: bool = False
    
    # Visualization settings
    max_csv_size_mb: int = 50
    plot_width: int = 10
    plot_height: int = 6
    plot_dpi: int = 300
    plot_format: str = "png"
    
    # Data processing settings
    max_sample_rows: int = 5
    max_unique_values_display: int = 10
    default_chart_type: str = "bar"
    
    # File paths
    plots_dir: str = "plots"
    mock_data_dir: str = "mock_data"
    
    # Analysis settings
    max_analysis_length: int = 5000
    include_confidence_scores: bool = True
    
    def __post_init__(self):
        """Validate configuration after initialization"""
        if self.temperature < 0 or self.temperature > 1:
            raise ValueError("Temperature must be between 0 and 1")
        
        if self.max_iterations < 1:
            raise ValueError("Max iterations must be at least 1")
        
        if self.max_csv_size_mb < 1:
            raise ValueError("Max CSV size must be at least 1MB")
        
        if self.plot_width < 1 or self.plot_height < 1:
            raise ValueError("Plot dimensions must be positive")
        
        if self.plot_format not in ["png", "jpg", "jpeg", "svg", "pdf"]:
            raise ValueError("Unsupported plot format")
    
    def get_plots_dir(self) -> Path:
        """Get the plots directory path"""
        return Path(__file__).parent / self.plots_dir
    
    def get_mock_data_dir(self) -> Path:
        """Get the mock data directory path"""
        return Path(__file__).parent / self.mock_data_dir


def load_config_from_env() -> AnalysisAgentConfig:
    """
    Load configuration from environment variables
    
    Returns:
        AnalysisAgentConfig: Configuration object with values from environment
    """
    config = AnalysisAgentConfig()
    
    # Model settings
    config.model_provider = os.getenv("ANALYSIS_MODEL_PROVIDER", config.model_provider)
    config.model_name = os.getenv("ANALYSIS_MODEL_NAME", config.model_name)
    config.temperature = float(os.getenv("ANALYSIS_TEMPERATURE", str(config.temperature)))
    
    # Max tokens (optional)
    max_tokens_str = os.getenv("ANALYSIS_MAX_TOKENS")
    if max_tokens_str:
        config.max_tokens = int(max_tokens_str)
    
    # Agent settings
    config.max_iterations = int(os.getenv("ANALYSIS_MAX_ITERATIONS", str(config.max_iterations)))
    config.enable_streaming = os.getenv("ANALYSIS_ENABLE_STREAMING", "true").lower() == "true"
    config.enable_debug = os.getenv("ANALYSIS_ENABLE_DEBUG", "false").lower() == "true"
    
    # Visualization settings
    config.max_csv_size_mb = int(os.getenv("ANALYSIS_MAX_CSV_SIZE_MB", str(config.max_csv_size_mb)))
    config.plot_width = int(os.getenv("ANALYSIS_PLOT_WIDTH", str(config.plot_width)))
    config.plot_height = int(os.getenv("ANALYSIS_PLOT_HEIGHT", str(config.plot_height)))
    config.plot_dpi = int(os.getenv("ANALYSIS_PLOT_DPI", str(config.plot_dpi)))
    config.plot_format = os.getenv("ANALYSIS_PLOT_FORMAT", config.plot_format)
    
    # Data processing settings
    config.max_sample_rows = int(os.getenv("ANALYSIS_MAX_SAMPLE_ROWS", str(config.max_sample_rows)))
    config.max_unique_values_display = int(os.getenv("ANALYSIS_MAX_UNIQUE_VALUES", str(config.max_unique_values_display)))
    config.default_chart_type = os.getenv("ANALYSIS_DEFAULT_CHART_TYPE", config.default_chart_type)
    
    # File paths
    config.plots_dir = os.getenv("ANALYSIS_PLOTS_DIR", config.plots_dir)
    config.mock_data_dir = os.getenv("ANALYSIS_MOCK_DATA_DIR", config.mock_data_dir)
    
    # Analysis settings
    config.max_analysis_length = int(os.getenv("ANALYSIS_MAX_LENGTH", str(config.max_analysis_length)))
    config.include_confidence_scores = os.getenv("ANALYSIS_INCLUDE_CONFIDENCE", "true").lower() == "true"
    
    return config


def get_api_key_for_provider(provider: str) -> str:
    """
    Get the API key for a specific provider
    
    Args:
        provider: The model provider (openai, anthropic, etc.)
        
    Returns:
        str: The API key for the provider
        
    Raises:
        ValueError: If the API key is not found
    """
    key_mapping = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "google": "GOOGLE_API_KEY",
        "azure": "AZURE_OPENAI_API_KEY",
    }
    
    env_var = key_mapping.get(provider.lower())
    if not env_var:
        raise ValueError(f"Unknown provider: {provider}")
    
    api_key = os.getenv(env_var)
    if not api_key:
        raise ValueError(f"API key not found for provider {provider}. Set {env_var} environment variable.")
    
    return api_key


def validate_environment() -> Dict[str, Any]:
    """
    Validate that the environment is properly configured
    
    Returns:
        Dict[str, Any]: Validation results
    """
    results = {
        "valid": True,
        "errors": [],
        "warnings": []
    }
    
    # Check for required environment variables
    config = load_config_from_env()
    
    try:
        get_api_key_for_provider(config.model_provider)
    except ValueError as e:
        results["valid"] = False
        results["errors"].append(str(e))
    
    # Check for optional but recommended settings
    # LangSmith tracing is optional and not required for core functionality
    
    # Check directories
    plots_dir = config.get_plots_dir()
    mock_data_dir = config.get_mock_data_dir()
    
    if not plots_dir.exists():
        results["warnings"].append(f"Plots directory doesn't exist: {plots_dir}")
    
    if not mock_data_dir.exists():
        results["warnings"].append(f"Mock data directory doesn't exist: {mock_data_dir}")
    
    # Check for required Python packages
    required_packages = [
        "pandas",
        "matplotlib",
        "numpy",
        "langgraph",
        "langchain",
        "langchain_openai"
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        results["valid"] = False
        results["errors"].append(f"Missing required packages: {', '.join(missing_packages)}")
    
    return results


def get_default_experiment_plan() -> str:
    """
    Get the path to a default experiment plan for testing
    
    Returns:
        str: Path to default experiment plan
    """
    config = load_config_from_env()
    mock_data_dir = config.get_mock_data_dir()
    
    # Prioritize the Iris experiment plan
    plan_dir = mock_data_dir / "experiment_plans"
    if plan_dir.exists():
        iris_plan = plan_dir / "iris_species_classification.md"
        if iris_plan.exists():
            return str(iris_plan)
        
        # Return the first available experiment plan
        for plan_file in plan_dir.glob("*.md"):
            return str(plan_file)
    
    return ""


def get_default_dataset() -> str:
    """
    Get the path to a default dataset for testing
    
    Returns:
        str: Path to default dataset
    """
    config = load_config_from_env()
    mock_data_dir = config.get_mock_data_dir()
    
    # Prioritize the Iris dataset
    dataset_dir = mock_data_dir / "datasets"
    if dataset_dir.exists():
        iris_dataset = dataset_dir / "iris_dataset.csv"
        if iris_dataset.exists():
            return str(iris_dataset)
        
        # Return the first available dataset
        for dataset_file in dataset_dir.glob("*.csv"):
            return str(dataset_file)
    
    return ""


# Default configuration instance
DEFAULT_CONFIG = AnalysisAgentConfig() 