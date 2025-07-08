"""
Output Assembler Node for LLM-Powered Renderer

This node assembles the final output when all validation and execution
steps have succeeded. Generates both HTML (interactive) and PNG (static) 
outputs. Only fires when error_msg is None.
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
                "plot_html_path": "",
                "plot_png_path": "",
                "llm_code_used": state.get("generated_code", ""),
                "warnings": state.get("warnings", []) + [f"Failed after {state.get('retry_count', 0)} retries: {state['error_msg']}"]
            }
        
        self.log_info("Assembling successful visualization output")
        
        # Extract ingredients for output paths
        ingredients = state["ingredients"]
        html_output_path = ingredients["html_output_path"]
        png_output_path = ingredients["png_output_path"]
        
        # Build final output with both HTML and PNG paths
        return {
            "plot_image_path": str(html_output_path),  # Primary path (HTML for interactivity)
            "plot_html_path": str(html_output_path),
            "plot_png_path": str(png_output_path),
            "llm_code_used": state.get("generated_code", ""),
            "warnings": state.get("warnings", [])
        } 