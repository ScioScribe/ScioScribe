"""
Analysis Agent using LangGraph - Visualization Agent

This module implements a LangGraph-based visualization agent that processes
experiment plans and datasets to generate analytical visualizations.

The agent follows a 6-node pipeline:
1. Input Loader - Validates and loads experiment plans and datasets
2. Plan Parser - Extracts structured information from experiment plans
3. Data Profiler - Analyzes dataset structure and generates statistics
4. Chart Chooser - Selects appropriate visualization using LLM
5. Renderer - Generates Matplotlib visualizations
6. Response Composer - Creates explanatory text and manages memory

Architecture follows the blueprint specified in the requirements document.
"""

import os
import logging
from typing import Annotated, List, Dict, Any, Optional
from typing_extensions import TypedDict
from dataclasses import dataclass, asdict
from pathlib import Path

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

# Import modular nodes
from .nodes import (
    InputLoaderNode,
    PlanParserNode,
    DataProfilerNode,
    ChartChooserNode,
    RendererNode,
    ResponseComposerNode
)

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '..', '.env'))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
PLOTS_DIR = Path(__file__).parent / "plots"
MOCK_DATA_DIR = Path(__file__).parent / "mock_data"

# Ensure plots directory exists
PLOTS_DIR.mkdir(exist_ok=True)


@dataclass
class ChartSpecification:
    """
    Chart specification schema for visualization generation
    """
    chart_type: str  # bar, line, scatter, violin, box, heatmap
    x_column: str
    y_column: str
    hue_column: Optional[str] = None
    groupby_column: Optional[str] = None
    statistical_overlay: Optional[str] = None  # trend, confidence, regression
    title: str = ""
    x_label: str = ""
    y_label: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChartSpecification':
        """Create from dictionary"""
        return cls(**data)


class AnalysisState(TypedDict):
    """
    State schema for the Analysis Agent
    
    The state contains all information flowing through the 6-node pipeline:
    - messages: Conversation history and LLM responses
    - user_prompt: Original user request
    - experiment_plan_path: Path to experiment plan file
    - csv_file_path: Path to dataset file
    - memory: Memory object for iterative refinement
    - plan_text: Raw experiment plan content
    - structured_plan: Extracted plan information
    - data_schema: CSV column types and statistics
    - data_sample: Sample rows from dataset
    - chart_specification: Selected visualization specification
    - plot_image_path: Path to generated visualization
    - llm_code_used: LLM-generated code for visualization (if used)
    - warnings: List of warnings from the rendering process
    - explanation: Generated explanatory text
    - error_message: Error information if any step fails
    """
    messages: Annotated[List, add_messages]
    user_prompt: str
    experiment_plan_path: str
    csv_file_path: str
    memory: Dict[str, Any]
    plan_text: str
    structured_plan: Dict[str, Any]
    data_schema: Dict[str, Any]
    data_sample: List[Dict[str, Any]]
    chart_specification: Dict[str, Any]
    plot_image_path: str
    llm_code_used: str
    warnings: List[str]
    explanation: str
    error_message: str


