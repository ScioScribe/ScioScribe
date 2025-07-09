"""
Input Loader Node for Analysis Agent

This module implements the input loader node that validates experiment plan
and CSV data content, performing immediate validation and failing fast on errors.
"""

import io
import pandas as pd
from typing import Dict, Any

from .base_node import BaseNode

# Constants
MAX_CSV_SIZE_MB = 50


class InputLoaderNode(BaseNode):
    """
    Input Loader Node
    
    Validates experiment plan content and CSV data content.
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
        self.log_info("Starting content validation")
        
        try:
            # Validate experiment plan content
            plan_content = state["experiment_plan_content"]
            if not plan_content or not plan_content.strip():
                raise ValueError("Experiment plan content is empty or invalid")
            
            self.log_info(f"Validated plan content ({len(plan_content)} characters)")
            
            # Validate CSV data content
            csv_content = state["csv_data_content"]
            if not csv_content or not csv_content.strip():
                raise ValueError("CSV data content is empty or invalid")
            
            # Check CSV content size
            csv_size_mb = len(csv_content.encode('utf-8')) / (1024 * 1024)
            if csv_size_mb > MAX_CSV_SIZE_MB:
                raise ValueError(f"CSV content too large: {csv_size_mb:.1f}MB (max: {MAX_CSV_SIZE_MB}MB)")
            
            # Validate CSV format by attempting to parse it
            try:
                df = pd.read_csv(io.StringIO(csv_content))
                if df.empty:
                    raise ValueError("CSV content produces empty dataframe")
                if len(df.columns) == 0:
                    raise ValueError("CSV content has no columns")
                self.log_info(f"Validated CSV content ({len(df)} rows, {len(df.columns)} columns, {csv_size_mb:.1f}MB)")
            except Exception as e:
                raise ValueError(f"Invalid CSV format: {str(e)}")
            
            return {
                "plan_text": plan_content,
                "error_message": ""
            }
            
        except Exception as e:
            return self.handle_error(e, "content validation") 