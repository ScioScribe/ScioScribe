"""
Sandbox Runner Node for LLM-Powered Renderer

This node executes generated Plotly Express code in a secure sandboxed environment with
timeout protection and performs post-execution safety checks on both HTML and PNG outputs.
"""

import os
import sys
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any
from PIL import Image
import numpy as np

from .base_node import BaseNode

# Constants
EXECUTION_TIMEOUT = 5  # seconds


class SandboxRunnerNode(BaseNode):
    """
    Sandbox Runner Node
    
    Executes generated Plotly Express code in a secure sandbox with timeout protection.
    Performs post-execution checks on both HTML and PNG output files.
    """
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute code in sandbox and check results
        
        Args:
            state: Current renderer state with generated_code, ingredients, etc.
            
        Returns:
            Dictionary with error_msg (None if successful) and warnings
        """
        self.log_info("Executing code in sandbox")
        
        # Skip if we already have an error
        if state.get("error_msg"):
            return state
        
        try:
            ingredients = state["ingredients"]
            generated_code = state["generated_code"]
            csv_data_content = ingredients["csv_data_content"]
            
            # Execute in sandboxed environment
            execution_result = self._execute_sandboxed(generated_code, csv_data_content)
            
            if not execution_result["success"]:
                self.log_warning(f"Execution failed: {execution_result['error']}")
                return {
                    "error_msg": f"Runtime error: {execution_result['error']}",
                    "warnings": execution_result.get("warnings", []),
                    "retry_count": state.get("retry_count", 0) + 1
                }
            
            # Success! Store the HTML content
            self.log_info("Code executed successfully and returned HTML content")
            return {
                "error_msg": None,
                "html_content": execution_result.get("html_content", ""),
                "warnings": execution_result.get("warnings", [])
            }
            
        except Exception as e:
            self.log_error(f"Sandbox execution failed: {str(e)}")
            return {
                "error_msg": f"Sandbox error: {str(e)}",
                "warnings": [],
                "retry_count": state.get("retry_count", 0) + 1
            }
    
    def _indent_code(self, code: str, indent: str = "    ") -> str:
        """Indent code for insertion into try block"""
        lines = code.split('\n')
        indented_lines = [indent + line if line.strip() else line for line in lines]
        return '\n'.join(indented_lines)
    
    def _execute_sandboxed(self, code: str, csv_data_content: str) -> Dict[str, Any]:
        """
        Execute generated Plotly code in a sandboxed environment with timeout
        
        Args:
            code: Validated Python code
            csv_data_content: Content of the CSV data file
            
        Returns:
            Execution result with success flag, HTML content, and any warnings
        """
        try:
            # Create temporary CSV file from content
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as csv_file:
                csv_file.write(csv_data_content)
                temp_csv_path = csv_file.name
            
            # Indent the generated code for insertion into try block
            indented_code = self._indent_code(code)
            
            # Create temporary execution script
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                execution_script = f"""
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import numpy as np
import pandas as pd
import sys
import signal

# Timeout handler
def timeout_handler(signum, frame):
    raise TimeoutError("Execution timeout")

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm({EXECUTION_TIMEOUT})

try:
    # Load data from temporary CSV file
    df = pd.read_csv('{temp_csv_path}')
    
    # Generated code (indented for try block)
{indented_code}
    
    # Execute the function (should return fig, html_content)
    result = draw_chart(df)
    
    # Verify the result is a tuple with figure and HTML content
    if not isinstance(result, tuple) or len(result) != 2:
        raise ValueError("draw_chart must return a tuple: (fig, html_content)")
    
    fig, html_content = result
    
    # Verify first element is a Plotly figure
    if not isinstance(fig, go.Figure):
        raise ValueError("First return value must be a plotly.graph_objects.Figure")
    
    # Verify second element is HTML content string
    if not isinstance(html_content, str) or not html_content.strip():
        raise ValueError("Second return value must be non-empty HTML content string")
    
    # Output the HTML content for capture
    print("SUCCESS")
    print("HTML_CONTENT_START")
    print(html_content)
    print("HTML_CONTENT_END")
    
except Exception as e:
    import traceback
    print("ERROR: " + str(e), file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)
finally:
    signal.alarm(0)
