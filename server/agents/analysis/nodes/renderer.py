"""
LLM-Powered Renderer Node using LangGraph

This module implements a LangGraph-based renderer that orchestrates three nodes:
1. DraftOrFixCode - Generates/fixes Plotly Express code with validation
2. SandboxRunner - Executes code in secure sandbox  
3. OutputAssembler - Assembles final output on success

The graph implements a lean retry loop without fallback rendering.
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Annotated
from typing_extensions import TypedDict

import pandas as pd
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

from .base_node import BaseNode
from .draft_or_fix_code import DraftOrFixCodeNode
from .sandbox_runner import SandboxRunnerNode
from .output_assembler import OutputAssemblerNode

# Constants
PLOTS_DIR = Path(__file__).parent.parent / "plots"
MAX_RETRIES = 3

# Ensure plots directory exists
PLOTS_DIR.mkdir(exist_ok=True)

# Style dictionary for LLM guidance - MODERN & BRIGHT
STYLE_DICTIONARY = {
    "color_palettes": {
        "modern_bright": ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7"],
        "neon": ["#FF006E", "#FB5607", "#FFBE0B", "#8338EC", "#3A86FF"],
        "pastel_pop": ["#FFB6C1", "#87CEEB", "#98FB98", "#DDA0DD", "#F0E68C"],
        "bold_primary": ["#FF4757", "#3742FA", "#2ED573", "#FFA502", "#747D8C"],
        "tropical": ["#FC5C65", "#26DE81", "#FD79A8", "#A29BFE", "#FDCB6E"],
        "electric": ["#00D2D3", "#FF6B9D", "#C44569", "#F8B500", "#2C2C54"]
    }
}


class RendererState(TypedDict):
    """
    State schema for the Renderer sub-graph
    
    Contains all information flowing through the 3-node renderer pipeline:
    - ingredients: All data needed for code generation
    - generated_code: LLM-generated Plotly Express code
    - error_msg: Current error message (None if no error)
    - retry_count: Number of retries attempted
    - warnings: List of warnings accumulated
    - plot_image_path: Final output path (primary format)
    - plot_html_path: HTML output path (interactive)
    - plot_png_path: PNG output path (static)
    - llm_code_used: Final code that worked
    """
    ingredients: Dict[str, Any]
    generated_code: str
    error_msg: str
    retry_count: int
    warnings: List[str]
    plot_image_path: str
    plot_html_path: str
    plot_png_path: str
    llm_code_used: str


class RendererNode(BaseNode):
    """
    LLM-Powered Renderer Node using LangGraph
    
    Orchestrates a 3-node sub-graph to generate Plotly Express visualizations
    with automatic error correction and retry logic.
    """
    
    def __init__(self, llm: Any):
        """Initialize the renderer with its sub-nodes"""
        super().__init__(llm)
        
        # Initialize sub-nodes
        self.draft_or_fix = DraftOrFixCodeNode(llm=self.llm)
        self.sandbox_runner = SandboxRunnerNode(llm=self.llm)
        self.output_assembler = OutputAssemblerNode(llm=self.llm)
        
        # Build the graph
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the 3-node renderer graph with conditional edges"""
        graph_builder = StateGraph(RendererState)
        
        # Add nodes
        graph_builder.add_node("draft_or_fix_code", self._draft_or_fix_wrapper)
        graph_builder.add_node("sandbox_runner", self._sandbox_runner_wrapper)
        graph_builder.add_node("output_assembler", self._output_assembler_wrapper)
        
        # Add edges
        # Start -> DraftOrFixCode
        graph_builder.add_edge(START, "draft_or_fix_code")
        
        # DraftOrFixCode -> conditional based on validation
        graph_builder.add_conditional_edges(
            "draft_or_fix_code",
            self._check_draft_result,
            {
                "retry": "draft_or_fix_code",  # Loop back on validation error
                "continue": "sandbox_runner",   # Continue on success
                "fail": END                     # Exit on max retries
            }
        )
        
        # SandboxRunner -> conditional based on execution
        graph_builder.add_conditional_edges(
            "sandbox_runner",
            self._check_sandbox_result,
            {
                "retry": "draft_or_fix_code",   # Loop back to fix code
                "success": "output_assembler",   # Continue to output
                "fail": END                      # Exit on max retries
            }
        )
        
        # OutputAssembler -> END (terminal node)
        graph_builder.add_edge("output_assembler", END)
        
        return graph_builder.compile()
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process visualization rendering using LangGraph sub-graph
        
        Args:
            state: Current analysis state
            
        Returns:
            Dictionary containing plot_image_path, llm_code_used, and warnings
        """
        self.log_info("Starting LLM-powered renderer graph")
        
        if state["error_message"] or not state["chart_specification"]:
            return {"plot_image_path": "", "llm_code_used": "", "warnings": []}
        
        try:
            # Gather ingredients for the sub-graph
            ingredients = self._gather_ingredients(state)
            
            # Initialize renderer state
            initial_state = {
                "ingredients": ingredients,
                "generated_code": "",
                "error_msg": None,
                "retry_count": 0,
                "warnings": [],
                "plot_image_path": "",
                "plot_html_path": "",
                "plot_png_path": "",
                "llm_code_used": ""
            }
            
            # Run the sub-graph
            result = self.graph.invoke(initial_state)
            
            # Handle final result
            if result.get("plot_html_path") or result.get("plot_png_path"):
                # Success path - return both HTML and PNG paths
                return {
                    "plot_image_path": result.get("plot_html_path", ""),  # Primary path (HTML for interactivity)
                    "plot_html_path": result.get("plot_html_path", ""),
                    "plot_png_path": result.get("plot_png_path", ""),
                    "llm_code_used": result["llm_code_used"],
                    "warnings": result.get("warnings", [])
                }
            else:
                # Failed after all retries
                error_msg = result.get("error_msg", "Unknown error")
                self.log_error(f"Renderer failed after {result.get('retry_count', 0)} retries: {error_msg}")
                
                return {
                    "plot_image_path": "",
                    "plot_html_path": "",
                    "plot_png_path": "",
                    "llm_code_used": result.get("generated_code", ""),
                    "warnings": [f"Visualization failed after {result.get('retry_count', 0)} retries: {error_msg}"]
                }
                
        except Exception as e:
            self.log_error(f"Renderer graph failed: {str(e)}")
            return {
                "plot_image_path": "",
                "plot_html_path": "",
                "plot_png_path": "",
                "llm_code_used": "",
                "warnings": [f"Renderer error: {str(e)}"]
            }
    
    def _gather_ingredients(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Gather all ingredients needed for code generation
        
        Returns:
            Dictionary with user_ask, data_snapshot, chart_specification, etc.
        """
        # User ask and chart spec
        user_ask = state["user_prompt"]
        chart_spec = state["chart_specification"]
        
        # Data snapshot
        df = pd.read_csv(state["csv_file_path"])
        data_snapshot = {
            "columns": list(df.columns),
            "dtypes": df.dtypes.astype(str).to_dict(),
            "sample_values": df.head(3).to_dict('records'),
            "shape": df.shape
        }
        
        # Output paths - generate both HTML and PNG
        spec_hash = hashlib.md5(json.dumps(chart_spec, sort_keys=True).encode()).hexdigest()[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = f"llm_chart_{spec_hash}_{timestamp}"
        
        html_path = PLOTS_DIR / f"{base_filename}.html"
        png_path = PLOTS_DIR / f"{base_filename}.png"
        
        return {
            "user_ask": user_ask,
            "chart_specification": chart_spec,
            "data_snapshot": data_snapshot,
            "style_dictionary": STYLE_DICTIONARY,
            "html_output_path": str(html_path),
            "png_output_path": str(png_path),
            "csv_path": state["csv_file_path"]
        }
    
    # Node wrappers to maintain state updates
    def _draft_or_fix_wrapper(self, state: RendererState) -> Dict[str, Any]:
        """Wrapper for draft_or_fix_code node"""
        result = self.draft_or_fix.process(state)
        # Merge results into state
        return {**state, **result}
    
    def _sandbox_runner_wrapper(self, state: RendererState) -> Dict[str, Any]:
        """Wrapper for sandbox_runner node"""
        result = self.sandbox_runner.process(state)
        # Merge results into state
        return {**state, **result}
    
    def _output_assembler_wrapper(self, state: RendererState) -> Dict[str, Any]:
        """Wrapper for output_assembler node"""
        result = self.output_assembler.process(state)
        # Merge results into state
        return {**state, **result}
    
    # Conditional edge functions
    def _check_draft_result(self, state: RendererState) -> str:
        """
        Check result of draft_or_fix_code node
        
        Returns:
            "retry" if validation failed and retries left
            "continue" if validation passed
            "fail" if max retries reached
        """
        if state.get("error_msg"):
            if state.get("retry_count", 0) < MAX_RETRIES:
                self.log_info(f"Draft validation failed, retry {state['retry_count']}/{MAX_RETRIES}")
                return "retry"
            else:
                self.log_error(f"Max retries reached in draft phase")
                return "fail"
        else:
            return "continue"
    
    def _check_sandbox_result(self, state: RendererState) -> str:
        """
        Check result of sandbox_runner node
        
        Returns:
            "retry" if execution failed and retries left
            "success" if execution succeeded
            "fail" if max retries reached
        """
        if state.get("error_msg"):
            if state.get("retry_count", 0) < MAX_RETRIES:
                self.log_info(f"Sandbox execution failed, retry {state['retry_count']}/{MAX_RETRIES}")
                return "retry"
            else:
                self.log_error(f"Max retries reached in sandbox phase")
                return "fail"
        else:
            return "success" 