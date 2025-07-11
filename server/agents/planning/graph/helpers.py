"""
Helper utility functions for the experiment planning graph system.

This module provides common utility functions used across the planning system
for input processing, section determination, and other shared functionality.
"""

from typing import Dict, List, Any
import logging

from ..state import ExperimentPlanState, PLANNING_STAGES
from ..llm_config import get_llm_manager, LLMConfigError  # noqa: E501 – functional import for new utilities
from langchain_core.messages import SystemMessage, HumanMessage  # type: ignore

logger = logging.getLogger(__name__)


def get_latest_user_input(state: ExperimentPlanState) -> str:
    """
    Extract the latest user input from chat history.
    
    This helper function searches through the chat history to find
    the most recent user message for processing by agents.
    
    Args:
        state: Current experiment plan state
        
    Returns:
        Latest user input content or empty string if none found
    """
    chat_history = state.get('chat_history', [])
    
    # Find the most recent user message
    for message in reversed(chat_history):
        if message.get('role') == 'user':
            return message.get('content', '')
    
    return ''


def determine_section_to_edit(user_input: str, state: ExperimentPlanState) -> str:
    """
    Determine which section the user wants to edit based on their input.
    
    This function analyzes user input to identify which planning stage
    they want to navigate to for editing. Uses enhanced keyword matching 
    and context analysis with fallback logic.
    
    Args:
        user_input: User's input message
        state: Current experiment plan state
        
    Returns:
        Planning stage name to navigate to
    """
    # --------------------------------------------------------
    # 1. Attempt LLM-based classification (preferred)
    # --------------------------------------------------------
    llm_section = _classify_section_with_llm(user_input, state)
    if llm_section:
        return llm_section

    # --------------------------------------------------------
    # 2. Heuristic keyword fallback (legacy logic)
    # --------------------------------------------------------

    user_input_lower = user_input.lower().strip()
    
    # Enhanced section keywords mapping with more comprehensive coverage
    section_keywords = {
        "objective_setting": [
            "objective", "goal", "hypothesis", "purpose", "aim", "research question",
            "what we're trying", "what we want", "main goal", "research aim",
            "study objective", "experimental objective", "month", "week", "day", "period",
            "timeline", "duration", "time frame"
        ],
        "variable_identification": [
            "variable", "independent", "dependent", "control", "measure", "measurement",
            "what we're measuring", "what we're changing", "factors", "parameters",
            "iv", "dv", "controlled variable", "confounding",
            # Common variable names and phrases
            "food source", "temperature", "ph", "concentration", "dose", "treatment",
            "control variable", "independent variable", "dependent variable",
            "remove", "add", "modify variable", "change variable", "variable type",
            "co2", "oxygen", "light", "humidity", "pressure", "time point"
        ],
        "experimental_design": [
            "design", "groups", "control group", "experimental group", "sample", 
            "statistical", "power", "replicates", "randomization", "treatment",
            "control condition", "experimental condition", "group size", "n=",
            "power analysis", "sample size", "biological replicates", "technical replicates"
        ],
        "methodology_protocol": [
            "protocol", "method", "procedure", "steps", "materials", "equipment",
            "how to", "protocol steps", "experimental procedure", "methodology",
            "materials list", "reagents", "instruments", "step by step",
            "incubation", "centrifuge", "pipette", "buffer", "solution"
        ],
        "data_planning": [
            "data", "analysis", "statistics", "visualization", "pitfalls", "collection",
            "statistical test", "data analysis", "graphs", "charts", "results",
            "statistical analysis", "data collection", "potential problems",
            "anova", "t-test", "regression", "correlation"
        ],
        "final_review": [
            "review", "export", "summary", "complete", "finalize", "overview",
            "final plan", "export plan", "summary report", "complete plan",
            "plan review", "final summary"
        ]
    }
    
    # Check for specific section keywords with scoring
    section_scores = {}
    for section, keywords in section_keywords.items():
        score = sum(1 for keyword in keywords if keyword in user_input_lower)
        if score > 0:
            section_scores[section] = score
    
    # If we found matches, return the highest scoring section
    if section_scores:
        best_section = max(section_scores, key=section_scores.get)
        logger.info(f"Determined section to edit: {best_section} (score: {section_scores[best_section]})")
        return best_section
    
    # Context-based fallback: analyze what might be incomplete
    incomplete_stages = []
    
    # Check each stage for completeness
    if not state.get('experiment_objective') or not state.get('hypothesis'):
        incomplete_stages.append("objective_setting")
    
    if not state.get('independent_variables') or not state.get('dependent_variables'):
        incomplete_stages.append("variable_identification")
    
    if not state.get('experimental_groups') or not state.get('control_groups'):
        incomplete_stages.append("experimental_design")
    
    if not state.get('methodology_steps') or not state.get('materials_equipment'):
        incomplete_stages.append("methodology_protocol")
    
    if not state.get('data_collection_plan') or not state.get('data_analysis_plan'):
        incomplete_stages.append("data_planning")
    
    # If there are incomplete stages, suggest the first one
    if incomplete_stages:
        suggested_section = incomplete_stages[0]
        logger.info(f"No specific section identified, suggesting incomplete stage: {suggested_section}")
        return suggested_section
    
    # Final fallback: if everything seems complete, go to review
    if all([
        state.get('experiment_objective'),
        state.get('independent_variables'),
        state.get('experimental_groups'),
        state.get('methodology_steps'),
        state.get('data_collection_plan')
    ]):
        logger.info("All stages appear complete, directing to final review")
        return "final_review"
    
    # Ultimate fallback
    logger.info("No specific section identified, defaulting to objective_setting")
    return "objective_setting"


