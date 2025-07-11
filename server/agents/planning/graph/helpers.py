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
    
    # Get current stage for context
    current_stage = state.get("current_stage", "objective_setting")
    
    
    # Check what sections are incomplete for context
    incomplete_sections = []
    if not state.get('experiment_objective'):
        incomplete_sections.append('objective_setting')
    if not state.get('independent_variables') or not state.get('dependent_variables'):
        incomplete_sections.append('variable_identification')
    if not state.get('experimental_groups') or not state.get('sample_size'):
        incomplete_sections.append('experimental_design')
    if not state.get('methodology_steps') or not state.get('materials_equipment'):
        incomplete_sections.append('methodology_protocol')
    if not state.get('data_collection_plan') or not state.get('data_analysis_plan'):
        incomplete_sections.append('data_planning')
    
    
    # Use LLM-based classification with enhanced error handling
    llm_section = _classify_section_with_llm(user_input, state)
    
    
    if llm_section and llm_section in PLANNING_STAGES:
        return llm_section
    
    # If LLM classification fails, try with a more direct approach
    logger.warning(f"[SECTION] ⚠️ Primary LLM classification failed (result: {llm_section}), trying fallback approach")
    fallback_section = _classify_section_with_fallback_llm(user_input, state)
    
    
    if fallback_section and fallback_section in PLANNING_STAGES:
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


def _classify_section_with_llm(user_input: str, state: ExperimentPlanState) -> str | None:
    """Enhanced LLM classification using two-step process with full state context."""
    
    # Step 1: Extract what the user wants to change
    change_analysis = _extract_change_intent(user_input)
    if not change_analysis:
        logger.warning(f"[LLM] Failed to extract change intent from: '{user_input}'")
        return None
    
    # Step 2: Map the change to the correct section based on current state
    section_mapping = _map_change_to_section(change_analysis, state, user_input)
    
    
    return section_mapping


def _extract_change_intent(user_input: str) -> str | None:
    """First LLM call: Extract what the user wants to change."""
    
    system_prompt = (
        "You are analyzing a user's edit request to extract what they want to change.\n\n"
        
        "Your task is to identify the SPECIFIC ASPECT they want to modify. Focus on:\n"
        "- What element/component they're referring to\n"
        "- What type of change they want (modify, add, remove, etc.)\n"
        "- The specific value or characteristic they mention\n\n"
        
        "Examples:\n"
        "- 'Can we change the timeline to 6 months?' -> 'timeline/duration'\n"
        "- 'Let's use 5 groups instead of 3' -> 'number of groups'\n"
        "- 'Add temperature as a control variable' -> 'control variables'\n"
        "- 'Change the sample size to 100' -> 'sample size'\n"
        "- 'Modify the hypothesis' -> 'hypothesis'\n"
        "- 'Update the procedure for step 3' -> 'methodology steps'\n"
        "- 'Change the statistical analysis method' -> 'analysis method'\n"
        "- 'Add more replicates' -> 'replicates/sample size'\n\n"
        
        "Respond with a SHORT phrase describing what they want to change. "
        "Focus on the CONTENT/ASPECT, not the section name."
    )
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"User edit request: '{user_input}'")
    ]
    
    result = _safe_invoke_llm(messages, "change_intent_extraction")
    
    if result:
        result = result.strip()
        return result
    
    return None


def _map_change_to_section(change_intent: str, state: ExperimentPlanState, original_input: str) -> str | None:
    """Second LLM call: Map the change to the correct section based on current state content."""
    
    # Build rich context about current state content
    state_context = _build_state_context_for_llm(state)
    
    system_prompt = (
        "You are mapping a user's change request to the correct planning section.\n\n"
        
        "PLANNING SECTIONS:\n"
        "1. objective_setting - Research goals, hypotheses, timelines, overall objectives\n"
        "2. variable_identification - Independent/dependent/control variables, measurements\n"
        "3. experimental_design - Groups, treatments, sample sizes, experimental structure\n"
        "4. methodology_protocol - Step-by-step procedures, materials, equipment\n"
        "5. data_planning - Data collection methods, analysis plans, statistics\n"
        "6. final_review - Review, summary, export\n\n"
        
        "CRITICAL RULES:\n"
        "- Timeline/duration changes = objective_setting\n"
        "- Hypothesis changes = objective_setting\n"
        "- Variable definitions = variable_identification\n"
        "- Group counts/sample sizes = experimental_design\n"
        "- Procedure steps = methodology_protocol\n"
        "- Analysis methods = data_planning\n\n"
        
        "You will receive:\n"
        "1. What the user wants to change\n"
        "2. Current content of each section\n"
        "3. The original user input\n\n"
        
        "Based on the CURRENT STATE CONTENT, determine which section the change belongs to.\n"
        "If the change relates to content that exists in a section, that's the correct section.\n\n"
        
        "Respond with ONLY the section name (e.g., 'objective_setting')."
    )
    
    human_message = (
        f"CHANGE REQUEST: {change_intent}\n"
        f"ORIGINAL INPUT: {original_input}\n\n"
        f"CURRENT STATE CONTENT:\n{state_context}\n\n"
        f"Which section should this change be made to?"
    )
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_message)
    ]
    
    result = _safe_invoke_llm(messages, "section_mapping")
    
    if result:
        result = result.strip().lower()
        
        # Validate result
        if result in PLANNING_STAGES:
            return result
        
        # Try to find partial match
        for stage in PLANNING_STAGES:
            if stage in result or result in stage:
                return stage
    
    logger.warning(f"[LLM] Section mapping failed for change: '{change_intent}'")
    return None


