"""
Draft or Fix Code Node for LLM-Powered Renderer

This node generates Plotly Express code using LLM, or fixes code based on errors.
Includes local validation (AST, regex, function presence) before passing to sandbox.

Enhanced with:
- Chart-specific templates for Plotly Express
- Semantic data hints (dtypes, cardinality, stats)
- Style guidance for interactive visualization
- Better validation for Plotly figures
"""

import ast
import re
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np

from .base_node import BaseNode

# Security patterns to deny
FORBIDDEN_PATTERNS = [
    r'os\.',
    r'subprocess',
    r'import os',
    r'import subprocess',
    r'open\s*\(',
    r'file\s*\(',
    r'exec\s*\(',
    r'eval\s*\(',
    r'__import__',
    r'globals\s*\(',
    r'locals\s*\(',
    r'setattr',
    r'getattr',
    r'delattr',
    r'hasattr',
    r'/etc',
    r'/proc',
    r'/sys',
    r'\.remove\(',
    r'\.unlink\(',
    r'\.rmdir\(',
    r'\.system\(',
]

# Allowed imports for Plotly visualization
ALLOWED_IMPORTS = {
    'plotly', 'plotly.express', 'plotly.graph_objects', 'plotly.io',
    'pandas', 'numpy', 'datetime', 'math'
}

# Modern color suggestions for different chart types
MODERN_COLORS = {
    "single": ["#FF6B6B", "#4ECDC4", "#45B7D1", "#FD79A8", "#A29BFE"],
    "gradient": ["#667eea", "#764ba2", "#f093fb", "#f5576c", "#4facfe"],
    "categorical": ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7", "#DDA0DD", "#74B9FF", "#A29BFE"],
    "diverging": ["#e74c3c", "#ecf0f1", "#3498db"],
    "sequential": ["#FFF3E0", "#FFE0B2", "#FFCC80", "#FFB74D", "#FFA726", "#FF9800", "#FB8C00", "#F57C00"]
}

MAX_CODE_LINES = 100  # Keep it simple - no complex visualizations

# Chart-specific template guidance for Plotly Express - SIMPLE & MODERN
CHART_TEMPLATES = {
    "scatter": """
SCATTER PLOT - Keep it simple & colorful with Plotly Express:
- Use px.scatter(df, x='col1', y='col2', color='group_col')
- Set template='plotly_white' for clean background
- Use color_discrete_sequence=MODERN_COLORS['categorical'] for vibrant colors
- Add size parameter for bubble effects if appropriate
- Keep hover_data minimal""",
    
    "line": """
LINE PLOT - Bold & clean with Plotly Express:
- Use px.line(df, x='col1', y='col2', color='group_col')
- Set template='plotly_white' and line_shape='linear'
- Use color_discrete_sequence=MODERN_COLORS['categorical'] for multiple lines
- Keep markers minimal or off
- Clean, smooth lines only""",
    
    "bar": """
BAR CHART - Vibrant & simple with Plotly Express:
- Use px.bar(df, x='col1', y='col2', color='group_col')
- Set template='plotly_white' for clean background
- Use color_discrete_sequence=MODERN_COLORS['categorical']
- Keep it simple with minimal customization
- Let the colors tell the story""",
    
    "histogram": """
HISTOGRAM - Clean & bright with Plotly Express:
- Use px.histogram(df, x='col1', color='group_col')
- Set template='plotly_white' and nbins=25
- Use color_discrete_sequence=MODERN_COLORS['categorical']
- No density curves or overlays
- Just clean, colorful bars""",
    
    "box": """
BOX PLOT - Simple & distinct with Plotly Express:
- Use px.box(df, x='col1', y='col2', color='group_col')
- Set template='plotly_white'
- Use color_discrete_sequence=MODERN_COLORS['categorical']
- Standard boxes only, no fancy variations
- Bold colors, clean look""",
    
    "heatmap": """
HEATMAP - Vibrant colors with Plotly Express:
- Use px.imshow(df.corr()) for correlation matrix
- Set template='plotly_white' and color_continuous_scale='viridis'
- Clean colorbar on the side
- Let the colors tell the story""",
    
    "violin": """
VIOLIN PLOT - Clean distribution with Plotly Express:
- Use px.violin(df, x='col1', y='col2', color='group_col')
- Set template='plotly_white'
- Use color_discrete_sequence=MODERN_COLORS['categorical']
- Show quartiles and mean lines
- Keep it simple and colorful""",
    
    "pie": """
PIE CHART - Simple & colorful with Plotly Express:
- Use px.pie(df, values='col1', names='col2')
- Set template='plotly_white'
- Use color_discrete_sequence=MODERN_COLORS['categorical']
- Keep labels clean and readable
- Let colors distinguish categories""",
    
    "area": """
AREA CHART - Clean filled areas with Plotly Express:
- Use px.area(df, x='col1', y='col2', color='group_col')
- Set template='plotly_white'
- Use color_discrete_sequence=MODERN_COLORS['categorical']
- Keep it simple with minimal overlays
- Clean, filled areas only""",
    
    "bubble": """
BUBBLE CHART - Interactive & colorful with Plotly Express:
- Use px.scatter(df, x='col1', y='col2', size='col3', color='col4')
- Set template='plotly_white'
- Use color_discrete_sequence=MODERN_COLORS['categorical']
- Keep size_max reasonable (around 60)
- Let size and color tell the story""",
    
    "density": """
DENSITY PLOT - Use histogram with marginal distributions:
- Use px.histogram(df, x='col1', marginal='box')
- Set template='plotly_white'
- Use color_discrete_sequence=MODERN_COLORS['categorical']
- Keep it simple and clean
- Show distribution clearly""",
    
    "radar": """
RADAR CHART - Use line_polar for radar effect:
- Use px.line_polar(df, r='values', theta='categories')
- Set template='plotly_white'
- Use color_discrete_sequence=MODERN_COLORS['categorical']
- Keep it simple with minimal customization
- Clean radar visualization""",
    
    "treemap": """
TREEMAP - Hierarchical visualization with Plotly Express:
- Use px.treemap(df, path=['col1', 'col2'], values='col3')
- Set template='plotly_white'
- Use color_discrete_sequence=MODERN_COLORS['categorical']
- Keep labels clean and readable
- Let colors and sizes tell the story""",
    
    "sunburst": """
SUNBURST - Hierarchical pie with Plotly Express:
- Use px.sunburst(df, path=['col1', 'col2'], values='col3')
- Set template='plotly_white'
- Use color_discrete_sequence=MODERN_COLORS['categorical']
- Keep it simple and colorful
- Clean hierarchical visualization"""
}


