"""
Data Profiler Node for Analysis Agent

This module implements the data profiler node that loads CSV files and analyzes
their structure, types, and summary statistics.
"""

import pandas as pd
from typing import Dict, Any, List

from .base_node import BaseNode


class DataProfilerNode(BaseNode):
    """
    Data Profiler Node
    
    Loads CSV and analyzes structure, types, and summary statistics.
    """
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process data profiling and analysis
        
        Args:
            state: Current analysis state
            
        Returns:
            Dictionary containing data schema and sample data
        """
        self.log_info("Analyzing dataset structure")
        
        if state["error_message"]:
            return {"data_schema": {}, "data_sample": []}
        
        try:
            # Load CSV into pandas
            df = pd.read_csv(state["csv_file_path"])
            self.log_info(f"Loaded CSV with {len(df)} rows, {len(df.columns)} columns")
            
            # Analyze column types and statistics
            data_schema = {
                "columns": {},
                "row_count": len(df),
                "column_count": len(df.columns)
            }
            
            for col in df.columns:
                col_info = {
                    "type": str(df[col].dtype),
                    "non_null_count": df[col].count(),
                    "null_count": df[col].isnull().sum(),
                    "unique_count": df[col].nunique()
                }
                
                # Add type-specific statistics
                if pd.api.types.is_numeric_dtype(df[col]):
                    col_info.update({
                        "mean": float(df[col].mean()) if not df[col].empty else 0,
                        "std": float(df[col].std()) if not df[col].empty else 0,
                        "min": float(df[col].min()) if not df[col].empty else 0,
                        "max": float(df[col].max()) if not df[col].empty else 0,
                        "data_type": "numeric"
                    })
                elif pd.api.types.is_categorical_dtype(df[col]) or df[col].dtype == 'object':
                    col_info.update({
                        "unique_values": df[col].unique().tolist()[:10],  # First 10 unique values
                        "data_type": "categorical"
                    })
                else:
                    col_info["data_type"] = "other"
                
                data_schema["columns"][col] = col_info
            
            # Get sample data
            sample_size = min(5, len(df))
            data_sample = df.head(sample_size).to_dict('records')
            
            self.log_info(f"Generated schema for {len(data_schema['columns'])} columns")
            
            return {
                "data_schema": data_schema,
                "data_sample": data_sample
            }
            
        except Exception as e:
            return self.handle_error(e, "data profiling") 