def get_stage_routing_map() -> Dict[str, str]:
    """
    Get the mapping from planning stages to routing keys.
    
    Returns:
        Dictionary mapping planning stages to router keys
    """
    return {
        "objective_setting": "objective",
        "variable_identification": "variables",
        "experimental_design": "design",
        "methodology_protocol": "methodology",
        "data_planning": "data_planning",
        "final_review": "review"
    }


def get_stage_descriptions() -> Dict[str, str]:
    """
    Get human-readable descriptions for each planning stage.
    
    Returns:
        Dictionary mapping planning stages to descriptions
    """
    return {
        "objective_setting": "Define research objectives and hypothesis",
        "variable_identification": "Identify independent, dependent, and control variables",
        "experimental_design": "Design experimental groups and sample sizes",
        "methodology_protocol": "Create step-by-step procedures and materials list",
        "data_planning": "Plan data collection and analysis methods",
        "final_review": "Review and finalize the complete experiment plan"
    }


def get_completion_keywords() -> Dict[str, List[str]]:
    """
    Get keywords used to identify completion or approval intents.
    
    Returns:
        Dictionary with approval and edit keywords
    """
    return {
        "approval": ["approve", "approved", "yes", "confirm", "complete", "finalize"],
        "edit": ["edit", "modify", "change", "update", "revise", "go back"]
    }


