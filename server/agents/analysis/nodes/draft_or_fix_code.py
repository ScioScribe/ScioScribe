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
        
        # Basic chart info
        chart_type = chart_spec.get('chart_type', 'scatter')
        x_col = chart_spec['x_column']
        y_col = chart_spec['y_column']
        
        # Additional encodings
        hue_col = chart_spec.get('hue_column')
        size_col = chart_spec.get('size_column')
        
        # Get chart-specific guidance
        chart_guidance = CHART_TEMPLATES.get(chart_type, CHART_TEMPLATES['scatter'])
        
        # Build color parameter string
        color_param = f",\n        color='{hue_col}'" if hue_col else ""
        
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

GENERATE THIS EXACT STRUCTURE (modify only the chart type and parameters):

```python
def draw_chart(df):
    \"\"\"Create a {chart_type} visualization using Plotly Express.\"\"\"
    import plotly.express as px
    import plotly.graph_objects as go
    
    # Modern color palette
    colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7", "#DDA0DD", "#74B9FF", "#A29BFE"]
    
    # Clean data
    df = df.dropna(subset=['{x_col}', '{y_col}'])
    
    # Create figure
    fig = px.{chart_type}(
        df,
        x='{x_col}',
        y='{y_col}'{color_param},
        template='plotly_white',
        color_discrete_sequence=colors,
        title="{chart_spec.get('title', 'Visualization')}"
    )
    
    # Update layout for responsiveness
    fig.update_layout(
        font=dict(size=12),
        margin=dict(t=50, r=20, b=50, l=50),
        autosize=True,
        width=None,
        height=None
    )
    
    # Generate responsive HTML
    html_content = fig.to_html(
        include_plotlyjs="cdn",
        div_id="plotly-div",
        config={{'responsive': True, 'displayModeBar': True, 'displaylogo': False}}
    )
    
    # Add responsive CSS and resize handling
    responsive_html = html_content.replace(
        '<head>',
        '''<head>
    <style>
        html, body {{ 
            margin: 0; 
            padding: 0; 
            height: 100%; 
            width: 100%; 
            background: transparent; 
            overflow: hidden;
        }}
        #plotly-div {{ 
            height: 100%; 
            width: 100%; 
            margin: 0;
            padding: 0;
        }}
        .plotly-graph-div {{
            width: 100% !important;
            height: 100% !important;
            box-sizing: border-box;
        }}
    </style>'''
    ).replace(
        '</body>',
        '''
    <script>
        // Handle resize messages from parent
        window.addEventListener('message', function(event) {{
            if (event.data.type === 'resize') {{
                setTimeout(() => {{
                    Plotly.Plots.resize('plotly-div');
                }}, 100);
            }}
        }});
        
        // Handle window resize
        window.addEventListener('resize', function() {{
            Plotly.Plots.resize('plotly-div');
        }});
    </script>
</body>'''
    )
    
    return fig, responsive_html
```

CRITICAL RULES:
1. Copy this structure EXACTLY
2. Only modify the px.{chart_type} call and its parameters
3. Do not add hasattr, try/except, or complex conditions
4. Keep it simple and clean
5. Return exactly: fig, responsive_html

Generate ONLY the complete function code:"""
        
        return prompt
    
    def _build_fix_prompt(self, state: Dict[str, Any]) -> str:
        """Build prompt to fix Plotly Express code based on error"""
        ingredients = state["ingredients"]
        previous_code = state.get("generated_code", "")
        error_msg = state["error_msg"]
        
        # Get column info for validation hints
        columns = ingredients['data_snapshot']['columns']
        
        prompt = f"""Fix the Plotly Express visualization code using this EXACT template:

PREVIOUS CODE:
{previous_code}

ERROR: {error_msg}

AVAILABLE COLUMNS: {columns}

