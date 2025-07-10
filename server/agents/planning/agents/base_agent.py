"""
Base agent class for the experiment planning system.

This module provides the foundational BaseAgent class that all specialized
planning agents inherit from, ensuring consistent behavior, logging, and
state management across the entire multi-agent system.
"""

from typing import Dict, Any, Optional, List, Tuple
from abc import ABC, abstractmethod
from datetime import datetime
import logging

from ..state import ExperimentPlanState, PLANNING_STAGES
from ..validation import StateValidationError, validate_experiment_plan_state
from ..factory import add_chat_message, add_error
from ..debug import StateDebugger, performance_monitor, performance_context, log_agent_interaction
from ..serialization import serialize_state_to_dict, deserialize_dict_to_state


class BaseAgent(ABC):
    """
    Base class for all experiment planning agents.
    
    Provides common functionality for state management, logging, validation,
    and user interaction that all specialized agents can inherit and extend.
    """
    
    def __init__(
        self,
        agent_name: str,
        stage: str,
        debugger: Optional[StateDebugger] = None,
        log_level: str = "INFO"
    ):
        """
        Initialize the base agent.
        
        Args:
            agent_name: Unique name for this agent
            stage: The planning stage this agent handles
            debugger: Optional StateDebugger instance for logging
            log_level: Logging level for this agent
        """
        self.agent_name = agent_name
        self.stage = stage
        self.debugger = debugger or StateDebugger(log_level)
        
        # Set up logging
        self.logger = logging.getLogger(f"agents.planning.{agent_name}")
        self.logger.setLevel(getattr(logging, log_level.upper()))
        
        # Validate stage
        if stage not in PLANNING_STAGES:
            raise ValueError(f"Invalid stage '{stage}'. Must be one of: {PLANNING_STAGES}")
        
        # Context memory for conversation tracking
        self.conversation_context = {
            "last_response": None,
            "response_count": 0,
            "topics_discussed": set(),
            "user_feedback_received": [],
            "stage_entry_time": None
        }
        
        self.logger.info(f"Initialized {agent_name} for stage: {stage}")
    
    @abstractmethod
    def process_state(self, state: ExperimentPlanState) -> ExperimentPlanState:
        """
        Process the current state and return updated state.
        
        This is the main method that each agent must implement to handle
        their specific planning stage responsibilities.
        
        Args:
            state: Current experiment plan state
            
        Returns:
            Updated ExperimentPlanState
            
        Raises:
            StateValidationError: If state validation fails
        """
        pass
    
    @abstractmethod
    def generate_questions(self, state: ExperimentPlanState) -> List[str]:
        """
        Generate relevant questions for the user based on current state.
        
        Args:
            state: Current experiment plan state
            
        Returns:
            List of questions to ask the user
        """
        pass
    
    @abstractmethod
    def validate_stage_requirements(self, state: ExperimentPlanState) -> Tuple[bool, List[str]]:
        """
        Validate that the state meets this agent's stage requirements.
        
        Args:
            state: Current experiment plan state
            
        Returns:
            Tuple of (is_valid, list_of_missing_requirements)
        """
        pass
    
    def execute(self, state: ExperimentPlanState, user_input: str = "") -> ExperimentPlanState:
        """
        Main execution method with comprehensive logging and error handling.
        
        Args:
            state: Current experiment plan state
            user_input: Optional user input/feedback
            
        Returns:
            Updated ExperimentPlanState
            
        Raises:
            StateValidationError: If state validation fails
        """
        start_time = datetime.utcnow()
        current_state = state.copy()

        try:
            # Validate input state
            self._validate_input_state(current_state)
            
            # Log user input if provided
            if user_input.strip():
                current_state = add_chat_message(current_state, "user", user_input)
                self.logger.info(f"User input received: {user_input[:100]}...")
            
            # Process state with performance monitoring
            with performance_context(f"{self.agent_name}_process", self.debugger):
                updated_state = self.process_state(current_state)
            
            # Validate output state
            self._validate_output_state(updated_state)
            
            # Log successful execution
            duration = (datetime.utcnow() - start_time).total_seconds()
            self._log_execution_success(current_state, updated_state, duration)
            
            return updated_state
            
        except StateValidationError as e:
            self.logger.error(f"State validation error in {self.agent_name}: {e}")
            current_state = add_error(current_state, f"{self.agent_name} validation error: {e}")
            return current_state
            
        except Exception as e:
            self.logger.error(f"Unexpected error in {self.agent_name}: {e}")
            current_state = add_error(current_state, f"{self.agent_name} execution error: {e}")
            return current_state
    
    def can_process_stage(self, state: ExperimentPlanState) -> bool:
        """
        Check if this agent can process the current stage.
        
        Args:
            state: Current experiment plan state
            
        Returns:
            bool: True if agent can process current stage
        """
        return state.get("current_stage") == self.stage
    
    def get_stage_progress(self, state: ExperimentPlanState) -> Dict[str, Any]:
        """
        Get progress information for this agent's stage.
        
        Args:
            state: Current experiment plan state
            
        Returns:
            Progress information dictionary
        """
        is_valid, missing_requirements = self.validate_stage_requirements(state)
        
        return {
            "stage": self.stage,
            "agent": self.agent_name,
            "is_complete": is_valid,
            "missing_requirements": missing_requirements,
            "completion_percentage": self._calculate_completion_percentage(state),
            "can_advance": is_valid and len(missing_requirements) == 0
        }
    
    def _generate_conversational_response(self, state: ExperimentPlanState, user_input: str = "") -> str:
        """
        Generate a natural, conversational response using LLM.
        
        Args:
            state: Current experiment plan state
            user_input: User's input/feedback
            
        Returns:
            Natural conversational response
        """
        try:
            from ..llm_config import get_llm
            from langchain_core.prompts import ChatPromptTemplate
            
            # Get LLM instance
            llm = get_llm()
            
            # Create context for the response
            chat_history = state.get('chat_history', [])
            recent_messages = chat_history[-3:] if len(chat_history) > 3 else chat_history
            
            # Format recent conversation
            conversation_context = ""
            if recent_messages:
                conversation_context = "\n".join([
                    f"{msg.get('role', 'unknown')}: {msg.get('content', '')}"
                    for msg in recent_messages
                ])
            
            # Get stage progress
            is_complete, missing_requirements = self.validate_stage_requirements(state)
            stage_display = self.stage.replace('_', ' ').title()
            
            # Create the prompt for natural response generation
            response_prompt = ChatPromptTemplate.from_messages([
                ("system", f"""You are a helpful AI research assistant specializing in {stage_display}. 
                
Your personality:
- Conversational and friendly, not robotic
- Knowledgeable about scientific research
- Encouraging and supportive
- Clear and concise in explanations
- Acknowledges user input and builds on previous conversation

Your current task: Help with {stage_display} for an experiment planning session.

Guidelines:
- Always acknowledge what the user said if they provided input
- Reference previous conversation when relevant
- Be specific about what you've accomplished or what's needed
- Use natural language, avoid template-like responses
- Show enthusiasm for the research project
- If something is complete, celebrate the progress
- If more work is needed, guide them naturally to the next step"""),
                
                ("human", f"""Current situation:
- Stage: {stage_display}
- Stage complete: {is_complete}
- Missing requirements: {missing_requirements if missing_requirements else "None"}
- User's latest input: "{user_input}" (if provided)

Recent conversation:
{conversation_context if conversation_context else "This is the start of our conversation."}

Generate a natural, conversational response that:
1. Acknowledges the user's input (if any)
2. Explains what you've done or what's needed next
3. Feels like talking to a helpful research colleague
4. Avoids robotic or template language

Keep it concise but warm and helpful.""")
            ])
            
            # Generate response
            chain = response_prompt | llm
            response = chain.invoke({})
            
            return response.content if hasattr(response, 'content') else str(response)
            
        except Exception as e:
            self.logger.error(f"Error generating conversational response: {e}")
            # Fallback to improved template
            return self._generate_improved_template_response(state, user_input)
    
    def _generate_improved_template_response(self, state: ExperimentPlanState, user_input: str = "") -> str:
        """
        Generate an improved template response as fallback.
        
        Args:
            state: Current experiment plan state
            user_input: User's input/feedback
            
        Returns:
            Improved template response
        """
        is_complete, missing_requirements = self.validate_stage_requirements(state)
        stage_display = self.stage.replace('_', ' ')
        
        # Acknowledge user input if provided
        acknowledgment = ""
        if user_input.strip():
            acknowledgment = f"Thanks for that input! "
        
        if is_complete:
            return f"{acknowledgment}Excellent! I've finished working on the {stage_display}. The information looks comprehensive and we're ready to move forward to the next stage of your experiment plan."
        
        elif missing_requirements:
            return f"{acknowledgment}I'm working on the {stage_display} for your experiment. To complete this section, I need a bit more information about: {', '.join(missing_requirements[:2])}. This will help ensure your plan is thorough and actionable."
        
        else:
            return f"{acknowledgment}I'm ready to help you develop the {stage_display} for your experiment. Let's work together to make sure this section is comprehensive and fits your research goals."

    def _update_conversation_context(self, state: ExperimentPlanState, response: str, user_input: str = ""):
        """
        Update conversation context to track the flow and avoid repetition.
        
        Args:
            state: Current experiment plan state
            response: The response being sent
            user_input: User's input that triggered this response
        """
        try:
            # Update response tracking
            self.conversation_context["last_response"] = response
            self.conversation_context["response_count"] += 1
            
            # Track user feedback
            if user_input.strip():
                self.conversation_context["user_feedback_received"].append({
                    "input": user_input,
                    "timestamp": datetime.utcnow().isoformat(),
                    "stage": self.stage
                })
            
            # Extract topics from user input and response
            if user_input:
                topics = self._extract_topics(user_input)
                self.conversation_context["topics_discussed"].update(topics)
            
            # Set stage entry time if first response in this stage
            if self.conversation_context["response_count"] == 1:
                self.conversation_context["stage_entry_time"] = datetime.utcnow().isoformat()
            
            self.logger.debug(f"Updated conversation context: {self.conversation_context}")
            
        except Exception as e:
            self.logger.error(f"Error updating conversation context: {e}")

    def _extract_topics(self, text: str) -> set:
        """
        Extract key topics from text for context tracking.
        
        Args:
            text: Text to analyze
            
        Returns:
            Set of topic keywords
        """
        # Simple keyword extraction for topics
        topic_keywords = {
            "hypothesis", "objective", "variable", "control", "independent", "dependent",
            "design", "groups", "sample", "methodology", "protocol", "data", "analysis",
            "materials", "equipment", "statistics", "visualization"
        }
        
        text_lower = text.lower()
        found_topics = {keyword for keyword in topic_keywords if keyword in text_lower}
        return found_topics

    def _check_response_repetition(self, proposed_response: str, state: ExperimentPlanState) -> bool:
        """
        Check if the proposed response is too similar to recent responses.
        
        Args:
            proposed_response: The response being considered
            state: Current experiment plan state
            
        Returns:
            True if response seems repetitive, False otherwise
        """
        try:
            # Check against last response
            if self.conversation_context["last_response"]:
                last_response = self.conversation_context["last_response"]
                
                # Simple similarity check - if more than 70% of words are the same
                proposed_words = set(proposed_response.lower().split())
                last_words = set(last_response.lower().split())
                
                if proposed_words and last_words:
                    common_words = proposed_words.intersection(last_words)
                    similarity = len(common_words) / max(len(proposed_words), len(last_words))
                    
                    if similarity > 0.7:
                        self.logger.warning(f"Response repetition detected (similarity: {similarity:.2f})")
                        return True
            
            # Check chat history for recent similar responses
            chat_history = state.get('chat_history', [])
            recent_agent_messages = [
                msg.get('content', '') for msg in chat_history[-5:]
                if msg.get('role') == 'assistant'
            ]
            
            for recent_msg in recent_agent_messages:
                if recent_msg and len(recent_msg) > 10:  # Skip very short messages
                    recent_words = set(recent_msg.lower().split())
                    proposed_words = set(proposed_response.lower().split())
                    
                    if recent_words and proposed_words:
                        common_words = recent_words.intersection(proposed_words)
                        similarity = len(common_words) / max(len(recent_words), len(proposed_words))
                        
                        if similarity > 0.6:  # Lower threshold for chat history
                            self.logger.warning(f"Response repetition detected in chat history")
                            return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking response repetition: {e}")
            return False

    def _generate_anti_repetition_response(self, state: ExperimentPlanState, user_input: str = "") -> str:
        """
        Generate a response that explicitly avoids repetition.
        
        Args:
            state: Current experiment plan state
            user_input: User's input/feedback
            
        Returns:
            Non-repetitive response
        """
        try:
            from ..llm_config import get_llm
            from langchain_core.prompts import ChatPromptTemplate
            
            llm = get_llm()
            
            # Get context about what we've already discussed
            topics_discussed = list(self.conversation_context["topics_discussed"])
            response_count = self.conversation_context["response_count"]
            last_response = self.conversation_context["last_response"]
            
            # Create a prompt that explicitly avoids repetition
            anti_repetition_prompt = ChatPromptTemplate.from_messages([
                ("system", f"""You are a helpful AI research assistant. This is response #{response_count + 1} in our conversation about {self.stage.replace('_', ' ')}.

CRITICAL: Avoid repeating previous responses. Be fresh and progressive in your communication.

Previous response you gave: "{last_response[:200] if last_response else 'None'}"
Topics already discussed: {', '.join(topics_discussed) if topics_discussed else 'None'}

Guidelines:
- DO NOT repeat phrases or structures from your previous response
- Build on the conversation progressively
- Acknowledge what we've already covered
- Focus on moving forward or addressing new aspects
- Use different vocabulary and sentence structures
- Be conversational but avoid redundancy"""),
                
                ("human", f"""User's input: "{user_input}"

Generate a fresh, non-repetitive response that:
1. Acknowledges this is a continuation of our conversation
2. References progress made so far
3. Uses new vocabulary and phrasing
4. Moves the conversation forward naturally

Keep it conversational and avoid repeating previous responses.""")
            ])
            
            chain = anti_repetition_prompt | llm
            response = chain.invoke({})
            
            return response.content if hasattr(response, 'content') else str(response)
            
        except Exception as e:
            self.logger.error(f"Error generating anti-repetition response: {e}")
            # Fallback with simple variation
            return f"Let me approach this differently. {self._generate_improved_template_response(state, user_input)}"

    def generate_response(self, state: ExperimentPlanState, user_input: str = "") -> str:
        """
        Generate a conversational response with context memory and anti-repetition.
        
        Args:
            state: Current experiment plan state
            user_input: User's input/feedback
            
        Returns:
            Natural, non-repetitive conversational response
        """
        try:
            # First, try to generate a normal conversational response
            proposed_response = self._generate_conversational_response(state, user_input)
            
            # Check if this response is too repetitive
            if self._check_response_repetition(proposed_response, state):
                # Generate an anti-repetition response instead
                final_response = self._generate_anti_repetition_response(state, user_input)
            else:
                final_response = proposed_response
            
            # Update conversation context
            self._update_conversation_context(state, final_response, user_input)
            
            return final_response
            
        except Exception as e:
            self.logger.error(f"Error generating response with context: {e}")
            return "I encountered an issue while processing your request. Let me try to help you with the next step in your experiment planning."
    
    def _validate_input_state(self, state: ExperimentPlanState) -> None:
        """Validate the input state structure."""
        if not isinstance(state, dict):
            raise StateValidationError("State must be a dictionary")
        
        validate_experiment_plan_state(state)
        
        # Log state validation
        self.debugger.log_state_change(
            state,
            f"{self.agent_name}_input_validation",
            {"stage": self.stage, "valid": True}
        )
    
    def _validate_output_state(self, state: ExperimentPlanState) -> None:
        """Validate the output state structure."""
        validate_experiment_plan_state(state)
        
        # Log state validation
        self.debugger.log_state_change(
            state,
            f"{self.agent_name}_output_validation",
            {"stage": self.stage, "valid": True}
        )
    
    def _log_execution_success(
        self,
        input_state: ExperimentPlanState,
        output_state: ExperimentPlanState,
        duration: float
    ) -> None:
        """Log successful agent execution."""
        log_agent_interaction(
            self.agent_name,
            output_state,
            {"current_stage": input_state.get("current_stage")},
            {"updated_stage": output_state.get("current_stage")},
            duration,
            self.debugger
        )
    
    def _calculate_completion_percentage(self, state: ExperimentPlanState) -> float:
        """Calculate completion percentage for this agent's stage."""
        is_valid, missing_requirements = self.validate_stage_requirements(state)
        
        if is_valid:
            return 100.0
        
        # Simple calculation based on missing requirements
        total_requirements = 5  # Assume 5 typical requirements per stage
        missing_count = len(missing_requirements)
        completion = max(0, (total_requirements - missing_count) / total_requirements * 100)
        
        return completion
    
    def _format_chat_history(self, chat_history: List[Dict[str, Any]]) -> str:
        """
        Format chat history for LLM prompts.
        
        Args:
            chat_history: List of chat messages with role and content
            
        Returns:
            Formatted chat history string
        """
        if not chat_history:
            return "No previous conversation."
        
        # Take the last 5 messages to keep context manageable
        recent_messages = chat_history[-5:]
        formatted_messages = []
        
        for msg in recent_messages:
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            formatted_messages.append(f"{role}: {content}")
        
        return "\n".join(formatted_messages)
    
    def _get_stage_fields(self) -> List[str]:
        """Get the fields relevant to this agent's stage."""
        stage_fields = {
            "objective_setting": ["experiment_objective", "hypothesis"],
            "variable_identification": ["independent_variables", "dependent_variables", "control_variables"],
            "experimental_design": ["experimental_groups", "control_groups", "sample_size"],
            "methodology_protocol": ["methodology_steps", "materials_equipment"],
            "data_planning": ["data_collection_plan", "data_analysis_plan", "potential_pitfalls"],
            "final_review": ["expected_outcomes", "ethical_considerations", "timeline"]
        }
        return stage_fields.get(self.stage, [])
    
    def get_debug_info(self, state: ExperimentPlanState) -> Dict[str, Any]:
        """Get debug information for this agent."""
        return {
            "agent_name": self.agent_name,
            "stage": self.stage,
            "can_process": self.can_process_stage(state),
            "progress": self.get_stage_progress(state),
            "state_summary": self.debugger.get_state_summary(state)
        }
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(agent_name='{self.agent_name}', stage='{self.stage}')" 