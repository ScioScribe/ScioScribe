"""
Nodes Package for Analysis Agent

This package contains all the modular node implementations for the LangGraph-based
visualization agent. Each node represents a specific step in the 6-node pipeline:

1. Input Loader - Validates and loads experiment plans and datasets
2. Plan Parser - Extracts structured information from experiment plans  
3. Data Profiler - Analyzes dataset structure and generates statistics
4. Chart Chooser - Selects appropriate visualization using LLM
5. Renderer - Generates Matplotlib visualizations (now a multi-node graph)
6. Response Composer - Creates explanatory text and manages memory

Additional nodes for the Renderer sub-graph:
- Draft or Fix Code - Generates/fixes matplotlib code with validation
- Sandbox Runner - Executes code in secure sandbox
- Output Assembler - Assembles final output on success
"""

from .base_node import BaseNode
from .input_loader import InputLoaderNode
from .plan_parser import PlanParserNode
from .data_profiler import DataProfilerNode
from .chart_chooser import ChartChooserNode
from .renderer import RendererNode
from .response_composer import ResponseComposerNode
from .draft_or_fix_code import DraftOrFixCodeNode
from .sandbox_runner import SandboxRunnerNode
from .output_assembler import OutputAssemblerNode

__all__ = [
    # Base classes
    "BaseNode",
    
    # Main pipeline nodes
    "InputLoaderNode",
    "PlanParserNode", 
    "DataProfilerNode",
    "ChartChooserNode",
    "RendererNode",
    "ResponseComposerNode",
    
    # Renderer sub-graph nodes
    "DraftOrFixCodeNode",
    "SandboxRunnerNode",
    "OutputAssemblerNode"
] 