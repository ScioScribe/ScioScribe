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
    Determine which section the user wants to edit based on their input using LLM classification.
    
    This function uses a robust LLM with structured output to reliably classify
    user edit requests to the correct planning stage based on content and context.
    
    Args:
        user_input: User's input message
        state: Current experiment plan state
        
    Returns:
        Planning stage name to navigate to
    """
    from ..llm_config import get_llm
    from ..models import StageClassificationOutput
    from langchain_core.prompts import ChatPromptTemplate
    
    # Get current stage and plan context
    current_stage = state.get("current_stage", "objective_setting")
    
    # Build context about current plan state
    plan_context = _build_plan_context(state)
    
    # Create comprehensive prompt for LLM classification
    classification_prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert at analyzing user requests in the context of experimental planning. 

Your task is to determine which planning stage a user wants to edit based on their input and the current experiment plan state.

PLANNING STAGES AND THEIR PURPOSES:
1. **objective_setting**: Research objectives, hypotheses, goals, timelines, research questions
2. **variable_identification**: Independent variables, dependent variables, control variables, factors, measurements, parameters
3. **experimental_design**: Experimental groups, control groups, sample sizes, treatments, randomization, replication
4. **methodology_protocol**: Methods, procedures, protocols, steps, materials, equipment, tools, processes
5. **data_planning**: Data collection, data analysis, statistics, statistical tests, visualizations, charts
6. **final_review**: Final review, completion, summary, export, overview

ANALYSIS GUIDELINES:
- Focus on WHAT the user wants to modify/edit, not just keywords
- Consider the current stage context - users often want to edit the current or recent stages
- If the user mentions specific elements (like "variables", "dependent variable"), map to the appropriate stage
- If uncertain, prefer the current stage when the request could reasonably apply to it
- Be confident in your classification - most requests have clear stage associations"""),
        
        ("human", """Current experiment context:
**Current Stage**: {current_stage}
**Plan State**: {plan_context}

**User Request**: "{user_input}"

Analyze this request and determine which planning stage the user wants to edit. Consider:
1. What specific elements they want to modify
2. Which stage owns those elements
3. The current context of their planning session

Provide your classification with confidence and clear reasoning.""")
    ])
    
    try:
        # Get LLM with structured output
        llm = get_llm()
        structured_llm = llm.with_structured_output(StageClassificationOutput)
        
        # Create the chain
        chain = classification_prompt | structured_llm
        
        # Invoke the LLM
        result = chain.invoke({
            "current_stage": current_stage,
            "plan_context": plan_context,
            "user_input": user_input
        })
        
        # Validate the result
        if result.target_stage in PLANNING_STAGES and result.confidence >= 0.7:
            logger.info(f"[SECTION] ✅ LLM classified '{user_input}' as '{result.target_stage}' (confidence: {result.confidence:.2f}) - {result.reasoning}")
            return result.target_stage
        else:
            logger.warning(f"[SECTION] ⚠️ Low confidence classification: {result.target_stage} ({result.confidence:.2f})")
            # Fall back to current stage for low confidence
            return current_stage
            
    except Exception as e:
        logger.error(f"[SECTION] ❌ LLM classification failed: {e}")
        # Fall back to current stage if LLM fails
        return current_stage


