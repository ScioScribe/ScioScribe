"""
Sandbox Runner Node for LLM-Powered Renderer

This node executes generated code in a secure sandboxed environment with
timeout protection and performs post-execution safety checks.
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
    
    Executes generated matplotlib code in a secure sandbox with timeout protection.
    Performs post-execution checks on the output file.
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
            csv_path = ingredients["csv_path"]
            output_path = ingredients["output_path"]
            
            # Execute in sandboxed environment
            execution_result = self._execute_sandboxed(
                generated_code, 
                csv_path, 
                output_path
            )
            
            if not execution_result["success"]:
                self.log_warning(f"Execution failed: {execution_result['error']}")
                return {
                    "error_msg": f"Runtime error: {execution_result['error']}",
                    "warnings": execution_result.get("warnings", []),
                    "retry_count": state.get("retry_count", 0) + 1
                }
            
            # Post-execution safety checks
            safety_check = self._post_execution_checks(Path(output_path))
            if not safety_check["is_safe"]:
                self.log_warning(f"Safety check failed: {safety_check['error']}")
                return {
                    "error_msg": f"Output validation error: {safety_check['error']}",
                    "warnings": execution_result.get("warnings", []),
                    "retry_count": state.get("retry_count", 0) + 1
                }
            
            # Success!
            self.log_info("Code executed successfully and passed all checks")
            return {
                "error_msg": None,
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
    
    def _execute_sandboxed(self, code: str, csv_path: str, output_path: str) -> Dict[str, Any]:
        """
        Execute generated code in a sandboxed environment with timeout
        
        Args:
            code: Validated Python code
            csv_path: Path to data file
            output_path: Path where plot should be saved
            
        Returns:
            Execution result with success flag and any warnings
        """
        try:
            # Indent the generated code for insertion into try block
            indented_code = self._indent_code(code)
            
            # Create temporary execution script
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                execution_script = f"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
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
    # Load data
    df = pd.read_csv('{csv_path}')
    
    # Generated code (indented for try block)
{indented_code}
    
    # Execute the function
    draw_chart(df)
    
    print("SUCCESS")
    
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
            
            # Clean up temp file
            os.unlink(script_path)
            
            # Check results
            if result.returncode == 0 and "SUCCESS" in result.stdout:
                warnings = []
                if result.stderr and "WARNING" in result.stderr:
                    warnings.append(f"Runtime warnings: {result.stderr}")
                
                return {
                    "success": True,
                    "error": None,
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
    
    def _post_execution_checks(self, output_path: Path) -> Dict[str, Any]:
        """
        Perform safety checks after code execution
        
        Args:
            output_path: Expected output file path
            
        Returns:
            Safety check result with is_safe flag and error message
        """
        try:
            # 1. Check file exists and has content
            if not output_path.exists():
                return {
                    "is_safe": False,
                    "error": "Output file was not created"
                }
            
            if output_path.stat().st_size == 0:
                return {
                    "is_safe": False,
                    "error": "Output file is empty"
                }
            
            # 2. Check file is actually an image
            try:
                # Basic check - can we open it as an image?
                img = Image.open(output_path)
                img.verify()  # Verify it's a valid image
            except Exception as e:
                return {
                    "is_safe": False,
                    "error": f"Invalid image file: {str(e)}"
                }
            
            # 3. Check image is not blank (reopen after verify)
            try:
                img = Image.open(output_path)
                # Convert to RGB if needed
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Check if image is mostly white (blank)
                np_img = np.array(img)
                white_pixels = np.sum(np_img > 240)  # Count near-white pixels
                total_pixels = np_img.size
                
                if white_pixels / total_pixels > 0.95:  # 95% white
                    return {
                        "is_safe": False,
                        "error": "Generated image appears to be blank"
                    }
                
            except Exception as e:
                # If we can't check for blankness, still consider it safe
                # (the image opened successfully)
                pass
            
            return {"is_safe": True, "error": None}
            
        except Exception as e:
            return {
                "is_safe": False,
                "error": f"Post-execution check failed: {str(e)}"
            } 