"""
Output Assembler Node for LLM-Powered Renderer

This node assembles the final output when all validation and execution
steps have succeeded. Only fires when error_msg is None.
"""

from typing import Dict, Any

from .base_node import BaseNode


class OutputAssemblerNode(BaseNode):
    """
    Output Assembler Node
    
    Terminal node that assembles the final output dictionary when
    visualization generation succeeds.
    """
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assemble final output for successful visualization
        
        Args:
            state: Current renderer state with all results
            
        Returns:
            Final output dictionary matching original renderer interface
        """
        # This node should only fire when error_msg is None
        if state.get("error_msg"):
            self.log_error(f"Output assembler called with error: {state['error_msg']}")
            # Should not happen with proper edge conditions, but handle gracefully
            return {
                "plot_image_path": "",
                "llm_code_used": state.get("generated_code", ""),
                "warnings": state.get("warnings", []) + [f"Failed after {state.get('retry_count', 0)} retries: {state['error_msg']}"]
            }
        
        self.log_info("Assembling successful visualization output")
        
        # Extract ingredients for output path
        ingredients = state["ingredients"]
        output_path = ingredients["output_path"]
        
        # Build final output matching original renderer interface
        return {
            "plot_image_path": str(output_path),
            "llm_code_used": state.get("generated_code", ""),
            "warnings": state.get("warnings", [])
        } 