def extract_user_intent(user_input: str) -> str:
    """
    Extract the user's intent from their input message using improved NLP.
    
    Args:
        user_input: User's input message
        
    Returns:
        Intent category: 'approval', 'edit', or 'unclear'
    """
    logger.info(f"[INTENT] Classifying user input: '{user_input}'")
    
    # --------------------------------------------------------
    # 1. Attempt LLM-based intent classification
    # --------------------------------------------------------
    llm_intent = _classify_intent_with_llm(user_input)
    if llm_intent:
        logger.info(f"[INTENT] LLM classification result: {llm_intent}")
        return llm_intent
    
    logger.info("[INTENT] LLM classification failed, using keyword fallback")

    # --------------------------------------------------------
    # 2. Heuristic keyword analysis (fallback)
    # --------------------------------------------------------

    user_input_lower = user_input.lower().strip()
    
    # Enhanced keyword sets for better detection
    approval_keywords = [
        "approve", "approved", "yes", "confirm", "complete", "finalize", 
        "done", "finished", "good", "looks good", "perfect", "ready",
        "export", "save", "accept", "ok", "okay", "great", "excellent",
        "thanks", "thank you", "that's all", "all set"
    ]
    
    edit_keywords = [
        "edit", "modify", "change", "update", "revise", "go back",
        "fix", "adjust", "improve", "refine", "alter", "correct",
        "want to change", "need to", "let me", "can we", "should we",
        "instead", "rather than", "could we", "make it", "but", "however", "actually"
    ]
    
    # Strong approval phrases (higher priority)
    strong_approval_phrases = [
        "looks good", "looks great", "that's perfect", "ready to go",
        "ready to export", "ready to save", "all done", "we're done",
        "that's it", "that's all", "thank you"
    ]
    
    # Strong edit phrases (higher priority)
    strong_edit_phrases = [
        "instead of", "rather than", "could we make it", "can we change",
        "what if we", "but what about", "however", "actually"
    ]
    
    # Check for strong edit phrases first (these are very clear indicators)
    for phrase in strong_edit_phrases:
        if phrase in user_input_lower:
            logger.info(f"[INTENT] Strong edit phrase detected: '{phrase}' -> edit")
            return "edit"
    
    # Check for strong approval phrases
    for phrase in strong_approval_phrases:
        if phrase in user_input_lower:
            logger.info(f"[INTENT] Strong approval phrase detected: '{phrase}' -> approval")
            return "approval"
    
    # Check for explicit approval/edit keywords
    approval_count = sum(1 for keyword in approval_keywords if keyword in user_input_lower)
    edit_count = sum(1 for keyword in edit_keywords if keyword in user_input_lower)
    
    logger.info(f"[INTENT] Keyword counts - approval: {approval_count}, edit: {edit_count}")
    
    # If user mentions specific sections, likely wants to edit
    section_mentions = ["objective", "variable", "design", "methodology", "data", "protocol"]
    section_mentioned = any(section in user_input_lower for section in section_mentions)
    
    if section_mentioned and edit_count > 0:
        logger.info(f"[INTENT] Section mention + edit keywords detected -> edit")
        return "edit"
    
    # Determine intent based on keyword counts
    if edit_count > approval_count and edit_count > 0:
        logger.info(f"[INTENT] Edit keywords dominate -> edit")
        return "edit"
    elif approval_count > edit_count and approval_count > 0:
        logger.info(f"[INTENT] Approval keywords dominate -> approval")
        return "approval"
    elif approval_count > 0:
        logger.info(f"[INTENT] Some approval keywords found -> approval")
        return "approval"
    else:
        logger.info(f"[INTENT] No clear intent detected -> unclear")
        return "unclear"


def validate_stage_name(stage_name: str) -> bool:
    """
    Validate that a stage name is valid.
    
    Args:
        stage_name: Name of the planning stage
        
    Returns:
        True if valid, False otherwise
    """
    return stage_name in PLANNING_STAGES


def get_next_stage(current_stage: str) -> str | None:
    """
    Get the next planning stage after the current one.
    
    Args:
        current_stage: Current planning stage
        
    Returns:
        Next stage name or None if current is the last stage
    """
    try:
        current_index = PLANNING_STAGES.index(current_stage)
        if current_index < len(PLANNING_STAGES) - 1:
            return PLANNING_STAGES[current_index + 1]
        return None
    except ValueError:
        logger.error(f"Invalid current stage: {current_stage}")
        return None


def get_previous_stage(current_stage: str) -> str | None:
    """
    Get the previous planning stage before the current one.
    
    Args:
        current_stage: Current planning stage
        
    Returns:
        Previous stage name or None if current is the first stage
    """
    try:
        current_index = PLANNING_STAGES.index(current_stage)
        if current_index > 0:
            return PLANNING_STAGES[current_index - 1]
        return None
    except ValueError:
        logger.error(f"Invalid current stage: {current_stage}")
        return None