class AnalysisAgent:
    """
    LangGraph-based Visualization Agent
    
    This agent processes experiment plans and datasets to generate
    analytical visualizations through a 6-node pipeline using modular nodes.
    """
    
    def __init__(self, model_provider: str = "openai", model_name: str = "gpt-4.1"):
        """
        Initialize the Analysis Agent
        
        Args:
            model_provider: The LLM provider (openai, anthropic, etc.)
            model_name: The specific model to use
        """
        self.model_provider = model_provider
        self.model_name = model_name
        
        # Initialize the language model
        self.llm = self._init_llm()
        
        # Initialize modular nodes
        self._init_nodes()
        
        # Build the graph
        self.graph = self._build_graph()
        
        logger.info(f"Analysis Agent initialized with {model_provider}:{model_name}")
    
    def _init_llm(self):
        """Initialize the language model based on provider"""
        model_string = f"{self.model_provider}:{self.model_name}"
        
        # Set up API keys based on provider
        if self.model_provider == "openai":
            if not os.getenv("OPENAI_API_KEY"):
                raise ValueError("OPENAI_API_KEY environment variable not set")
        elif self.model_provider == "anthropic":
            if not os.getenv("ANTHROPIC_API_KEY"):
                raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        
        return init_chat_model(model_string)
    
    def _init_nodes(self):
        """Initialize all modular nodes with the LLM instance"""
        self.input_loader = InputLoaderNode(llm=self.llm)
        self.plan_parser = PlanParserNode(llm=self.llm)
        self.data_profiler = DataProfilerNode(llm=self.llm)
        self.chart_chooser = ChartChooserNode(llm=self.llm)
        self.renderer = RendererNode(llm=self.llm)
        self.response_composer = ResponseComposerNode(llm=self.llm)
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph 6-node visualization pipeline"""
        graph_builder = StateGraph(AnalysisState)
        
        # Add the 6 nodes using modular implementations
        graph_builder.add_node("input_loader", self._input_loader_wrapper)
        graph_builder.add_node("plan_parser", self._plan_parser_wrapper)
        graph_builder.add_node("data_profiler", self._data_profiler_wrapper)
        graph_builder.add_node("chart_chooser", self._chart_chooser_wrapper)
        graph_builder.add_node("renderer", self._renderer_wrapper)
        graph_builder.add_node("response_composer", self._response_composer_wrapper)
        
        # Add edges - linear pipeline
        graph_builder.add_edge(START, "input_loader")
        graph_builder.add_edge("input_loader", "plan_parser")
        graph_builder.add_edge("plan_parser", "data_profiler")
        graph_builder.add_edge("data_profiler", "chart_chooser")
        graph_builder.add_edge("chart_chooser", "renderer")
        graph_builder.add_edge("renderer", "response_composer")
        graph_builder.add_edge("response_composer", END)
        
        return graph_builder.compile()
    
    # Node wrapper methods to maintain LangGraph interface
    def _input_loader_wrapper(self, state: AnalysisState) -> Dict[str, Any]:
        """Wrapper for input loader node"""
        return self.input_loader.process(state)
    
    def _plan_parser_wrapper(self, state: AnalysisState) -> Dict[str, Any]:
        """Wrapper for plan parser node"""
        return self.plan_parser.process(state)
    
    def _data_profiler_wrapper(self, state: AnalysisState) -> Dict[str, Any]:
        """Wrapper for data profiler node"""
        return self.data_profiler.process(state)
    
    def _chart_chooser_wrapper(self, state: AnalysisState) -> Dict[str, Any]:
        """Wrapper for chart chooser node"""
        return self.chart_chooser.process(state)
    
    def _renderer_wrapper(self, state: AnalysisState) -> Dict[str, Any]:
        """Wrapper for renderer node"""
        return self.renderer.process(state)
    
    def _response_composer_wrapper(self, state: AnalysisState) -> Dict[str, Any]:
        """Wrapper for response composer node"""
        return self.response_composer.process(state)
    
    def generate_visualization(self, 
                             user_prompt: str,
                             experiment_plan_path: str,
                             csv_file_path: str,
                             memory: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Main method to generate visualization from user request
        
        Args:
            user_prompt: Natural language question or instruction
            experiment_plan_path: Path to experiment plan file
            csv_file_path: Path to dataset CSV file
            memory: Optional memory object for iterative refinement
            
        Returns:
            Dictionary containing explanation and image path
        """
        logger.info(f"Starting visualization generation for: {user_prompt}")
        
        # Initialize state
        initial_state = {
            "messages": [],
            "user_prompt": user_prompt,
            "experiment_plan_path": experiment_plan_path,
            "csv_file_path": csv_file_path,
            "memory": memory or {},
            "plan_text": "",
            "structured_plan": {},
            "data_schema": {},
            "data_sample": [],
            "chart_specification": {},
            "plot_image_path": "",
            "llm_code_used": "",
            "warnings": [],
            "explanation": "",
            "error_message": ""
        }
        
        # Run the graph
        result = self.graph.invoke(initial_state)
        
        # Return final result
        return {
            "explanation": result["explanation"],
            "image_path": result["plot_image_path"],
            "memory": result["memory"],
            "llm_code_used": result.get("llm_code_used", ""),
            "warnings": result.get("warnings", [])
        }


def create_analysis_agent(model_provider: str = "openai", model_name: str = "gpt-4.1") -> AnalysisAgent:
    """
    Factory function to create an Analysis Agent instance
    
    Args:
        model_provider: The LLM provider to use
        model_name: The specific model to use
        
    Returns:
        Configured AnalysisAgent instance
    """
    return AnalysisAgent(model_provider=model_provider, model_name=model_name) 