class DraftOrFixCodeNode(BaseNode):
    """
    Enhanced Draft or Fix Code Node for Plotly Express
    
    Generates Plotly Express code using LLM with rich prompts and semantic hints.
    Performs validation before allowing code to proceed to sandbox.
    """
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate or fix visualization code
        
        Args:
            state: Current renderer state with error_msg, ingredients, etc.
            
        Returns:
            Dictionary with generated_code and potentially error_msg
        """
        self.log_info("Generating/fixing Plotly Express visualization code")
        
        try:
            # Build prompt based on whether we're fixing an error
            if state.get("error_msg"):
                prompt = self._build_fix_prompt(state)
                self.log_info(f"Fixing code due to error: {state['error_msg']}")
            else:
                prompt = self._build_initial_prompt(state)
                self.log_info("Generating initial Plotly Express code")
            
            # Call LLM
            response = self.llm.invoke(prompt)
            
            # Extract and clean code
            generated_code = self._extract_code_from_response(response.content)
            
            # Run local validation
            validation_result = self._validate_code(generated_code, state["ingredients"])
            
            if not validation_result["is_valid"]:
                self.log_warning(f"Code validation failed: {validation_result['error']}")
                return {
                    "generated_code": generated_code,
                    "error_msg": f"Validation error: {validation_result['error']}",
                    "retry_count": state.get("retry_count", 0) + 1
                }
            
            # Run dry-run validation with synthetic data
            dry_run_result = self._dry_run_validation(generated_code, state["ingredients"])
            
            if not dry_run_result["is_valid"]:
                self.log_warning(f"Dry-run failed: {dry_run_result['error']}")
                return {
                    "generated_code": generated_code,
                    "error_msg": f"Dry-run error: {dry_run_result['error']}",
                    "retry_count": state.get("retry_count", 0) + 1
                }
            
            # Success - return clean code
            return {
                "generated_code": generated_code,
                "error_msg": None
            }
            
        except Exception as e:
            self.log_error(f"Code generation failed: {str(e)}")
            return {
                "generated_code": "",
                "error_msg": f"Generation failed: {str(e)}",
                "retry_count": state.get("retry_count", 0) + 1
            }
    
    def _get_semantic_hints(self, df_sample: pd.DataFrame, columns: List[str], dtypes: Dict[str, str]) -> Dict[str, Any]:
        """Extract semantic hints about the data"""
        hints = {}
        
        for col in columns:
            dtype_str = dtypes.get(col, 'object')
            col_hints = {"dtype": dtype_str}
            
            if col not in df_sample.columns:
                continue
                
            series = df_sample[col]
            
            # Basic stats for different types
            if dtype_str in ['int64', 'float64']:
                col_hints.update({
                    "type": "numeric",
                    "min": float(series.min()) if not series.empty else None,
                    "max": float(series.max()) if not series.empty else None,
                    "mean": float(series.mean()) if not series.empty else None,
                    "unique_count": series.nunique()
                })
            elif dtype_str == 'object':
                col_hints.update({
                    "type": "categorical",
                    "unique_count": series.nunique(),
                    "top_values": series.value_counts().head(5).to_dict() if not series.empty else {}
                })
            elif 'datetime' in dtype_str:
                col_hints.update({
                    "type": "datetime",
                    "min": str(series.min()) if not series.empty else None,
                    "max": str(series.max()) if not series.empty else None
                })
            
            hints[col] = col_hints
            
        return hints
    
    def _build_initial_prompt(self, state: Dict[str, Any]) -> str:
        """Build enhanced initial code generation prompt for Plotly Express"""
        ingredients = state["ingredients"]
        chart_spec = ingredients['chart_specification']
        data_snapshot = ingredients['data_snapshot']
        html_output_path = ingredients['html_output_path']
        png_output_path = ingredients['png_output_path']
        
        # Basic chart info
        chart_type = chart_spec.get('chart_type', 'scatter')
        x_col = chart_spec['x_column']
        y_col = chart_spec['y_column']
        
        # Additional encodings
        hue_col = chart_spec.get('hue_column')
        size_col = chart_spec.get('size_column')
        
        # Get chart-specific guidance
        chart_guidance = CHART_TEMPLATES.get(chart_type, CHART_TEMPLATES['scatter'])
        
        # Build enhanced prompt
        prompt = f"""Create a SIMPLE, COLORFUL, and MODERN Plotly Express interactive visualization.