def calculate_progress_percentage(completed_stages: List[str]) -> float:
    """
    Calculate the progress percentage based on completed stages.
    
    Args:
        completed_stages: List of completed stage names
        
    Returns:
        Progress percentage (0.0 to 100.0)
    """
    if not PLANNING_STAGES:
        return 0.0
    
    total_stages = len(PLANNING_STAGES)
    completed_count = len(completed_stages)
    
    return (completed_count / total_stages) * 100.0


def format_stage_name(stage_name: str) -> str:
    """
    Format a stage name for display to users.
    
    Args:
        stage_name: Internal stage name
        
    Returns:
        Formatted stage name for display
    """
    return stage_name.replace('_', ' ').title()


def is_terminal_stage(stage_name: str) -> bool:
    """
    Check if a stage is the terminal (final) stage.
    
    Args:
        stage_name: Name of the planning stage
        
    Returns:
        True if this is the final stage, False otherwise
    """
    return stage_name == PLANNING_STAGES[-1] if PLANNING_STAGES else False


def is_graph_complete(state_snapshot) -> bool:
    """
    Check if the LangGraph has reached completion (END state).
    
    Args:
        state_snapshot: LangGraph state snapshot from aget_state()
        
    Returns:
        True if graph is complete, False otherwise
    """
    if not state_snapshot:
        return False
    
    # If there are no next nodes, the graph has completed
    if not state_snapshot.next:
        return True
    
    # Check if next nodes is empty list (also indicates completion)
    if isinstance(state_snapshot.next, list) and len(state_snapshot.next) == 0:
        return True
    
    return False


def detect_session_completion(session_id: str, graph_components: Dict[str, Any]) -> bool:
    """
    Detect if a planning session has reached completion.
    
    Args:
        session_id: Session identifier
        graph_components: Graph components dictionary
        
    Returns:
        True if session is complete, False otherwise
    """
    try:
        import asyncio
        
        # This is a synchronous wrapper for async detection
        async def _async_detect():
            graph = graph_components["graph"]
            config = graph_components["config"]
            
            state_snapshot = await graph.aget_state(config)
            return is_graph_complete(state_snapshot)
        
        # Run the async function
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're already in an async context, we can't use this approach
            # Return False as fallback
            return False
        else:
            return loop.run_until_complete(_async_detect())
            
    except Exception as e:
        logger.error(f"Error detecting session completion: {e}")
        return False


# ============================================================
# LLM-ASSISTED CLASSIFICATION HELPERS
# ============================================================


def _safe_invoke_llm(messages: list, agent_type: str) -> str | None:
    """Invoke the global LLM manager safely.

    Args:
        messages: A list of LangChain message objects.
        agent_type: A descriptive label for logging/metrics.

    Returns:
        The raw string response from the LLM **or** None if the call fails.
    """
    logger.info("[LLM] Invoking classification LLM for %s", agent_type)
    try:
        manager = get_llm_manager()
        llm = manager.create_llm(agent_type=agent_type, temperature=0.0, max_tokens=64)
        response = manager.invoke_llm(llm, messages, agent_type)
        return response.strip()
    except (LLMConfigError, Exception) as e:  # noqa: BLE001 – broad except used intentionally as a guardrail
        logger.warning(
            "LLM classification failed (%s). Falling back to keyword heuristics.",
            getattr(e, "message", str(e)),
        )
        return None


