"""
Helper utility functions for the experiment planning graph system.

This module provides common utility functions used across the planning system
for input processing, section determination, and other shared functionality.
All classification is now 100% LLM-based for maximum accuracy and consistency.
"""

from typing import Dict, List, Any
import logging

from ..state import ExperimentPlanState, PLANNING_STAGES
from ..llm_config import get_llm_manager, LLMConfigError
from langchain_core.messages import SystemMessage, HumanMessage

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
    
    This function uses LLM-based classification to identify which planning stage
    they want to navigate to for editing. Uses enhanced prompts and robust
    error handling to ensure reliable classification.
    
    Args:
        user_input: User's input message
        state: Current experiment plan state
        
    Returns:
        Planning stage name to navigate to
        
    Raises:
        RuntimeError: If LLM classification fails completely
    """
    logger.info(f"[SECTION] Determining section to edit for: '{user_input}'")
    
    # Get current stage for context
    current_stage = state.get("current_stage", "objective_setting")
    logger.info(f"[SECTION] Current stage: {current_stage}")
    
    # Use LLM-based classification with enhanced error handling
    llm_section = _classify_section_with_llm(user_input, state)
    
    if llm_section and llm_section in PLANNING_STAGES:
        logger.info(f"[SECTION] ✅ LLM classified '{user_input}' -> {llm_section}")
        return llm_section
    
    # If LLM classification fails, try with a more direct approach
    logger.warning(f"[SECTION] ⚠️ Primary LLM classification failed (result: {llm_section}), trying fallback approach")
    fallback_section = _classify_section_with_fallback_llm(user_input, state)
    
    if fallback_section and fallback_section in PLANNING_STAGES:
        logger.info(f"[SECTION] ✅ Fallback LLM classified '{user_input}' -> {fallback_section}")
        return fallback_section
    
    # If both approaches fail, make an intelligent guess based on state
    intelligent_guess = _make_intelligent_section_guess(state, user_input)
    logger.warning(f"[SECTION] ⚠️ LLM classification failed completely, using intelligent guess: {intelligent_guess}")
    return intelligent_guess


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


def extract_user_intent(user_input: str) -> str:
    """
    Extract the user's intent from their input message using LLM classification.
    
    Args:
        user_input: User's input message
        
    Returns:
        Intent category: 'approval', 'edit', or 'unclear'
        
    Raises:
        RuntimeError: If LLM classification fails completely
    """
    logger.info(f"[INTENT] Classifying user input: '{user_input}'")
    
    # Use LLM-based intent classification
    llm_intent = _classify_intent_with_llm(user_input)
    
    if llm_intent and llm_intent in {"approval", "edit", "unclear"}:
        logger.info(f"[INTENT] ✅ LLM classified '{user_input}' -> {llm_intent}")
        return llm_intent
    
    # If primary classification fails, try with a more direct approach
    logger.warning(f"[INTENT] ⚠️ Primary LLM classification failed (result: {llm_intent}), trying fallback approach")
    fallback_intent = _classify_intent_with_fallback_llm(user_input)
    
    if fallback_intent and fallback_intent in {"approval", "edit", "unclear"}:
        logger.info(f"[INTENT] ✅ Fallback LLM classified '{user_input}' -> {fallback_intent}")
        return fallback_intent
    
    # If both approaches fail, default to 'unclear' as the safest option
    logger.warning(f"[INTENT] ⚠️ LLM classification failed completely, defaulting to 'unclear'")
    return "unclear"


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


def _safe_invoke_llm(messages: list, agent_type: str, max_retries: int = 2) -> str | None:
    """Invoke the global LLM manager safely with retry logic.

    Args:
        messages: A list of LangChain message objects.
        agent_type: A descriptive label for logging/metrics.
        max_retries: Maximum number of retry attempts.

    Returns:
        The raw string response from the LLM or None if all attempts fail.
    """
    for attempt in range(max_retries + 1):
        try:
            logger.info(f"[LLM] Invoking classification LLM for {agent_type} (attempt {attempt + 1}/{max_retries + 1})")
            manager = get_llm_manager()
            llm = manager.create_llm(agent_type=agent_type, temperature=0.0, max_tokens=64)
            response = manager.invoke_llm(llm, messages, agent_type)
            
            result = response.strip().lower()
            logger.info(f"[LLM] Raw response for {agent_type}: '{result}'")
            return result
            
        except (LLMConfigError, Exception) as e:
            logger.warning(
                f"LLM classification attempt {attempt + 1} failed for {agent_type}: {getattr(e, 'message', str(e))}"
            )
            if attempt == max_retries:
                logger.error(f"All LLM classification attempts failed for {agent_type}")
                return None
    
    return None


def _classify_section_with_llm(user_input: str, state: ExperimentPlanState) -> str | None:
    """Use an LLM to map user_input to one of the planning stage identifiers.

    The function returns the stage identifier if confident, otherwise None.
    """
    current_stage = state.get("current_stage", "objective_setting")
    
    # Create a comprehensive mapping of keywords to stages
    stage_keywords = {
        "objective_setting": [
            "objective", "goal", "purpose", "hypothesis", "research question", "aim", "target",
            "timeline", "duration", "timeframe", "schedule", "deadline", "phase", "overall goal"
        ],
        "variable_identification": [
            "variable", "independent", "dependent", "control", "factor", "parameter", "measurement",
            "metric", "indicator", "predictor", "outcome", "response", "treatment", "condition"
        ],
        "experimental_design": [
            "design", "group", "sample", "treatment", "control group", "experimental group",
            "replication", "randomization", "sample size", "power", "allocation", "assignment"
        ],
        "methodology_protocol": [
            "method", "procedure", "protocol", "step", "process", "technique", "approach",
            "material", "equipment", "tool", "instrument", "reagent", "supply", "resource"
        ],
        "data_planning": [
            "data", "analysis", "statistics", "statistical", "test", "collection", "visualization",
            "chart", "graph", "plot", "report", "analysis plan", "data collection"
        ],
        "final_review": [
            "review", "final", "complete", "finish", "summary", "export", "overview", "conclusion"
        ]
    }
    
    # Build examples for better classification
    examples = []
    for stage, keywords in stage_keywords.items():
        examples.append(f"- {stage}: {', '.join(keywords[:5])}")
    
    system_prompt = (
        "You are a section-routing assistant for an experimental planning system. "
        "Users can request edits to any part of their experiment plan at any time. "
        "Based on their message, determine which planning stage they want to edit.\n\n"
        
        "**PLANNING STAGES WITH KEYWORDS:**\n"
        f"{chr(10).join(examples)}\n\n"
        
        "**CLASSIFICATION RULES:**\n"
        "1. Look for specific keywords that indicate which section to edit\n"
        "2. Consider the context of what the user is trying to change\n"
        "3. If user mentions specific variables or measurements, route to variable_identification\n"
        "4. If user mentions groups, treatments, or sample sizes, route to experimental_design\n"
        "5. If user mentions steps, procedures, or materials, route to methodology_protocol\n"
        "6. If user mentions data collection or analysis, route to data_planning\n"
        "7. If user mentions objectives or hypotheses, route to objective_setting\n"
        "8. If user mentions review or completion, route to final_review\n\n"
        
        f"Available stages: {', '.join(PLANNING_STAGES)}\n\n"
        
        "CRITICAL: You must respond with ONLY the stage identifier (e.g., 'variable_identification'). "
        "Do not include any other text, explanations, or formatting. "
        "If you cannot determine the stage with high confidence, respond with 'unknown'."
    )

    # Create detailed context about the current state
    incomplete_stages = []
    for stage in PLANNING_STAGES:
        stage_field = stage.replace("_", "")
        if stage == "objective_setting":
            if not state.get('experiment_objective') or not state.get('hypothesis'):
                incomplete_stages.append(stage)
        elif stage == "variable_identification":
            if not state.get('independent_variables') or not state.get('dependent_variables'):
                incomplete_stages.append(stage)
        elif stage == "experimental_design":
            if not state.get('experimental_groups') or not state.get('sample_size'):
                incomplete_stages.append(stage)
        elif stage == "methodology_protocol":
            if not state.get('methodology_steps') or not state.get('materials_equipment'):
                incomplete_stages.append(stage)
        elif stage == "data_planning":
            if not state.get('data_collection_plan') or not state.get('data_analysis_plan'):
                incomplete_stages.append(stage)
    
    human_msg = (
        f"USER MESSAGE: '{user_input}'\n\n"
        f"CURRENT CONTEXT:\n"
        f"- Current stage: {current_stage}\n"
        f"- Incomplete stages: {', '.join(incomplete_stages) if incomplete_stages else 'none'}\n\n"
        f"TASK: Analyze the user's message and determine which planning stage they want to edit. "
        f"Focus on the specific content they want to change, not just the current stage."
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_msg),
    ]

    result = _safe_invoke_llm(messages, "section_routing")
    
    # Clean and validate the result
    if result:
        result = result.strip().lower()
        # Check for exact match
        if result in PLANNING_STAGES:
            return result
        # Check for partial matches
        for stage in PLANNING_STAGES:
            if stage in result or result in stage:
                logger.info(f"[SECTION] Found partial match: '{result}' -> '{stage}'")
                return stage
    
    logger.warning(f"[SECTION] Primary LLM classification failed for '{user_input}', result: {result}")
    return None


def _classify_section_with_fallback_llm(user_input: str, state: ExperimentPlanState) -> str | None:
    """Fallback LLM classification with a more direct approach."""
    
    system_prompt = (
        "You are classifying user requests for an experiment planning system. "
        "The user wants to edit one of these sections:\n\n"
        
        "objective_setting - research goals, hypotheses, objectives, timelines\n"
        "variable_identification - variables, measurements, factors\n"
        "experimental_design - groups, sample sizes, treatments\n"
        "methodology_protocol - procedures, materials, equipment\n"
        "data_planning - data collection, analysis, statistics\n"
        "final_review - review, export, summary\n\n"
        
        "Examples:\n"
        "- 'change the hypothesis' -> objective_setting\n"
        "- 'add a control variable' -> variable_identification\n"
        "- 'modify the sample size' -> experimental_design\n"
        "- 'update the procedure' -> methodology_protocol\n"
        "- 'change the analysis method' -> data_planning\n"
        "- 'review the final plan' -> final_review\n\n"
        
        "Respond with ONLY the section name. If unclear, respond with the current stage."
    )

    current_stage = state.get("current_stage", "objective_setting")
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"User wants to edit: '{user_input}'\nCurrent stage: {current_stage}"),
    ]

    result = _safe_invoke_llm(messages, "section_routing_fallback")
    
    if result:
        result = result.strip().lower()
        # Check for exact match
        if result in PLANNING_STAGES:
            return result
        # Check for partial matches
        for stage in PLANNING_STAGES:
            if stage in result or result in stage:
                logger.info(f"[SECTION] Fallback found partial match: '{result}' -> '{stage}'")
                return stage
    
    logger.warning(f"[SECTION] Fallback LLM classification failed for '{user_input}', result: {result}")
    return None


def _make_intelligent_section_guess(state: ExperimentPlanState, user_input: str) -> str:
    """Make an intelligent guess about which section to edit based on state completeness and user input."""
    
    current_stage = state.get("current_stage", "objective_setting")
    
    # First, try keyword-based matching as a last resort
    user_input_lower = user_input.lower()
    
    # Keyword matching with scoring
    stage_scores = {
        "objective_setting": 0,
        "variable_identification": 0,
        "experimental_design": 0,
        "methodology_protocol": 0,
        "data_planning": 0,
        "final_review": 0
    }
    
    # Score based on keywords
    keyword_mapping = {
        "objective_setting": ["objective", "goal", "purpose", "hypothesis", "research", "aim", "question", "timeline", "duration"],
        "variable_identification": ["variable", "independent", "dependent", "control", "factor", "measure", "parameter"],
        "experimental_design": ["design", "group", "sample", "treatment", "control", "size", "replication", "randomization"],
        "methodology_protocol": ["method", "procedure", "protocol", "step", "process", "material", "equipment", "tool"],
        "data_planning": ["data", "analysis", "statistics", "statistical", "test", "collection", "visualization", "chart"],
        "final_review": ["review", "final", "complete", "finish", "summary", "export", "overview"]
    }
    
    for stage, keywords in keyword_mapping.items():
        for keyword in keywords:
            if keyword in user_input_lower:
                stage_scores[stage] += 1
    
    # Find the stage with the highest score
    best_stage = max(stage_scores, key=stage_scores.get)
    best_score = stage_scores[best_stage]
    
    if best_score > 0:
        logger.info(f"[SECTION] Keyword-based guess: '{user_input}' -> {best_stage} (score: {best_score})")
        return best_stage
    
    # If no keywords match, check state completeness and prefer current stage or next incomplete stage
    incomplete_stages = []
    
    # Check each stage for completeness
    if not state.get('experiment_objective') or not state.get('hypothesis'):
        incomplete_stages.append("objective_setting")
    
    if not state.get('independent_variables') or not state.get('dependent_variables'):
        incomplete_stages.append("variable_identification")
    
    if not state.get('experimental_groups') or not state.get('sample_size'):
        incomplete_stages.append("experimental_design")
    
    if not state.get('methodology_steps') or not state.get('materials_equipment'):
        incomplete_stages.append("methodology_protocol")
    
    if not state.get('data_collection_plan') or not state.get('data_analysis_plan'):
        incomplete_stages.append("data_planning")
    
    # Prefer current stage if it's incomplete
    if current_stage in incomplete_stages:
        logger.info(f"[SECTION] Intelligent guess: using current incomplete stage '{current_stage}'")
        return current_stage
    
    # Otherwise, use the first incomplete stage
    if incomplete_stages:
        logger.info(f"[SECTION] Intelligent guess: using first incomplete stage '{incomplete_stages[0]}'")
        return incomplete_stages[0]
    
    # If everything seems complete, default to current stage
    logger.info(f"[SECTION] Intelligent guess: defaulting to current stage '{current_stage}'")
    return current_stage


def _classify_intent_with_llm(user_input: str) -> str | None:
    """Classify the user_input as 'approval', 'edit', or 'unclear' using the LLM."""

    system_prompt = (
        "You are an intent classifier for an experimental planning system. "
        "Users are being asked to approve sections of their experiment plan or request changes.\n\n"
        
        "**INTENT CATEGORIES:**\n"
        "- **approval**: User agrees to proceed with the current section as-is\n"
        "  Examples: 'approve', 'yes', 'looks good', 'proceed', 'continue', 'ready to move on'\n\n"
        
        "- **edit**: User wants to modify or change something in the current section\n"
        "  Examples: 'instead of X, make it Y', 'change the duration', 'can we modify', 'rather than', 'but what if'\n"
        "  Key indicators: 'instead', 'change', 'modify', 'could we', 'can we', 'rather than', 'but', 'however'\n\n"
        
        "- **unclear**: User message is ambiguous or doesn't clearly indicate approval or edit intent\n"
        "  Examples: unclear questions, off-topic comments, or ambiguous statements\n\n"
        
        "**CRITICAL RULES:**\n"
        "1. If a user suggests ANY modification, change, or alternative (even while being polite), classify as 'edit'\n"
        "2. Phrases like 'instead of X could we make it Y' are clearly edit requests\n"
        "3. Only classify as 'approval' if the user clearly agrees with the current state\n\n"
        
        "CRITICAL: You must respond with ONLY the category name: approval, edit, or unclear. "
        "Do not include any other text, explanations, or formatting."
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"User message: {user_input}"),
    ]

    result = _safe_invoke_llm(messages, "intent_classification")
    
    if result and result in {"approval", "edit", "unclear"}:
        return result
    
    logger.warning(f"[INTENT] Primary LLM classification failed for '{user_input}', result: {result}")
    return None


def _classify_intent_with_fallback_llm(user_input: str) -> str | None:
    """Fallback LLM intent classification with a more direct approach."""
    
    system_prompt = (
        "Classify this user message:\n"
        "- 'approval' if they agree/approve\n"
        "- 'edit' if they want to change something\n"
        "- 'unclear' if ambiguous\n\n"
        "Respond with only: approval, edit, or unclear"
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_input),
    ]

    result = _safe_invoke_llm(messages, "intent_classification_fallback")
    
    if result and result in {"approval", "edit", "unclear"}:
        return result
    
    return None 