REQUEST: {ingredients['user_ask']}

DATA INFO:
- Columns: {data_snapshot['columns']}
- Shape: {data_snapshot['shape']}

CHART DETAILS:
- Type: {chart_type}
- X: {x_col}
- Y: {y_col}
{f'- Color by: {hue_col}' if hue_col else ''}
{f'- Size by: {size_col}' if size_col else ''}

{chart_guidance}

🎨 STYLE RULES - KEEP IT SIMPLE & COLORFUL:
- Use Plotly Express (import plotly.express as px)
- Set template='plotly_white' for clean background
- Use color_discrete_sequence from MODERN_COLORS for vibrant colors
- MINIMAL customization - let Plotly handle the aesthetics
- Interactive features are good but keep them simple
- Clean, modern color schemes

REQUIREMENTS:
```python
def draw_chart(df):
    \"\"\"Simple {chart_type} visualization using Plotly Express.\"\"\"
    import plotly.express as px
    import plotly.graph_objects as go
    import plotly.io as pio
    import pandas as pd
    import numpy as np
    
    # Modern color palette
    MODERN_COLORS = {{
        "categorical": ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7", "#DDA0DD", "#74B9FF", "#A29BFE"],
        "sequential": ["#FFF3E0", "#FFE0B2", "#FFCC80", "#FFB74D", "#FFA726", "#FF9800", "#FB8C00", "#F57C00"]
    }}
    
    # Handle missing data
    df = df.dropna(subset=['{x_col}', '{y_col}'])
    
    # Create Plotly Express figure
    fig = px.{chart_type}(df, x='{x_col}', y='{y_col}'{f", color='{hue_col}'" if hue_col else ""})
    
    # Apply clean styling
    fig.update_layout(
        template='plotly_white',
        font=dict(size=14, family='Inter, sans-serif'),
        margin=dict(t=60, r=20, b=60, l=60),
        title=dict(
            text="{chart_spec.get('title', 'Visualization')}",
            font=dict(size=18, weight='bold'),
            x=0.5
        ),
        xaxis_title='{x_col}'.replace('_', ' ').title(),
        yaxis_title='{y_col}'.replace('_', ' ').title()
    )
    
    # Use modern colors if grouping
    if hasattr(fig, 'update_traces'):
        fig.update_traces(marker=dict(size=8, line=dict(width=0.5, color='white')))
    
    # Save both HTML (interactive) and PNG (static) versions
    fig.write_html("{html_output_path}", include_plotlyjs="cdn")
    fig.write_image("{png_output_path}", scale=3)
    
    return fig
```

