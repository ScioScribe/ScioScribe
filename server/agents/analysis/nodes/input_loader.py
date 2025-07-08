"""
Input Loader Node for Analysis Agent

This module implements the input loader node that validates and loads
experiment plans and datasets, performing immediate validation and failing
fast on errors.
"""

from pathlib import Path
from typing import Dict, Any

from .base_node import BaseNode

# Constants
MAX_CSV_SIZE_MB = 50


class InputLoaderNode(BaseNode):
    """
    Input Loader Node
    
    Reads experiment plan file and validates CSV file access.
    Performs immediate validation and fails fast on errors.
    """
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process input validation and loading
        
        Args:
            state: Current analysis state
            
        Returns:
            Dictionary containing plan text and error status
        """
        self.log_info("Starting validation")
        
        try:
            # Read experiment plan file
            plan_path = Path(state["experiment_plan_path"])
            if not plan_path.exists():
                raise FileNotFoundError(f"Experiment plan file not found: {plan_path}")
            
            plan_text = plan_path.read_text(encoding='utf-8')
            self.log_info(f"Read plan file ({len(plan_text)} characters)")
            
            # Validate CSV file
            csv_path = Path(state["csv_file_path"])
            if not csv_path.exists():
                raise FileNotFoundError(f"CSV file not found: {csv_path}")
            
            # Check file size
            csv_size_mb = csv_path.stat().st_size / (1024 * 1024)
            if csv_size_mb > MAX_CSV_SIZE_MB:
                raise ValueError(f"CSV file too large: {csv_size_mb:.1f}MB (max: {MAX_CSV_SIZE_MB}MB)")
            
            self.log_info(f"Validated CSV file ({csv_size_mb:.1f}MB)")
            
            return {
                "plan_text": plan_text,
                "error_message": ""
            }
            
        except Exception as e:
            return self.handle_error(e, "validation") 