def _classify_section_with_llm(user_input: str, state: ExperimentPlanState) -> str | None:
    """Use an LLM to map *user_input* to one of the planning stage identifiers.

    The function returns the stage identifier if confident, otherwise *None*.
    """
    stage_list = ", ".join(PLANNING_STAGES)

    system_prompt = (
        "You are a section-routing assistant for an experimental planning system. "
        "Users can request edits to any part of their experiment plan at any time. "
        "Based on their message, determine which planning stage they want to edit:\n\n"
        
        "**objective_setting**: Research objectives, hypotheses, goals, purpose, aims, timelines\n"
        "- Examples: 'change the objective', 'modify the hypothesis', 'make it 6 months instead of 3'\n\n"
        
        "**variable_identification**: Independent, dependent, control variables, measurements, factors\n"
        "- Examples: 'remove the food source control variable', 'add temperature as a variable', 'change the measurement method'\n"
        "- Key indicators: specific variable names, 'control variable', 'independent variable', 'dependent variable'\n\n"
        
        "**experimental_design**: Experimental groups, control groups, sample sizes, replicates, treatments\n"
        "- Examples: 'add another control group', 'change sample size', 'modify the treatment groups'\n\n"
        
        "**methodology_protocol**: Step-by-step procedures, materials, equipment, protocols, methods\n"
        "- Examples: 'change the protocol steps', 'add more materials', 'modify the procedure'\n\n"
        
        "**data_planning**: Data collection methods, statistical analysis, visualization plans\n"
        "- Examples: 'change the statistical test', 'modify data collection', 'update analysis plan'\n\n"
        
        "**final_review**: Overall plan review, export, summary, completion\n"
        "- Examples: 'review the whole plan', 'export the plan', 'final summary'\n\n"
        
        f"Available stages: {stage_list}\n\n"
        
        "IMPORTANT: \n"
        "- If user mentions specific variable names or types (like 'food source', 'temperature', 'pH'), route to variable_identification\n"
        "- If user mentions 'control variable', 'independent variable', or 'dependent variable', route to variable_identification\n"
        "- If user mentions time periods, durations, or objectives, route to objective_setting\n"
        "- Be very specific about variable-related requests\n\n"
        
        "Respond with only the stage identifier (e.g. `variable_identification`). "
        "If none apply clearly, respond with `unknown`."
    )

    # Include current context and incomplete stages for better routing
    incomplete = [s for s in PLANNING_STAGES if not state.get(s.replace("_", ""), None)]
    current_stage = state.get("current_stage", "unknown")
    
    human_msg = (
        f"User message: {user_input}\n\n"
        f"Current stage: {current_stage}\n"
        f"Incomplete stages: {', '.join(incomplete) if incomplete else 'none'}\n\n"
        f"Context: User is currently at the {current_stage} stage and wants to make an edit. "
        f"Which stage should handle their request?"
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_msg),
    ]

    result = _safe_invoke_llm(messages, "routing")
    if result and result in PLANNING_STAGES:
        logger.info(f"[SECTION] LLM classified '{user_input}' -> {result}")
        return result
    
    logger.warning(f"[SECTION] LLM classification failed for '{user_input}', result: {result}")
    return None


def _classify_intent_with_llm(user_input: str) -> str | None:
    """Classify the *user_input* as `approval`, `edit`, or `unclear` using the LLM."""

    system_prompt = (
        "You are an intent classifier for an experimental planning system. "
        "Users are being asked to approve sections of their experiment plan or request changes. "
        "Classify user messages into exactly one category:\n\n"
        
        "**approval**: User agrees to proceed with the current section as-is\n"
        "- Examples: 'approve', 'yes', 'looks good', 'proceed', 'continue', 'ready to move on'\n\n"
        
        "**edit**: User wants to modify or change something in the current section\n"
        "- Examples: 'instead of X, make it Y', 'change the duration', 'can we modify', 'rather than', 'but what if'\n"
        "- Key indicators: 'instead', 'change', 'modify', 'could we', 'can we', 'rather than', 'but', 'however'\n\n"
        
        "**unclear**: User message is ambiguous or doesn't clearly indicate approval or edit intent\n"
        "- Examples: unclear questions, off-topic comments, or ambiguous statements\n\n"
        
        "IMPORTANT: If a user suggests ANY modification, change, or alternative (even while being polite), "
        "classify it as 'edit', not 'approval'. Phrases like 'instead of X could we make it Y' are clearly edit requests.\n\n"
        
        "Respond with only the category name: approval, edit, or unclear"
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"User message: {user_input}"),
    ]

    result = _safe_invoke_llm(messages, "intent")
    if result in {"approval", "edit", "unclear"}:
        return result
    return None 