USE THIS EXACT STRUCTURE:
```python
def draw_chart(df):
    \"\"\"Create visualization using Plotly Express.\"\"\"
    import plotly.express as px
    import plotly.graph_objects as go
    
    # Modern color palette
    colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7", "#DDA0DD", "#74B9FF", "#A29BFE"]
    
    # Clean data (adjust column names as needed)
    df = df.dropna()
    
    # Create figure (modify chart type and parameters to fix the error)
    fig = px.scatter(  # Replace with correct chart type
        df,
        x='column1',  # Replace with correct column
        y='column2',  # Replace with correct column
        template='plotly_white',
        color_discrete_sequence=colors,
        title="Visualization"
    )
    
    # Update layout for responsiveness
    fig.update_layout(
        font=dict(size=12),
        margin=dict(t=50, r=20, b=50, l=50),
        autosize=True,
        width=None,
        height=None
    )
    
    # Generate responsive HTML
    html_content = fig.to_html(
        include_plotlyjs="cdn",
        div_id="plotly-div",
        config={{'responsive': True, 'displayModeBar': True, 'displaylogo': False}}
    )
    
    # Add responsive CSS and resize handling
    responsive_html = html_content.replace(
        '<head>',
        '''<head>
    <style>
        html, body {{ 
            margin: 0; 
            padding: 0; 
            height: 100%; 
            width: 100%; 
            background: transparent; 
            overflow: hidden;
        }}
        #plotly-div {{ 
            height: 100%; 
            width: 100%; 
            margin: 0;
            padding: 0;
        }}
        .plotly-graph-div {{
            width: 100% !important;
            height: 100% !important;
            box-sizing: border-box;
        }}
    </style>'''
    ).replace(
        '</body>',
        '''
    <script>
        // Handle resize messages from parent
        window.addEventListener('message', function(event) {{
            if (event.data.type === 'resize') {{
                setTimeout(() => {{
                    Plotly.Plots.resize('plotly-div');
                }}, 100);
            }}
        }});
        
        // Handle window resize
        window.addEventListener('resize', function() {{
            Plotly.Plots.resize('plotly-div');
        }});
    </script>
</body>'''
    )
    
    return fig, responsive_html
```

CRITICAL: 
- Use this exact structure to fix the error
- Only modify chart type and column names
- NO hasattr, try/except, or complex conditions
- Keep it simple and clean

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
        
        # 7. Check for proper HTML content generation
        if 'fig.to_html' not in code:
            return {
                "is_valid": False,
                "error": "Missing required fig.to_html() call for HTML content generation"
            }
        
        # 8. Check for return statement
        if 'return fig, responsive_html' not in code and 'return fig, html_content' not in code:
            return {
                "is_valid": False,
                "error": "Missing required return statement: 'return fig, responsive_html' or 'return fig, html_content'"
            }
        
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
            
            import plotly.graph_objects as go
            
            # Call the function (should return fig, html_content)
            result = namespace['draw_chart'](df_test)
            
            # Validate that it returns a tuple with figure and HTML content
            if not isinstance(result, tuple) or len(result) != 2:
                return {
                    "is_valid": False,
                    "error": "draw_chart must return a tuple: (fig, html_content)"
                }
            
            fig, html_content = result
            
            # Validate that first element is a Plotly figure
            if not isinstance(fig, go.Figure):
                return {
                    "is_valid": False,
                    "error": "First return value must be a plotly.graph_objects.Figure"
                }
            
            # Validate that second element is HTML content string
            if not isinstance(html_content, str) or not html_content.strip():
                return {
                    "is_valid": False,
                    "error": "Second return value must be non-empty HTML content string"
                }
            
            # Validate HTML content contains expected elements
            if not any(tag in html_content.lower() for tag in ['<div', '<script', 'plotly']):
                return {
                    "is_valid": False,
                    "error": "HTML content does not appear to be valid Plotly HTML"
                }
            
            return {"is_valid": True, "error": None}
                
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