"""
Response Composer Node for Analysis Agent

This module implements the response composer node that generates explanatory text
and updates memory with chart specification, focusing on the user's original 
request and intent.
"""

from datetime import datetime
from typing import Dict, Any

from .base_node import BaseNode


class ResponseComposerNode(BaseNode):
    """
    Response Composer Node
    
    Generates explanatory text and updates memory with chart specification.
    FOCUSES on the user's original request and intent.
    """
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process response generation and memory updates
        
        Args:
            state: Current analysis state
            
        Returns:
            Dictionary containing explanation, memory, and messages
        """
        self.log_info("Generating explanation")
        
        if state.get("error_msg"):
            return {
                "explanation": f"Unable to fulfill your request: {state['error_msg']}",
                "memory": state.get("memory", {}),
                "html_content": state.get("html_content", "")  # Pass through HTML content
            }
        
        try:
            # Get chart specification from ingredients
            ingredients = state.get("ingredients", {})
            chart_spec = ingredients.get('chart_specification', {})
            user_ask = ingredients.get('user_ask', 'Create a visualization')
            
            # Create explanation that directly addresses user's request
            explanation_prompt = f"""
            Generate a clear, helpful explanation for the user about the visualization you created.
            
            USER'S ORIGINAL REQUEST: "{user_ask}"
            
            CHART CREATED:
            - Type: {chart_spec.get('chart_type', 'visualization')}
            - Title: {chart_spec.get('title', 'Data Visualization')}
            - X-axis: {chart_spec.get('x_column', 'X values')}
            - Y-axis: {chart_spec.get('y_column', 'Y values')}
            - Grouping: {chart_spec.get('hue_column', 'None')}
            
            Write a response that:
            1. Directly addresses their original request
            2. Explains how the visualization answers their question
            3. Describes what they can see in the chart
            4. Uses their language and terminology
            5. Provides insights relevant to their specific request
            
            Keep it concise but informative. Focus on fulfilling their intent.
            """
            
            # Get LLM response for explanation
            response = self.llm.invoke([{"role": "user", "content": explanation_prompt}])
            explanation = response.content.strip()
            
            # Add technical details
            explanation += f"\n\n📊 **Chart Details:**\n"
            explanation += f"- **Type:** {chart_spec.get('chart_type', 'visualization').title()} Chart\n"
            explanation += f"- **Data:** {chart_spec.get('x_column', 'X')} vs {chart_spec.get('y_column', 'Y')}\n"
            
            if chart_spec.get('hue_column'):
                explanation += f"- **Grouped by:** {chart_spec['hue_column']}\n"
            
            explanation += f"\n✨ **Interactive visualization generated successfully!**\n"
            
            # Update memory with user-focused information
            updated_memory = state.get("memory", {}).copy()
            updated_memory["last_user_request"] = user_ask
            updated_memory["last_chart_specification"] = chart_spec
            updated_memory["last_analysis_timestamp"] = datetime.now().isoformat()
            updated_memory["last_analytical_goal"] = "User-defined analysis"
            
            self.log_info("Generated user-focused explanation and updated memory")
            
            return {
                "explanation": explanation,
                "memory": updated_memory,
                "messages": [{"role": "assistant", "content": explanation}],
                "html_content": state.get("html_content", "")  # Pass through HTML content
            }
            
        except Exception as e:
            # Fallback to user-aware explanation even on error
            ingredients = state.get("ingredients", {})
            chart_spec = ingredients.get('chart_specification', {})
            user_ask = ingredients.get('user_ask', 'Create a visualization')
            
            fallback_explanation = f"""
            I created a {chart_spec.get('chart_type', 'visualization')} to address your request: "{user_ask}"
            
            The chart shows {chart_spec.get('x_column', 'data')} on the x-axis and {chart_spec.get('y_column', 'values')} on the y-axis.
            
            ✨ **Interactive visualization generated successfully!**
            
            Note: There was an issue generating the detailed explanation, but the visualization should still fulfill your request.
            """
            
            return {
                "explanation": fallback_explanation,
                "memory": state.get("memory", {}),
                "messages": [{"role": "assistant", "content": fallback_explanation}],
                "html_content": state.get("html_content", "")  # Pass through HTML content
            } 