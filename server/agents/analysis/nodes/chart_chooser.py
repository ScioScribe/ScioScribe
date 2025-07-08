"""
Chart Chooser Node for Analysis Agent

This module implements the chart chooser node that selects appropriate visualization
specifications using LLM. It prioritizes user-requested chart types and uses LLM
to check viability with the data before falling back to alternatives.
"""

import json
import numpy as np
import re
from typing import Dict, Any, List, Optional

from .base_node import BaseNode


class ChartChooserNode(BaseNode):
    """
    Chart Chooser Node
    
    Prioritizes user-requested chart types, checks viability with LLM,
    and supports a wide range of chart types beyond basic restrictions.
    """
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process chart selection and specification
        
        Args:
            state: Current analysis state
            
        Returns:
            Dictionary containing chart specification and messages
        """
        self.log_info("Selecting visualization specification based on user request")
        
        if state["error_message"]:
            return {"chart_specification": {}}
        
        try:
            # Get previous chart from memory if available
            previous_chart = state["memory"].get("last_chart_specification", {})
            
            # Convert numpy types to Python native types for JSON serialization
            def convert_numpy_types(obj):
                """Convert numpy types to Python native types for JSON serialization"""
                if isinstance(obj, dict):
                    return {k: convert_numpy_types(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_numpy_types(item) for item in obj]
                elif hasattr(obj, 'item'):  # numpy scalar
                    return obj.item()
                elif isinstance(obj, (np.int64, np.int32, np.int16, np.int8)):
                    return int(obj)
                elif isinstance(obj, (np.float64, np.float32, np.float16)):
                    return float(obj)
                elif isinstance(obj, np.bool_):
                    return bool(obj)
                else:
                    return obj
            
            # Get data context
            available_columns = list(state["data_schema"]["columns"].keys())
            data_schema = state["data_schema"]["columns"]
            
            # Step 1: Extract user-requested chart type
            requested_chart_type = self._extract_requested_chart_type(state["user_prompt"])
            
            # Step 2: Check viability and get chart specification
            chart_spec_dict = self._get_chart_specification_with_viability_check(
                state["user_prompt"], 
                requested_chart_type, 
                available_columns, 
                data_schema, 
                previous_chart
            )
            
            # Log the selected chart
            self.log_info(f"Selected {chart_spec_dict['chart_type']} chart (requested: {requested_chart_type})")
            
            return {
                "chart_specification": chart_spec_dict,
                "messages": [{"role": "assistant", "content": f"🎨 Creating {chart_spec_dict['chart_type']} visualization: {chart_spec_dict['title']}"}]
            }
            
        except Exception as e:
            return self.handle_error(e, "chart selection")
    
    def _extract_requested_chart_type(self, user_prompt: str) -> Optional[str]:
        """
        Extract the specific chart type requested by the user
        
        Args:
            user_prompt: User's request
            
        Returns:
            Chart type if found, None otherwise
        """
        user_prompt_lower = user_prompt.lower()
        
        # Comprehensive chart type mapping
        chart_type_patterns = {
            # Basic chart types
            "bar": ["bar chart", "bar plot", "bar graph", "column chart", "column plot"],
            "line": ["line chart", "line plot", "line graph", "time series", "trend line"],
            "scatter": ["scatter plot", "scatter chart", "scatterplot", "dot plot"],
            "histogram": ["histogram", "hist", "frequency distribution"],
            "pie": ["pie chart", "pie plot", "pie graph"],
            "area": ["area chart", "area plot", "stacked area", "filled area"],
            "box": ["box plot", "box chart", "boxplot", "box and whisker"],
            "violin": ["violin plot", "violin chart"],
            "heatmap": ["heatmap", "heat map", "correlation matrix"],
            
            # Advanced chart types
            "bubble": ["bubble chart", "bubble plot"],
            "radar": ["radar chart", "spider chart", "polar chart"],
            "donut": ["donut chart", "doughnut chart"],
            "treemap": ["treemap", "tree map"],
            "sunburst": ["sunburst chart", "sunburst plot"],
            "sankey": ["sankey diagram", "sankey chart"],
            "parallel": ["parallel coordinates", "parallel plot"],
            "density": ["density plot", "kde plot", "kernel density"],
            "strip": ["strip plot", "stripplot"],
            "swarm": ["swarm plot", "beeswarm"],
            "ridge": ["ridge plot", "ridgeline plot"],
            "polar": ["polar plot", "polar chart"],
            "3d": ["3d plot", "3d chart", "three dimensional"],
            
            # Statistical charts
            "regression": ["regression plot", "regression line"],
            "residual": ["residual plot", "residuals"],
            "qq": ["qq plot", "quantile-quantile", "q-q plot"],
            "distribution": ["distribution plot", "dist plot"],
            "joint": ["joint plot", "jointplot"],
            "pair": ["pair plot", "pairplot", "scatter matrix"],
            
            # Time series specific
            "candlestick": ["candlestick chart", "ohlc chart"],
            "waterfall": ["waterfall chart", "waterfall plot"],
            "gantt": ["gantt chart", "timeline chart"],
            
            # Network/Graph
            "network": ["network graph", "network plot", "graph plot"],
            "chord": ["chord diagram", "chord chart"],
            
            # Geospatial
            "map": ["map", "geographical plot", "geo chart"],
            "choropleth": ["choropleth map", "choropleth chart"]
        }
        
        # Check for exact matches first
        for chart_type, patterns in chart_type_patterns.items():
            for pattern in patterns:
                if pattern in user_prompt_lower:
                    return chart_type
        
        # Check for single word matches
        for chart_type in chart_type_patterns.keys():
            if f" {chart_type} " in f" {user_prompt_lower} " or user_prompt_lower.startswith(f"{chart_type} ") or user_prompt_lower.endswith(f" {chart_type}"):
                return chart_type
        
        return None
    
    def _get_chart_specification_with_viability_check(self, 
                                                     user_prompt: str, 
                                                     requested_chart_type: Optional[str],
                                                     available_columns: List[str],
                                                     data_schema: Dict[str, Any],
                                                     previous_chart: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get chart specification with viability check using LLM
        
        Args:
            user_prompt: User's request
            requested_chart_type: Chart type requested by user
            available_columns: Available data columns
            data_schema: Column schema information
            previous_chart: Previous chart specification
            
        Returns:
            Chart specification dictionary
        """
        # Create comprehensive data context
        data_context = self._create_data_context(available_columns, data_schema)
        
        # Create viability check prompt
        viability_prompt = f"""
        You are a data visualization expert. Analyze the user's request and determine the best chart specification.

        USER REQUEST: "{user_prompt}"
        REQUESTED CHART TYPE: {requested_chart_type if requested_chart_type else "Not specified"}
        
        AVAILABLE DATA:
        {data_context}
        
        PREVIOUS CHART: {previous_chart}
        
        INSTRUCTIONS:
        1. If the user specified a chart type, prioritize that exact type
        2. Check if the requested chart type is viable with the available data
        3. If not viable, suggest the closest alternative that fulfills the user's intent
        4. Select appropriate columns based on the user's question
        5. Create engaging titles and labels using the user's language
        
        SUPPORTED CHART TYPES (not limited to):
        - bar, line, scatter, histogram, pie, area, box, violin, heatmap
        - bubble, radar, donut, treemap, density, strip, swarm, ridge
        - regression, residual, qq, distribution, joint, pair
        - candlestick, waterfall, network, chord, map, polar, 3d
        
        Return JSON with this structure:
        {{
            "chart_type": "exact type to use (prioritize user request if viable)",
            "viable_with_requested": true/false,
            "viability_reason": "explanation of why requested type is/isn't viable",
            "x_column": "column for x-axis",
            "y_column": "column for y-axis",
            "hue_column": "grouping column if applicable",
            "groupby_column": "aggregation column if applicable",
            "statistical_overlay": "trend/confidence/regression if requested",
            "title": "engaging title using user's language",
            "x_label": "clear x-axis label",
            "y_label": "clear y-axis label",
            "color_palette": "attractive color scheme",
            "style_theme": "modern/elegant/bold/vibrant",
            "visual_enhancements": "specific styling enhancements"
        }}
        
        REMEMBER: User's exact request is highest priority. Only change chart type if truly not viable.
        """
        
        # Get LLM response
        response = self.llm.invoke([{"role": "user", "content": viability_prompt}])
        response_text = response.content.strip()
        
        # Try to parse LLM response
        try:
            chart_spec_dict = json.loads(response_text)
            
            # Validate required fields
            required_fields = ["chart_type", "x_column", "y_column", "title"]
            if not all(field in chart_spec_dict for field in required_fields):
                raise ValueError("Missing required fields in chart specification")
            
            # Validate column names exist
            if chart_spec_dict["x_column"] not in available_columns:
                raise ValueError(f"X column '{chart_spec_dict['x_column']}' not found")
            if chart_spec_dict["y_column"] not in available_columns:
                raise ValueError(f"Y column '{chart_spec_dict['y_column']}' not found")
            
            # Log viability information
            if chart_spec_dict.get("viable_with_requested") == False:
                self.log_warning(f"Requested chart type '{requested_chart_type}' not viable: {chart_spec_dict.get('viability_reason', 'Unknown reason')}")
            
            return chart_spec_dict
            
        except (json.JSONDecodeError, ValueError) as e:
            self.log_warning(f"LLM response parsing failed ({e}), creating fallback specification")
            return self._create_fallback_specification(user_prompt, requested_chart_type, available_columns, data_schema)
    
    def _create_data_context(self, available_columns: List[str], data_schema: Dict[str, Any]) -> str:
        """
        Create a comprehensive data context string for the LLM
        
        Args:
            available_columns: List of column names
            data_schema: Column schema information
            
        Returns:
            Formatted data context string
        """
        context_lines = []
        
        for col in available_columns:
            col_info = data_schema.get(col, {})
            data_type = col_info.get("data_type", "unknown")
            
            context_parts = [f"- {col} ({data_type})"]
            
            if "unique_values" in col_info:
                unique_count = col_info["unique_values"]
                context_parts.append(f"unique: {unique_count}")
            
            if "min_value" in col_info and "max_value" in col_info:
                context_parts.append(f"range: {col_info['min_value']} - {col_info['max_value']}")
            
            if "sample_values" in col_info:
                samples = col_info["sample_values"][:3]  # Show first 3 samples
                context_parts.append(f"samples: {samples}")
            
            context_lines.append(" ".join(context_parts))
        
        return "\n".join(context_lines)
    
    def _create_fallback_specification(self, 
                                     user_prompt: str, 
                                     requested_chart_type: Optional[str],
                                     available_columns: List[str],
                                     data_schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a fallback chart specification when LLM parsing fails
        
        Args:
            user_prompt: User's request
            requested_chart_type: Chart type requested by user
            available_columns: Available data columns
            data_schema: Column schema information
            
        Returns:
            Fallback chart specification dictionary
        """
        # Use requested chart type if available, otherwise infer from prompt
        if requested_chart_type:
            chart_type = requested_chart_type
        else:
            chart_type = self._infer_chart_type_from_prompt(user_prompt)
        
        # Get column information
        numeric_columns = [col for col, info in data_schema.items() 
                         if info.get("data_type") == "numeric"]
        categorical_columns = [col for col, info in data_schema.items() 
                             if info.get("data_type") == "categorical"]
        
        # Smart column selection
        x_col = available_columns[0] if available_columns else "index"
        y_col = numeric_columns[0] if numeric_columns else (available_columns[1] if len(available_columns) > 1 else "value")
        
        # Look for specific column names in user request
        for col in available_columns:
            col_variations = [col.lower(), col.replace('_', ' ').lower(), col.replace('_', '').lower()]
            if any(variation in user_prompt.lower() for variation in col_variations):
                if any(word in user_prompt.lower() for word in ["x", "horizontal", "width"]):
                    x_col = col
                elif any(word in user_prompt.lower() for word in ["y", "vertical", "height", "length"]):
                    y_col = col
                else:
                    y_col = col  # Default to y if no clear direction
        
        # Determine grouping column
        hue_col = None
        if any(word in user_prompt.lower() for word in ["by", "group", "color", "category", "type", "class"]):
            for col in categorical_columns:
                if col != x_col and col != y_col:
                    hue_col = col
                    break
        
        return {
            "chart_type": chart_type,
            "viable_with_requested": True,
            "viability_reason": "Fallback specification created",
            "x_column": x_col,
            "y_column": y_col,
            "hue_column": hue_col,
            "groupby_column": None,
            "statistical_overlay": None,
            "title": f"✨ {user_prompt[:60]}{'...' if len(user_prompt) > 60 else ''}",
            "x_label": x_col.replace('_', ' ').title(),
            "y_label": y_col.replace('_', ' ').title(),
            "color_palette": "viridis",
            "style_theme": "modern",
            "visual_enhancements": "simple,colorful,clean"
        }
    
    def _infer_chart_type_from_prompt(self, user_prompt: str) -> str:
        """
        Infer chart type from user prompt using keyword matching
        
        Args:
            user_prompt: User's request
            
        Returns:
            Inferred chart type
        """
        user_prompt_lower = user_prompt.lower()
        
        # Keyword-based inference with expanded options
        if any(word in user_prompt_lower for word in ["bar", "column", "count", "frequency", "category"]):
            return "bar"
        elif any(word in user_prompt_lower for word in ["scatter", "dot", "point", "correlation", "relationship", "vs"]):
            return "scatter"
        elif any(word in user_prompt_lower for word in ["line", "trend", "time", "over", "series", "change"]):
            return "line"
        elif any(word in user_prompt_lower for word in ["histogram", "hist", "distribution", "frequency"]):
            return "histogram"
        elif any(word in user_prompt_lower for word in ["pie", "proportion", "percentage", "share"]):
            return "pie"
        elif any(word in user_prompt_lower for word in ["area", "filled", "stacked"]):
            return "area"
        elif any(word in user_prompt_lower for word in ["box", "quartile", "median", "outlier"]):
            return "box"
        elif any(word in user_prompt_lower for word in ["violin", "distribution", "shape"]):
            return "violin"
        elif any(word in user_prompt_lower for word in ["heatmap", "heat", "matrix", "correlation"]):
            return "heatmap"
        elif any(word in user_prompt_lower for word in ["bubble", "size", "three dimensional"]):
            return "bubble"
        elif any(word in user_prompt_lower for word in ["radar", "spider", "polar"]):
            return "radar"
        elif any(word in user_prompt_lower for word in ["density", "kde", "kernel"]):
            return "density"
        else:
            return "bar"  # Default fallback 