IMPORTANT:
- Use Plotly Express for simplicity and modern aesthetics
- Keep the code CLEAN and UNCLUTTERED
- Let interactive features enhance, not overwhelm
- Use the modern color palette provided
- Save BOTH HTML and PNG formats
- Return the figure object

Generate ONLY the complete function code:"""
        
        return prompt
    
    def _build_fix_prompt(self, state: Dict[str, Any]) -> str:
        """Build prompt to fix Plotly Express code based on error"""
        ingredients = state["ingredients"]
        previous_code = state.get("generated_code", "")
        error_msg = state["error_msg"]
        html_output_path = ingredients['html_output_path']
        png_output_path = ingredients['png_output_path']
        
        # Get column info for validation hints
        columns = ingredients['data_snapshot']['columns']
        
        prompt = f"""Fix the Plotly Express visualization code while keeping it SIMPLE and COLORFUL.

PREVIOUS CODE:
{previous_code}

ERROR: {error_msg}

AVAILABLE COLUMNS: {columns}

FIX REQUIREMENTS:
- Resolve the error but KEEP IT SIMPLE
- Use Plotly Express (import plotly.express as px)
- Use template='plotly_white' for clean background
- Use modern, vibrant colors
- Function: draw_chart(df) -> go.Figure
- Save both HTML and PNG formats:
  - HTML: {html_output_path}
  - PNG: {png_output_path}
- Use fig.write_html() AND fig.write_image() for both outputs

STYLE REMINDER:
- Clean white background with template='plotly_white'
- Bold, bright colors from MODERN_COLORS
- Simple chart, no clutter
- Interactive features but keep them minimal
- Generate BOTH HTML and PNG outputs