def _build_state_context_for_llm(state: ExperimentPlanState) -> str:
    """Build rich context about current state content for LLM."""
    
    context_lines = []
    
    # Objective Setting Content
    objective_content = []
    if state.get('experiment_objective'):
        objective_content.append(f"Objective: {state['experiment_objective']}")
    if state.get('hypothesis'):
        objective_content.append(f"Hypothesis: {state['hypothesis']}")
    if state.get('research_query'):
        objective_content.append(f"Research Query: {state['research_query']}")
    
    if objective_content:
        context_lines.append("OBJECTIVE_SETTING:")
        context_lines.extend([f"  {line}" for line in objective_content])
    else:
        context_lines.append("OBJECTIVE_SETTING: [Empty]")
    
    # Variable Identification Content
    var_content = []
    if state.get('independent_variables'):
        var_content.append(f"Independent Variables: {len(state['independent_variables'])} defined")
        for var in state['independent_variables'][:2]:  # Show first 2
            var_content.append(f"  - {var.get('name', 'unnamed')}")
    if state.get('dependent_variables'):
        var_content.append(f"Dependent Variables: {len(state['dependent_variables'])} defined")
        for var in state['dependent_variables'][:2]:  # Show first 2
            var_content.append(f"  - {var.get('name', 'unnamed')}")
    if state.get('control_variables'):
        var_content.append(f"Control Variables: {len(state['control_variables'])} defined")
        for var in state['control_variables'][:2]:  # Show first 2
            var_content.append(f"  - {var.get('name', 'unnamed')}")
    
    if var_content:
        context_lines.append("VARIABLE_IDENTIFICATION:")
        context_lines.extend([f"  {line}" for line in var_content])
    else:
        context_lines.append("VARIABLE_IDENTIFICATION: [Empty]")
    
    # Experimental Design Content
    design_content = []
    if state.get('experimental_groups'):
        design_content.append(f"Experimental Groups: {len(state['experimental_groups'])} defined")
        for group in state['experimental_groups'][:2]:  # Show first 2
            design_content.append(f"  - {group.get('name', 'unnamed')}")
    if state.get('control_groups'):
        design_content.append(f"Control Groups: {len(state['control_groups'])} defined")
    if state.get('sample_size'):
        design_content.append(f"Sample Size: {state['sample_size']}")
    
    if design_content:
        context_lines.append("EXPERIMENTAL_DESIGN:")
        context_lines.extend([f"  {line}" for line in design_content])
    else:
        context_lines.append("EXPERIMENTAL_DESIGN: [Empty]")
    
    # Methodology Content
    method_content = []
    if state.get('methodology_steps'):
        method_content.append(f"Methodology Steps: {len(state['methodology_steps'])} defined")
        for step in state['methodology_steps'][:2]:  # Show first 2
            method_content.append(f"  - Step {step.get('step_number', '?')}: {step.get('description', 'no description')[:50]}...")
    if state.get('materials_equipment'):
        method_content.append(f"Materials/Equipment: {len(state['materials_equipment'])} items")
    
    if method_content:
        context_lines.append("METHODOLOGY_PROTOCOL:")
        context_lines.extend([f"  {line}" for line in method_content])
    else:
        context_lines.append("METHODOLOGY_PROTOCOL: [Empty]")
    
    # Data Planning Content
    data_content = []
    if state.get('data_collection_plan'):
        data_content.append(f"Data Collection Plan: {type(state['data_collection_plan']).__name__}")
        if isinstance(state['data_collection_plan'], dict):
            data_content.append(f"  Keys: {list(state['data_collection_plan'].keys())}")
    if state.get('data_analysis_plan'):
        data_content.append(f"Data Analysis Plan: {type(state['data_analysis_plan']).__name__}")
        if isinstance(state['data_analysis_plan'], dict):
            data_content.append(f"  Keys: {list(state['data_analysis_plan'].keys())}")
    
    if data_content:
        context_lines.append("DATA_PLANNING:")
        context_lines.extend([f"  {line}" for line in data_content])
    else:
        context_lines.append("DATA_PLANNING: [Empty]")
    
    return "\n".join(context_lines)


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
        return current_stage
    
    # Otherwise, use the first incomplete stage
    if incomplete_stages:
        return incomplete_stages[0]
    
    # If everything seems complete, default to current stage
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