def _build_plan_context(state: ExperimentPlanState) -> str:
    """
    Build a concise context summary of the current experiment plan state for LLM analysis.
    
    Args:
        state: Current experiment plan state
        
    Returns:
        Formatted context string describing the plan state
    """
    context_parts = []
    
    # Objective and hypothesis
    if state.get('experiment_objective'):
        context_parts.append(f"Objective: {state['experiment_objective'][:100]}...")
    if state.get('hypothesis'):
        context_parts.append(f"Hypothesis: {state['hypothesis'][:100]}...")
    
    # Variables
    indep_vars = state.get('independent_variables', [])
    dep_vars = state.get('dependent_variables', [])
    control_vars = state.get('control_variables', [])
    
    if indep_vars:
        var_names = [var.get('name', 'Unnamed') for var in indep_vars[:3]]
        context_parts.append(f"Independent Variables: {', '.join(var_names)}")
    if dep_vars:
        var_names = [var.get('name', 'Unnamed') for var in dep_vars[:3]]
        context_parts.append(f"Dependent Variables: {', '.join(var_names)}")
    if control_vars:
        var_names = [var.get('name', 'Unnamed') for var in control_vars[:3]]
        context_parts.append(f"Control Variables: {', '.join(var_names)}")
    
    # Experimental design
    exp_groups = state.get('experimental_groups', [])
    if exp_groups:
        group_names = [group.get('name', 'Unnamed') for group in exp_groups[:2]]
        context_parts.append(f"Experimental Groups: {', '.join(group_names)}")
    
    # Methodology
    method_steps = state.get('methodology_steps', [])
    if method_steps:
        context_parts.append(f"Methodology: {len(method_steps)} steps defined")
    
    # Data planning
    if state.get('data_collection_plan'):
        context_parts.append("Data Collection: Plan defined")
    if state.get('data_analysis_plan'):
        context_parts.append("Data Analysis: Plan defined")
    
    return " | ".join(context_parts) if context_parts else "No plan elements defined yet"


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
    
    # Use LLM-based intent classification
    llm_intent = _classify_intent_with_llm(user_input)
    
    if llm_intent and llm_intent in {"approval", "edit", "unclear"}:
        return llm_intent
    
    # If primary classification fails, try with a more direct approach
    logger.warning(f"[INTENT] ⚠️ Primary LLM classification failed (result: {llm_intent}), trying fallback approach")
    fallback_intent = _classify_intent_with_fallback_llm(user_input)
    
    if fallback_intent and fallback_intent in {"approval", "edit", "unclear"}:
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

    # Check if next nodes represent an empty list or only the terminal '__end__' node
    if isinstance(state_snapshot.next, list):
        if len(state_snapshot.next) == 0:
            return True
        # Some LangGraph implementations keep a sentinel "__end__" as the sole next node
        if len(state_snapshot.next) == 1 and str(state_snapshot.next[0]) == "__end__":
            return True
    
    return False


def should_skip_interrupt_for_edit_mode(state: ExperimentPlanState) -> bool:
    """
    Check if we should skip the interrupt because we're in edit mode.
    
    This function determines whether the current execution is part of an edit
    operation that should bypass the normal approval interrupt.
    
    Args:
        state: Current experiment plan state
        
    Returns:
        True if interrupt should be skipped (edit mode), False otherwise
    """
    edit_mode = state.get('edit_mode', False)
    return bool(edit_mode)


def set_edit_mode(state: ExperimentPlanState, enabled: bool, return_stage: str = None) -> ExperimentPlanState:
    """
    Set or clear edit mode in the state.
    
    Args:
        state: Current experiment plan state
        enabled: Whether to enable edit mode
        return_stage: Stage to return to after edit (if enabling)
        
    Returns:
        Updated state with edit mode set
    """
    updated_state = state.copy() if hasattr(state, 'copy') else dict(state)
    updated_state['edit_mode'] = enabled
    
    if enabled and return_stage:
        updated_state['return_to_stage'] = return_stage
    elif not enabled:
        # Clear return stage when disabling edit mode
        updated_state.pop('return_to_stage', None)
    
    return updated_state


def clear_edit_mode(state: ExperimentPlanState) -> ExperimentPlanState:
    """
    Clear edit mode and return stage from state.
    
    Args:
        state: Current experiment plan state
        
    Returns:
        Updated state with edit mode cleared
    """
    return set_edit_mode(state, False)


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
            manager = get_llm_manager()
            llm = manager.create_llm(agent_type=agent_type, temperature=0.0, max_tokens=64)
            response = manager.invoke_llm(llm, messages, agent_type)
            
            result = response.strip().lower()
            return result
            
        except (LLMConfigError, Exception) as e:
            logger.warning(
                f"LLM classification attempt {attempt + 1} failed for {agent_type}: {getattr(e, 'message', str(e))}"
            )
            if attempt == max_retries:
                logger.error(f"All LLM classification attempts failed for {agent_type}")
                return None
    
    return None


# Old classification functions removed - using new LLM-based approach in determine_section_to_edit()


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