Generate ONLY the complete fixed function code:"""
        
        return prompt
    
    def _extract_code_from_response(self, response: str) -> str:
        """Extract Python code from LLM response"""
        # Remove markdown code blocks
        code = re.sub(r'```python\n?', '', response)
        code = re.sub(r'```\n?', '', code)
        
        # Remove any leading/trailing whitespace
        code = code.strip()
        
        return code
    
    def _validate_code(self, code: str, ingredients: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced validation with column checking and AST analysis for Plotly"""
        # 1. Line budget check (now percentage based)
        lines = code.split('\n')
        base_template_lines = 30  # Approximate template size
        max_allowed = int(base_template_lines * 6)  # 600% of template
        
        if len(lines) > max_allowed:
            return {
                "is_valid": False,
                "error": f"Code exceeds reasonable length ({len(lines)} lines, max {max_allowed})"
            }
        
        # 2. Regex denial list check
        for pattern in FORBIDDEN_PATTERNS:
            if re.search(pattern, code, re.IGNORECASE):
                return {
                    "is_valid": False,
                    "error": f"Forbidden pattern detected: {pattern}"
                }
        
        # 3. AST parse and validation
        try:
            tree = ast.parse(code)
            
            # Check imports
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name not in ALLOWED_IMPORTS:
                            return {
                                "is_valid": False,
                                "error": f"Forbidden import: {alias.name}"
                            }
                elif isinstance(node, ast.ImportFrom):
                    if node.module and node.module not in ALLOWED_IMPORTS:
                        # Check for submodules
                        base_module = node.module.split('.')[0]
                        if base_module not in ALLOWED_IMPORTS:
                            return {
                                "is_valid": False,
                                "error": f"Forbidden import from: {node.module}"
                            }
            
            # 4. Column validation - check df[...] accesses
            available_columns = ingredients['data_snapshot']['columns']
            for node in ast.walk(tree):
                if isinstance(node, ast.Subscript):
                    # Check for df[column] pattern
                    if (isinstance(node.value, ast.Name) and node.value.id == 'df' and
                        isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str)):
                        col_name = node.slice.value
                        if col_name not in available_columns:
                            return {
                                "is_valid": False,
                                "error": f"Column '{col_name}' not found in data. Available: {available_columns}"
                            }
        
        except SyntaxError as e:
            return {
                "is_valid": False,
                "error": f"Syntax error: {str(e)}"
            }
        
        # 5. Function structure checks
        if 'def draw_chart(df):' not in code:
            return {
                "is_valid": False,
                "error": "Missing required function draw_chart(df)"
            }
        
        # 6. Check for Plotly-specific requirements
        if 'import plotly.express as px' not in code and 'import plotly.express' not in code:
            return {
                "is_valid": False,
                "error": "Missing required import: plotly.express"
            }
        
        # 7. Check for proper output handling - both HTML and PNG required
        if 'fig.write_html' not in code:
            return {
                "is_valid": False,
                "error": "Missing required fig.write_html() call for HTML output"
            }
        
        if 'fig.write_image' not in code:
            return {
                "is_valid": False,
                "error": "Missing required fig.write_image() call for PNG output"
            }
        
        # 8. Check for return statement
        if 'return fig' not in code:
            self.log_warning("Generated code missing return statement for figure")
        
        return {"is_valid": True, "error": None}
    
    def _dry_run_validation(self, code: str, ingredients: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform dry-run validation with synthetic data for Plotly figures
        
        Creates a small DataFrame with correct column names/types and tests the function
        """
        try:
            # Create synthetic DataFrame with correct columns
            columns = ingredients['data_snapshot']['columns']
            dtypes = ingredients['data_snapshot']['dtypes']
            
            # Build synthetic data
            synthetic_data = {}
            for col in columns:
                dtype_str = dtypes.get(col, 'object')
                
                if dtype_str in ['int64', 'int32']:
                    synthetic_data[col] = np.random.randint(0, 100, size=10)
                elif dtype_str in ['float64', 'float32']:
                    synthetic_data[col] = np.random.uniform(0, 100, size=10)
                elif 'datetime' in dtype_str:
                    synthetic_data[col] = pd.date_range('2023-01-01', periods=10)
                else:  # object/string
                    synthetic_data[col] = [f'cat_{i}' for i in range(10)]
            
            df_test = pd.DataFrame(synthetic_data)
            
            # Create a namespace for execution
            namespace = {
                'pd': pd,
                'np': np,
                'px': None,  # Will be imported by the function
                'go': None,  # Will be imported by the function
                'plotly': None,
            }
            
            # Execute the generated code to define the function
            exec(code, namespace)
            
            # Check if draw_chart function was created
            if 'draw_chart' not in namespace:
                return {
                    "is_valid": False,
                    "error": "Function draw_chart not defined after execution"
                }
            
            # Mock the write methods to prevent actual file writing
            import plotly.graph_objects as go
            import plotly.io as pio
            
            original_write_html = go.Figure.write_html
            original_write_image = go.Figure.write_image if hasattr(go.Figure, 'write_image') else None
            original_pio_write_image = pio.write_image
            
            # Mock the write methods
            go.Figure.write_html = lambda self, *args, **kwargs: None
            if hasattr(go.Figure, 'write_image'):
                go.Figure.write_image = lambda self, *args, **kwargs: None
            pio.write_image = lambda *args, **kwargs: None
            
            try:
                # Call the function
                result = namespace['draw_chart'](df_test)
                
                # Validate that it returns a Plotly figure
                if not isinstance(result, go.Figure):
                    return {
                        "is_valid": False,
                        "error": "draw_chart must return a plotly.graph_objects.Figure"
                    }
                
                # Try a lightweight serialization test
                result.to_json()
                
                return {"is_valid": True, "error": None}
                
            finally:
                # Restore the original methods
                go.Figure.write_html = original_write_html
                if original_write_image:
                    go.Figure.write_image = original_write_image
                pio.write_image = original_pio_write_image
                
        except Exception as e:
            # Extract meaningful error message
            error_msg = str(e)
            
            # Common error patterns to provide better feedback
            if "KeyError" in error_msg:
                return {
                    "is_valid": False,
                    "error": f"Column access error: {error_msg}"
                }
            elif "NameError" in error_msg:
                return {
                    "is_valid": False,
                    "error": f"Missing import or undefined variable: {error_msg}"
                }
            elif "AttributeError" in error_msg:
                return {
                    "is_valid": False,
                    "error": f"Invalid method or attribute: {error_msg}"
                }
            elif "ValueError" in error_msg and "plotly" in error_msg.lower():
                return {
                    "is_valid": False,
                    "error": f"Plotly configuration error: {error_msg}"
                }
            else:
                return {
                    "is_valid": False,
                    "error": f"Runtime error in dry-run: {error_msg}"
                } 