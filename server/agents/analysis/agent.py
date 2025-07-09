"""
Analysis Agent using LangGraph - Specialized Visualization Agent System

This module implements a LangGraph-based visualization agent that processes
experiment plans and datasets to generate analytical visualizations using
specialized AI agents following Crew AI principles.

The agent orchestrates a 6-node pipeline of specialized experts:
1. Input Validation Specialist - Expert data validator and quality controller
2. Experiment Plan Analyst - Research methodology and plan interpretation expert
3. Data Profiling Specialist - Statistical analysis and data characterization expert
4. Visualization Strategy Expert - Chart selection and design methodology specialist
5. Code Generation Specialist - Plotly visualization code generation expert
6. Scientific Communication Expert - Explanatory text and memory management specialist

Each agent has a specific role, expertise domain, and clear objectives to ensure
high-quality, contextually appropriate visualizations for scientific analysis.
"""

import os
import logging
from typing import Annotated, List, Dict, Any, Optional
from typing_extensions import TypedDict
from dataclasses import dataclass, asdict


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
    Specialized Agent Communication State Schema
    
    This state facilitates seamless communication between specialized agents,
    ensuring each expert receives the context they need and can pass their
    insights to the next specialist in the pipeline.
    
    AGENT COMMUNICATION FLOW:
    
    Input Validation Specialist → Research Methodology Analyst:
    - messages: Conversation history and agent communications
    - user_prompt: Original analytical question or visualization request
    - experiment_plan_content: Experiment plan content as text
    - csv_data_content: CSV data content as text
    - memory: Context for iterative refinement and learning
    
    Research Methodology Analyst → Statistical Data Profiling Expert:
    - plan_text: Raw experiment plan content for context
    - structured_plan: Extracted experimental context and objectives
    
    Statistical Data Profiling Expert → Visualization Design Strategist:
    - data_schema: Detailed column types, statistics, and data characteristics
    - data_sample: Representative sample rows for design decisions
    
    Visualization Design Strategist → Plotly Code Generation Expert:
    - chart_specification: Optimal chart type and design specifications
    
    Plotly Code Generation Expert → Scientific Communication Expert:
    - plot_image_path: Primary path to generated visualization
    - plot_html_path: Interactive HTML visualization for exploration
    - plot_png_path: Static PNG image for reports and presentations
    - html_content: Interactive HTML content as string
    - llm_code_used: Generated code for transparency and debugging
    - warnings: Technical caveats or limitations
    
    Scientific Communication Expert → Final Output:
    - explanation: Clear, insightful explanation of findings and methodology
    - error_message: Error information if any specialist encounters issues
    """
    messages: Annotated[List, add_messages]
    user_prompt: str
    experiment_plan_content: str
    csv_data_content: str
    memory: Dict[str, Any]
    plan_text: str
    structured_plan: Dict[str, Any]
    data_schema: Dict[str, Any]
    data_sample: List[Dict[str, Any]]
    chart_specification: Dict[str, Any]
    plot_image_path: str
    plot_html_path: str
    plot_png_path: str
    html_content: str
    llm_code_used: str
    warnings: List[str]
    explanation: str
    error_message: str


class AnalysisAgent:
    """
    LangGraph-based Specialized Visualization Agent System
    
    ROLE: Senior Data Visualization Orchestrator
    
    GOAL: Coordinate a team of specialized AI agents to transform raw scientific data
    and experiment plans into publication-ready, interactive visualizations that
    clearly communicate analytical insights.
    
    BACKSTORY: You are an experienced data visualization director who has spent years
    building scientific visualization pipelines. You understand that effective data
    visualization requires multiple specialized skills - from data validation and
    statistical analysis to design principles and scientific communication. You
    orchestrate a team of specialized agents, each with deep expertise in their
    domain, to ensure every visualization is accurate, insightful, and professionally
    presented.
    
    EXPERTISE DOMAINS:
    - Scientific data visualization methodology
    - Research workflow coordination
    - Quality assurance and validation
    - Multi-agent system orchestration
    - Interactive visualization design
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
        
        logger.info(f"🎯 Specialized Visualization Agent System initialized with {model_provider}:{model_name}")
        logger.info("👥 Agent Team Assembled:")
        logger.info("   🔍 Input Validation Specialist - Data integrity and quality control")
        logger.info("   📋 Research Methodology Analyst - Experimental context extraction")
        logger.info("   📊 Statistical Data Profiling Expert - Data characterization")
        logger.info("   🎨 Visualization Design Strategist - Chart selection and design")
        logger.info("   ⚡ Plotly Code Generation Expert - Interactive visualization development")
        logger.info("   ✍️ Scientific Communication Expert - Insight explanation and communication")
        logger.info("🚀 System ready for publication-quality visualization generation")
    
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
        """
        Initialize specialized agent nodes with role-based context and expertise domains
        
        Each node is configured as a specialized expert with specific responsibilities,
        following Crew AI principles for maximum effectiveness.
        """
        # Input Validation Specialist
        self.input_loader = InputLoaderNode(
            llm=self.llm,
            role_context={
                "role": "Senior Data Validation Specialist",
                "goal": "Ensure data integrity and experiment plan validity before analysis",
                "backstory": "You are a meticulous data quality expert with 15+ years of experience in scientific data validation. You have seen countless data issues that compromise analysis results, so you thoroughly validate file formats, data structures, and experiment plan coherence before allowing any analysis to proceed.",
                "expertise": ["Data quality assessment", "File format validation", "Experiment plan verification", "Error detection and reporting"]
            }
        )
        
        # Experiment Plan Analyst
        self.plan_parser = PlanParserNode(
            llm=self.llm,
            role_context={
                "role": "Research Methodology Analyst",
                "goal": "Extract and structure experimental context to guide visualization decisions",
                "backstory": "You are a research methodology expert who has designed and analyzed hundreds of scientific experiments. You understand how experimental design influences visualization requirements and can extract key insights from experiment plans to inform appropriate visual analysis approaches.",
                "expertise": ["Experimental design analysis", "Research methodology", "Hypothesis extraction", "Variable relationship identification"]
            }
        )
        
        # Data Profiling Specialist
        self.data_profiler = DataProfilerNode(
            llm=self.llm,
            role_context={
                "role": "Statistical Data Profiling Expert",
                "goal": "Characterize dataset structure and statistical properties to inform visualization strategy",
                "backstory": "You are a statistician with deep expertise in exploratory data analysis. You can quickly identify data types, distributions, correlations, and patterns that determine the most appropriate visualization approaches. Your statistical insights directly influence chart selection and design decisions.",
                "expertise": ["Statistical analysis", "Data type detection", "Distribution analysis", "Correlation identification", "Outlier detection"]
            }
        )
        
        # Visualization Strategy Expert
        self.chart_chooser = ChartChooserNode(
            llm=self.llm,
            role_context={
                "role": "Visualization Design Strategist",
                "goal": "Select optimal chart types and design specifications based on data characteristics and analytical objectives",
                "backstory": "You are a data visualization expert who combines statistical knowledge with design principles. You understand that different data types and analytical questions require specific visualization approaches. Your decisions are guided by both statistical appropriateness and visual clarity principles.",
                "expertise": ["Chart type selection", "Visual design principles", "Statistical visualization", "Interactive design", "Data-driven design decisions"]
            }
        )
        
        # Code Generation Specialist
        self.renderer = RendererNode(
            llm=self.llm,
            role_context={
                "role": "Plotly Code Generation Expert",
                "goal": "Generate clean, efficient, and visually appealing Plotly code that brings visualization specifications to life",
                "backstory": "You are a skilled visualization developer with mastery of Plotly and modern interactive visualization techniques. You write clean, maintainable code that creates publication-quality visualizations. You understand both the technical capabilities of Plotly and the design principles that make visualizations effective.",
                "expertise": ["Plotly Express proficiency", "Interactive visualization development", "Code optimization", "Visual styling", "Error handling"]
            }
        )
        
        # Scientific Communication Expert
        self.response_composer = ResponseComposerNode(
            llm=self.llm,
            role_context={
                "role": "Scientific Communication Specialist",
                "goal": "Craft clear, insightful explanations that help users understand their data and visualization choices",
                "backstory": "You are a science communication expert who excels at translating complex analytical results into clear, actionable insights. You understand that effective visualization is not just about creating charts, but about helping users understand what their data reveals and why specific visualization choices were made.",
                "expertise": ["Scientific writing", "Data interpretation", "Insight communication", "Memory management", "User guidance"]
            }
        )
    
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
    
    # Specialized Agent Coordination Methods
    def _input_loader_wrapper(self, state: AnalysisState) -> Dict[str, Any]:
        """
        Coordinate with Input Validation Specialist
        
        HANDOFF: The Data Validation Specialist receives raw inputs and ensures
        data integrity before any analysis begins. Critical for preventing
        downstream errors and ensuring reliable results.
        """
        logger.info("🔍 Input Validation Specialist: Ensuring data integrity and experiment plan validity")
        return self.input_loader.process(state)
    
    def _plan_parser_wrapper(self, state: AnalysisState) -> Dict[str, Any]:
        """
        Coordinate with Research Methodology Analyst
        
        HANDOFF: The Research Methodology Analyst receives validated inputs and
        extracts structured experimental context to guide visualization decisions.
        """
        logger.info("📋 Research Methodology Analyst: Extracting experimental context and research objectives")
        return self.plan_parser.process(state)
    
    def _data_profiler_wrapper(self, state: AnalysisState) -> Dict[str, Any]:
        """
        Coordinate with Statistical Data Profiling Expert
        
        HANDOFF: The Statistical Expert receives structured experiment context and
        characterizes dataset properties to inform visualization strategy.
        """
        logger.info("📊 Statistical Data Profiling Expert: Analyzing dataset structure and statistical properties")
        return self.data_profiler.process(state)
    
    def _chart_chooser_wrapper(self, state: AnalysisState) -> Dict[str, Any]:
        """
        Coordinate with Visualization Design Strategist
        
        HANDOFF: The Visualization Strategist receives statistical insights and
        selects optimal chart types based on data characteristics and analytical goals.
        """
        logger.info("🎨 Visualization Design Strategist: Selecting optimal chart specification and design approach")
        return self.chart_chooser.process(state)
    
    def _renderer_wrapper(self, state: AnalysisState) -> Dict[str, Any]:
        """
        Coordinate with Plotly Code Generation Expert
        
        HANDOFF: The Code Generation Expert receives visualization specifications
        and creates clean, efficient Plotly code to bring the design to life.
        """
        logger.info("⚡ Plotly Code Generation Expert: Generating interactive visualization code")
        result = self.renderer.process(state)
        
        # Debug logging to track HTML content flow
        html_content = result.get("html_content", "")
        logger.info(f"📊 Renderer returned HTML content length: {len(html_content)}")
        
        return result
    
    def _response_composer_wrapper(self, state: AnalysisState) -> Dict[str, Any]:
        """
        Coordinate with Scientific Communication Expert
        
        HANDOFF: The Communication Expert receives the completed visualization
        and crafts clear explanations to help users understand their results.
        """
        logger.info("✍️ Scientific Communication Expert: Crafting insightful explanations and managing context")
        
        # Debug logging to track HTML content flow
        html_content = state.get("html_content", "")
        logger.info(f"📊 Response composer received HTML content length: {len(html_content)}")
        
        result = self.response_composer.process(state)
        
        # Debug logging to track HTML content in final result
        final_html = result.get("html_content", "")
        logger.info(f"📊 Response composer returning HTML content length: {len(final_html)}")
        
        return result
    
    def _build_specific_response_message(self,
                                       user_prompt: str,
                                       chart_spec: Dict[str, Any],
                                       structured_plan: Dict[str, Any],
                                       data_schema: Dict[str, Any],
                                       html_content: str,
                                       warnings: List[str]) -> str:
        """
        Build a specific response message based on the actual agent state and results
        
        Args:
            user_prompt: Original user request
            chart_spec: Chart specification generated by the visualization strategist
            structured_plan: Experimental plan extracted by research analyst
            data_schema: Data characteristics identified by statistical expert
            html_content: Generated HTML visualization
            warnings: Any warnings from the pipeline
            
        Returns:
            Specific, contextual response message
        """
        if not html_content or not chart_spec:
            return f"I wasn't able to create a visualization for your request: '{user_prompt}'. Please check your data and try again."
        
        # Extract key information from state
        chart_type = chart_spec.get('chart_type', 'visualization')
        x_column = chart_spec.get('x_column', 'X-axis')
        y_column = chart_spec.get('y_column', 'Y-axis')
        hue_column = chart_spec.get('hue_column')
        title = chart_spec.get('title', 'Data Visualization')
        
        # Get data information
        data_shape = data_schema.get('shape', [0, 0])
        column_count = data_shape[1] if len(data_shape) > 1 else 0
        row_count = data_shape[0] if len(data_shape) > 0 else 0
        
        # Get analytical context
        analytical_goal = structured_plan.get('analytical_goal', 'explore the data')
        research_questions = structured_plan.get('research_questions', [])
        
        # Build specific response message
        message_parts = []
        
        # Opening - directly address the user's request
        message_parts.append(f"✅ **Generated {chart_type} visualization** for your request: \"{user_prompt}\"")
        
        # Chart details
        message_parts.append(f"📊 **Visualization Details:**")
        message_parts.append(f"- **Chart Type**: {chart_type.title()}")
        message_parts.append(f"- **Title**: {title}")
        message_parts.append(f"- **X-Axis**: {x_column.replace('_', ' ').title()}")
        message_parts.append(f"- **Y-Axis**: {y_column.replace('_', ' ').title()}")
        
        if hue_column:
            message_parts.append(f"- **Grouped by**: {hue_column.replace('_', ' ').title()}")
        
        # Data context
        if row_count > 0:
            message_parts.append(f"📈 **Data**: Analyzed {row_count:,} rows across {column_count} columns")
        
        # Analytical context
        if analytical_goal and analytical_goal != 'explore the data':
            message_parts.append(f"🎯 **Analysis Goal**: {analytical_goal}")
        
        if research_questions:
            questions_text = research_questions[0] if len(research_questions) == 1 else f"{len(research_questions)} research questions"
            message_parts.append(f"🔬 **Research Focus**: {questions_text}")
        
        # Technical details
        message_parts.append(f"⚡ **Interactive Features**: Hover for details, zoom, pan, and download options available")
        
        # Warnings if any
        if warnings:
            message_parts.append(f"⚠️ **Notes**: {'; '.join(warnings)}")
        
        # Closing
        message_parts.append(f"🎨 The visualization is now ready for exploration and analysis!")
        
        return "\n".join(message_parts)
    
    def generate_visualization(self, 
                             user_prompt: str,
                             experiment_plan_content: str,
                             csv_data_content: str,
                             memory: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Orchestrate specialized agents to generate publication-quality visualizations
        
        MISSION: Transform user's analytical question into a compelling, accurate, and
        insightful visualization by coordinating a team of specialized AI agents.
        
        APPROACH: Each agent in the pipeline has specific expertise and responsibilities:
        - Input Validation ensures data integrity and prevents downstream errors
        - Research Analyst extracts experimental context to guide visualization decisions
        - Statistical Expert characterizes data properties for appropriate chart selection
        - Visualization Strategist selects optimal chart types and design specifications
        - Code Generation Expert creates clean, efficient Plotly implementation
        - Communication Expert crafts clear explanations of results and insights
        
        QUALITY STANDARDS:
        - All outputs must be scientifically accurate and methodologically sound
        - Visualizations must be publication-ready with professional aesthetics
        - Code must be clean, efficient, and follow best practices
        - Explanations must be clear, insightful, and actionable
        
        Args:
            user_prompt: Natural language analytical question or visualization request
            experiment_plan_content: Experiment plan content as text
            csv_data_content: CSV data content as text for analysis
            memory: Optional memory object for iterative refinement and context retention
            
        Returns:
            Dictionary containing:
            - html_content: Interactive HTML visualization content as string
            - memory: Updated memory with context for future iterations
            - llm_code_used: Generated code for transparency and debugging
            - warnings: Any important caveats or limitations
        """
        logger.info(f"🎯 MISSION: Generating publication-quality visualization for: {user_prompt}")
        logger.info("🚀 Initializing specialized agent coordination pipeline")
        
        # Initialize comprehensive state with clear objectives for each agent
        initial_state = {
            "messages": [],
            "user_prompt": user_prompt,
            "experiment_plan_content": experiment_plan_content,
            "csv_data_content": csv_data_content,
            "memory": memory or {},
            "plan_text": "",
            "structured_plan": {},
            "data_schema": {},
            "data_sample": [],
            "chart_specification": {},
            "plot_image_path": "",
            "plot_html_path": "",
            "plot_png_path": "",
            "html_content": "",
            "llm_code_used": "",
            "warnings": [],
            "explanation": "",
            "error_message": ""
        }
        
        # Execute coordinated agent pipeline
        logger.info("🔄 Executing specialized agent coordination pipeline")
        result = self.graph.invoke(initial_state)
        
        # Build specific response message based on agent state
        html_content = result.get("html_content", "")
        chart_spec = result.get("chart_specification", {})
        structured_plan = result.get("structured_plan", {})
        data_schema = result.get("data_schema", {})
        warnings = result.get("warnings", [])
        
        # Create specific response message based on what was actually generated
        response_message = self._build_specific_response_message(
            user_prompt=user_prompt,
            chart_spec=chart_spec,
            structured_plan=structured_plan,
            data_schema=data_schema,
            html_content=html_content,
            warnings=warnings
        )
        
        logger.info("✅ Visualization generation completed successfully")
        logger.info(f"📊 Final HTML content length: {len(html_content)}")
        logger.info(f"💬 Generated specific response message: {response_message[:100]}...")
        
        return {
            "html_content": html_content,
            "explanation": response_message,
            "memory": result.get("memory", {}),
            "llm_code_used": result.get("llm_code_used", ""),
            "warnings": warnings
        }


def create_analysis_agent(model_provider: str = "openai", model_name: str = "gpt-4.1") -> AnalysisAgent:
    """
    Factory function to create a Specialized Visualization Agent System
    
    CREATES: A sophisticated multi-agent system that transforms raw scientific data
    into publication-quality, interactive visualizations through coordinated
    specialized AI agents.
    
    AGENT TEAM COMPOSITION:
    - Input Validation Specialist: Ensures data integrity and quality
    - Research Methodology Analyst: Extracts experimental context
    - Statistical Data Profiling Expert: Characterizes data properties
    - Visualization Design Strategist: Selects optimal chart approaches
    - Plotly Code Generation Expert: Creates clean, efficient code
    - Scientific Communication Expert: Crafts clear explanations
    
    CAPABILITIES:
    - Publication-ready interactive visualizations
    - Scientifically accurate chart selection
    - Context-aware design decisions
    - Clean, maintainable code generation
    - Clear, insightful explanations
    - Iterative refinement support
    
    Args:
        model_provider: The LLM provider to use (openai, anthropic, etc.)
        model_name: The specific model to use for agent coordination
        
    Returns:
        Fully configured AnalysisAgent system with specialized agent team
    """
    return AnalysisAgent(model_provider=model_provider, model_name=model_name) 