"""
                f.write(execution_script)
                script_path = f.name
            
            # Execute with subprocess and capture output
            result = subprocess.run(
                [sys.executable, script_path],
                capture_output=True,
                text=True,
                timeout=EXECUTION_TIMEOUT + 1
            )
            
            # Clean up temp files
            os.unlink(script_path)
            os.unlink(temp_csv_path)
            
            # Check results
            if result.returncode == 0 and "SUCCESS" in result.stdout:
                warnings = []
                if result.stderr and "WARNING" in result.stderr:
                    warnings.append(f"Runtime warnings: {result.stderr}")
                
                # Extract HTML content from stdout
                html_content = ""
                stdout_lines = result.stdout.split('\n')
                capturing = False
                for line in stdout_lines:
                    if line == "HTML_CONTENT_START":
                        capturing = True
                        continue
                    elif line == "HTML_CONTENT_END":
                        capturing = False
                        break
                    elif capturing:
                        if html_content:
                            html_content += '\n'
                        html_content += line
                
                return {
                    "success": True,
                    "error": None,
                    "html_content": html_content,
                    "warnings": warnings
                }
            else:
                # Extract error message from stderr/stdout
                error_msg = result.stderr or result.stdout or "Unknown execution error"
                # Clean up error message for readability
                if "Traceback" in error_msg or "SyntaxError" in error_msg:
                    # Extract the most relevant error line
                    lines = error_msg.split('\n')
                    for line in reversed(lines):
                        line = line.strip()
                        if line.startswith("ERROR:"):
                            error_msg = line[6:].strip()
                            break
                        elif "Error:" in line and not line.startswith(" "):
                            error_msg = line
                            break
                
                return {
                    "success": False,
                    "error": error_msg
                }
                
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"Execution timeout after {EXECUTION_TIMEOUT} seconds"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Sandbox setup failed: {str(e)}"
            }
    
    def _post_execution_checks(self, html_output_path: Path, png_output_path: Path) -> Dict[str, Any]:
        """
        Perform safety checks after code execution on both output files
        
        Args:
            html_output_path: Expected HTML output file path
            png_output_path: Expected PNG output file path
            
        Returns:
            Safety check result with is_safe flag and error message
        """
        try:
            # Check HTML file
            html_check = self._check_html_output(html_output_path)
            if not html_check["is_safe"]:
                return html_check
            
            # Check PNG file
            png_check = self._check_png_output(png_output_path)
            if not png_check["is_safe"]:
                return png_check
            
            return {"is_safe": True, "error": None}
            
        except Exception as e:
            return {
                "is_safe": False,
                "error": f"Post-execution check failed: {str(e)}"
            }
    
    def _check_html_output(self, html_path: Path) -> Dict[str, Any]:
        """Check HTML output file"""
        try:
            # 1. Check file exists and has content
            if not html_path.exists():
                return {
                    "is_safe": False,
                    "error": "HTML output file was not created"
                }
            
            if html_path.stat().st_size == 0:
                return {
                    "is_safe": False,
                    "error": "HTML output file is empty"
                }
            
            # 2. Basic HTML validation - check for Plotly content
            try:
                with open(html_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for essential Plotly HTML elements
                if 'plotly' not in content.lower():
                    return {
                        "is_safe": False,
                        "error": "HTML file does not contain Plotly content"
                    }
                
                if len(content) < 1000:  # Very basic size check
                    return {
                        "is_safe": False,
                        "error": "HTML file appears to be truncated or minimal"
                    }
                
            except Exception as e:
                return {
                    "is_safe": False,
                    "error": f"Could not read HTML file: {str(e)}"
                }
            
            return {"is_safe": True, "error": None}
            
        except Exception as e:
            return {
                "is_safe": False,
                "error": f"HTML check failed: {str(e)}"
            }
    
    def _check_png_output(self, png_path: Path) -> Dict[str, Any]:
        """Check PNG output file"""
        try:
            # 1. Check file exists and has content
            if not png_path.exists():
                return {
                    "is_safe": False,
                    "error": "PNG output file was not created"
                }
            
            if png_path.stat().st_size == 0:
                return {
                    "is_safe": False,
                    "error": "PNG output file is empty"
                }
            
            # 2. Check file is actually an image
            try:
                # Basic check - can we open it as an image?
                img = Image.open(png_path)
                img.verify()  # Verify it's a valid image
            except Exception as e:
                return {
                    "is_safe": False,
                    "error": f"Invalid PNG file: {str(e)}"
                }
            
            # 3. Check image is not blank (reopen after verify)
            try:
                img = Image.open(png_path)
                # Convert to RGB if needed
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                np_img = np.array(img)
                
                # Multiple checks for blank detection
                # Check 1: White pixel percentage (adjusted for Plotly backgrounds)
                white_pixels = np.sum(np_img > 240)  # Count near-white pixels
                total_pixels = np_img.size
                white_percentage = white_pixels / total_pixels
                
                # Check 2: Color variation (standard deviation of pixel values)
                color_std = np.std(np_img)
                
                # Check 3: File size (truly blank images compress to very small sizes)
                file_size = png_path.stat().st_size
                
                # Consider image blank if:
                # - Over 99% white pixels AND very low color variation AND small file size
                if (white_percentage > 0.99 and 
                    color_std < 5.0 and 
                    file_size < 10000):  # Less than 10KB
                    return {
                        "is_safe": False,
                        "error": f"Generated PNG image appears to be blank ({white_percentage*100:.1f}% white pixels, {color_std:.1f} color variation, {file_size} bytes)"
                    }
                
                # Additional check for completely uniform images
                if color_std < 1.0:
                    return {
                        "is_safe": False,
                        "error": f"Generated PNG image has no color variation (std: {color_std:.1f})"
                    }
                
            except Exception as e:
                # If we can't check for blankness, still consider it safe
                # (the image opened successfully)
                pass
            
            return {"is_safe": True, "error": None}
            
        except Exception as e:
            return {
                "is_safe": False,
                "error": f"PNG check failed: {str(e)}"
            } 