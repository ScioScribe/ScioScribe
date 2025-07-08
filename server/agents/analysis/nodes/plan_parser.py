"""
Plan Parser Node for Analysis Agent

This module implements the plan parser node that extracts structured information
from experiment plans using LLM, preserving user's original intent and specific language.
"""

import json
from typing import Dict, Any

from .base_node import BaseNode


class PlanParserNode(BaseNode):
    """
    Plan Parser Node
    
    Extracts structured information from experiment plan using LLM.
    PRESERVES user's original intent and specific language.
    """
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process plan parsing and structured extraction
        
        Args:
            state: Current analysis state
            
        Returns:
            Dictionary containing structured plan and messages
        """
        self.log_info("Extracting structured plan information")
        
        if state["error_message"]:
            return {"structured_plan": {}}
        
        try:
            # Create user-intent-preserving prompt for plan parsing
            parsing_prompt = f"""
            CRITICAL: The user's request is the primary directive. Your job is to understand and support their specific intent.
            
            USER REQUEST (HIGHEST PRIORITY): "{state["user_prompt"]}"
            
            EXPERIMENT PLAN CONTEXT:
            {state["plan_text"]}
            
            Your task is to extract information that SUPPORTS the user's specific request. Do not generalize or override their intent.
            
            INSTRUCTIONS:
            1. Identify the user's specific analytical goal from their request
            2. Extract variables that directly relate to their question
            3. Determine grouping factors they mentioned or implied
            4. Identify time-related aspects if they asked for trends/time series
            5. Note any statistical analysis they specifically requested
            6. Provide context that helps fulfill their visualization request
            
            Extract and return a JSON object with this structure:
            {{
                "analytical_goal": "User's specific goal from their request (not generalized)",
                "variables_of_interest": ["Variables mentioned or implied in user request"],
                "grouping_factors": ["Grouping/categorization factors from user request"],
                "time_factors": ["Time-related variables if user asked for trends/time analysis"],
                "statistical_tests": ["Statistical analysis specifically requested by user"],
                "chart_context": "Context that supports the user's visualization request"
            }}
            
            Remember: Support the user's intent, don't override it with generic analysis goals.
            Return only the JSON object, no additional text.
            """
            
            # Get LLM response
            response = self.llm.invoke([{"role": "user", "content": parsing_prompt}])
            response_text = response.content.strip()
            
            # Try to parse JSON
            try:
                structured_plan = json.loads(response_text)
                self.log_info("Successfully extracted user-intent-preserving plan")
            except json.JSONDecodeError:
                self.log_warning("Failed to parse JSON, using user-aware fallback")
                
                # Create USER-AWARE fallback that preserves their intent
                user_prompt_lower = state["user_prompt"].lower()
                
                # Determine analytical goal based on user language
                if any(word in user_prompt_lower for word in ["distribution", "spread", "range"]):
                    analytical_goal = "Analyze data distribution patterns"
                elif any(word in user_prompt_lower for word in ["compare", "comparison", "vs", "versus", "between"]):
                    analytical_goal = "Compare different groups or categories"
                elif any(word in user_prompt_lower for word in ["correlation", "relationship", "association"]):
                    analytical_goal = "Examine relationships between variables"
                elif any(word in user_prompt_lower for word in ["trend", "time", "over", "series", "change"]):
                    analytical_goal = "Analyze trends and patterns over time"
                elif any(word in user_prompt_lower for word in ["cluster", "group", "segment"]):
                    analytical_goal = "Identify clusters and groupings in data"
                else:
                    analytical_goal = f"Fulfill user request: {state['user_prompt']}"
                
                # Extract variables mentioned in the request
                variables_of_interest = []
                for word in state["user_prompt"].split():
                    # Look for potential variable names (common patterns)
                    if any(keyword in word.lower() for keyword in ["length", "width", "height", "size", "count", "rate", "score", "value", "amount"]):
                        variables_of_interest.append(word)
                
                # Determine grouping factors from user language
                grouping_factors = []
                if any(word in user_prompt_lower for word in ["by", "group", "category", "type", "species", "class"]):
                    grouping_factors.append("Categorical grouping as requested")
                
                # Time factors if mentioned
                time_factors = []
                if any(word in user_prompt_lower for word in ["time", "date", "year", "month", "day", "period"]):
                    time_factors.append("Time-based analysis")
                
                # Statistical tests based on user request
                statistical_tests = []
                if any(word in user_prompt_lower for word in ["test", "significant", "correlation", "regression"]):
                    statistical_tests.append("Statistical analysis as requested")
                
                structured_plan = {
                    "analytical_goal": analytical_goal,
                    "variables_of_interest": variables_of_interest or ["Variables from user request"],
                    "grouping_factors": grouping_factors or ["As specified by user"],
                    "time_factors": time_factors,
                    "statistical_tests": statistical_tests,
                    "chart_context": f"Support user's request: {state['user_prompt']}"
                }
                
                self.log_info("Created user-aware fallback plan")
            
            return {
                "structured_plan": structured_plan,
                "messages": [{"role": "assistant", "content": f"Understanding your request: {structured_plan['analytical_goal']}"}]
            }
            
        except Exception as e:
            return self.handle_error(e, "plan parsing") 