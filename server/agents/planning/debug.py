"""
Logging and debugging utilities for the experiment planning agent system.

This module provides comprehensive logging setup, state debugging utilities,
performance monitoring, and error tracking for the planning agent workflow.
"""

import logging
import json
import time
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from contextlib import contextmanager
from functools import wraps
import traceback
import sys
from pathlib import Path

from .state import ExperimentPlanState, PLANNING_STAGES
from .validation import StateValidationError
from .serialization import serialize_state_to_dict

# Create logger for this module
logger = logging.getLogger(__name__)


class StateDebugger:
    """Debug utilities for ExperimentPlanState objects."""
    
    def __init__(self, log_level: str = "INFO"):
        self.logger = logging.getLogger(f"{__name__}.StateDebugger")
        self.logger.setLevel(getattr(logging, log_level.upper()))
        
        # Track state changes
        self.state_history: List[Dict[str, Any]] = []
        self.performance_metrics: Dict[str, List[float]] = {}
    
    def log_state_change(
        self,
        state: ExperimentPlanState,
        operation: str,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log a state change with full context.
        
        Args:
            state: Current state
            operation: Description of the operation
            details: Additional details about the change
        """
        try:
            state_snapshot = {
                "timestamp": datetime.utcnow().isoformat(),
                "operation": operation,
                "experiment_id": state.get("experiment_id"),
                "current_stage": state.get("current_stage"),
                "errors": state.get("errors", []),
                "details": details or {}
            }
            
            self.state_history.append(state_snapshot)
            
            self.logger.info(
                f"State change: {operation}",
                extra={
                    "experiment_id": state.get("experiment_id"),
                    "stage": state.get("current_stage"),
                    "operation": operation,
                    "details": details
                }
            )
            
        except Exception as e:
            self.logger.error(f"Failed to log state change: {str(e)}")
    
    def validate_state_integrity(self, state: ExperimentPlanState) -> Dict[str, Any]:
        """Validate state integrity and return detailed report.
        
        Args:
            state: State to validate
            
        Returns:
            Validation report dictionary
        """
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "experiment_id": state.get("experiment_id"),
            "current_stage": state.get("current_stage"),
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "field_analysis": {}
        }
        
        try:
            # Check required fields (simplified schema)
            required_fields = [
                "experiment_id", "research_query", "current_stage",
                "errors", "chat_history"
            ]
            
            for field in required_fields:
                if field not in state:
                    report["errors"].append(f"Missing required field: {field}")
                    report["is_valid"] = False
                elif not state[field] and field not in ["errors"]:  # errors can be empty list
                    report["warnings"].append(f"Empty required field: {field}")
            
            # Check stage consistency
            current_stage = state.get("current_stage")
            if current_stage and current_stage not in PLANNING_STAGES:
                report["errors"].append(f"Invalid current stage: {current_stage}")
                report["is_valid"] = False
            
            # Analyze field completeness by stage
            for stage in PLANNING_STAGES:
                stage_fields = self._get_stage_fields(stage)
                completeness = self._analyze_field_completeness(state, stage_fields)
                report["field_analysis"][stage] = completeness
            
        except Exception as e:
            report["errors"].append(f"Validation error: {str(e)}")
            report["is_valid"] = False
        
        return report
    
    def _get_stage_fields(self, stage: str) -> List[str]:
        """Get relevant fields for a specific stage."""
        stage_fields = {
            "objective_setting": ["research_query", "experiment_objective", "hypothesis"],
            "variable_identification": ["independent_variables", "dependent_variables", "control_variables"],
            "experimental_design": ["experimental_groups", "control_groups", "sample_size"],
            "methodology_protocol": ["methodology_steps", "materials_equipment"],
            "data_planning": ["data_collection_plan", "data_analysis_plan", "potential_pitfalls"],
            "final_review": ["expected_outcomes", "ethical_considerations", "timeline"]
        }
        return stage_fields.get(stage, [])
    
    def _analyze_field_completeness(self, state: ExperimentPlanState, fields: List[str]) -> Dict[str, Any]:
        """Analyze completeness of fields for a stage."""
        analysis = {
            "total_fields": len(fields),
            "completed_fields": 0,
            "empty_fields": [],
            "populated_fields": [],
            "completion_percentage": 0
        }
        
        for field in fields:
            if field in state and state[field]:
                if isinstance(state[field], list) and len(state[field]) > 0:
                    analysis["completed_fields"] += 1
                    analysis["populated_fields"].append(field)
                elif isinstance(state[field], dict) and len(state[field]) > 0:
                    analysis["completed_fields"] += 1
                    analysis["populated_fields"].append(field)
                elif isinstance(state[field], str) and state[field].strip():
                    analysis["completed_fields"] += 1
                    analysis["populated_fields"].append(field)
                else:
                    analysis["empty_fields"].append(field)
            else:
                analysis["empty_fields"].append(field)
        
        if analysis["total_fields"] > 0:
            analysis["completion_percentage"] = (
                analysis["completed_fields"] / analysis["total_fields"]
            ) * 100
        
        return analysis
    
    def get_state_summary(self, state: ExperimentPlanState) -> Dict[str, Any]:
        """Get a comprehensive summary of the state.
        
        Args:
            state: State to summarize
            
        Returns:
            State summary dictionary
        """
        try:
            summary = {
                "experiment_id": state.get("experiment_id"),
                "current_stage": state.get("current_stage"),
                "progress": {
                    "total_stages": len(PLANNING_STAGES),
                    "completed_count": 0,  # LangGraph manages stage completion
                    "current_stage_index": PLANNING_STAGES.index(state.get("current_stage", "")) if state.get("current_stage") in PLANNING_STAGES else -1
                },
                "data_completeness": {},
                "errors": state.get("errors", []),
                "chat_history_length": len(state.get("chat_history", [])),
                # LangGraph manages timestamps via checkpoints
            }
            
            # Calculate progress percentage
            if summary["progress"]["total_stages"] > 0:
                summary["progress"]["percentage"] = (
                    summary["progress"]["completed_count"] / summary["progress"]["total_stages"]
                ) * 100
            
            # Analyze data completeness for each stage
            for stage in PLANNING_STAGES:
                stage_fields = self._get_stage_fields(stage)
                completeness = self._analyze_field_completeness(state, stage_fields)
                summary["data_completeness"][stage] = completeness["completion_percentage"]
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Failed to generate state summary: {str(e)}")
            return {"error": str(e)}
    
    def export_debug_report(self, state: ExperimentPlanState) -> str:
        """Export a comprehensive debug report as JSON.
        
        Args:
            state: State to report on
            
        Returns:
            JSON string of debug report
        """
        try:
            report = {
                "timestamp": datetime.utcnow().isoformat(),
                "debug_report_version": "1.0",
                "state_summary": self.get_state_summary(state),
                "validation_report": self.validate_state_integrity(state),
                "state_history": self.state_history[-10:],  # Last 10 changes
                "performance_metrics": self.performance_metrics,
                "serialized_state": serialize_state_to_dict(state)
            }
            
            return json.dumps(report, indent=2, default=str)
            
        except Exception as e:
            error_report = {
                "timestamp": datetime.utcnow().isoformat(),
                "error": f"Failed to generate debug report: {str(e)}",
                "traceback": traceback.format_exc()
            }
            return json.dumps(error_report, indent=2)
    
    def clear_history(self) -> None:
        """Clear the state history."""
        self.state_history.clear()
        self.performance_metrics.clear()
        self.logger.info("State history and performance metrics cleared")


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    enable_structured_logging: bool = True
) -> None:
    """Set up comprehensive logging for the planning agent system.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional file path for log output
        enable_structured_logging: Enable structured JSON logging
    """
    # Create formatters
    if enable_structured_logging:
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s", "module": "%(module)s", "function": "%(funcName)s", "line": %(lineno)d}'
        )
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Configure specific loggers
    planning_logger = logging.getLogger("server.agents.planning")
    planning_logger.setLevel(getattr(logging, log_level.upper()))
    
    logger.info(f"Logging configured with level: {log_level}")


def performance_monitor(operation_name_or_func=None, debugger: Optional[StateDebugger] = None):
    """
    Decorator for monitoring operation performance.
    
    Can be used as:
    1. Function decorator: @performance_monitor
    2. Decorator with args: @performance_monitor("custom_name")
    
    Args:
        operation_name_or_func: Either operation name string or function (when used as decorator)
        debugger: Optional StateDebugger instance for metrics storage
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            operation_name = operation_name_or_func if isinstance(operation_name_or_func, str) else func.__name__
            start_time = time.time()
            
            try:
                logger.debug(f"Starting operation: {operation_name}")
                result = func(*args, **kwargs)
                return result
                
            except Exception as e:
                logger.error(f"Operation {operation_name} failed: {str(e)}")
                raise
                
            finally:
                duration = time.time() - start_time
                logger.debug(f"Operation {operation_name} completed in {duration:.3f}s")
                
                if debugger:
                    if operation_name not in debugger.performance_metrics:
                        debugger.performance_metrics[operation_name] = []
                    debugger.performance_metrics[operation_name].append(duration)
        
        return wrapper
    
    # If used as a decorator without arguments
    if callable(operation_name_or_func):
        return decorator(operation_name_or_func)
    
    # If used as a decorator with arguments
    return decorator


@contextmanager
def performance_context(operation_name: str, debugger: Optional[StateDebugger] = None):
    """Context manager for monitoring operation performance."""
    start_time = time.time()
    
    try:
        logger.debug(f"Starting operation: {operation_name}")
        yield
        
    except Exception as e:
        logger.error(f"Operation {operation_name} failed: {str(e)}")
        raise
        
    finally:
        duration = time.time() - start_time
        logger.debug(f"Operation {operation_name} completed in {duration:.3f}s")
        
        if debugger:
            if operation_name not in debugger.performance_metrics:
                debugger.performance_metrics[operation_name] = []
            debugger.performance_metrics[operation_name].append(duration)


def trace_state_changes(debugger: StateDebugger):
    """Decorator to trace state changes in functions.
    
    Args:
        debugger: StateDebugger instance
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Try to find state argument
            state_arg = None
            for arg in args:
                if isinstance(arg, dict) and "experiment_id" in arg:
                    state_arg = arg
                    break
            
            if not state_arg:
                for value in kwargs.values():
                    if isinstance(value, dict) and "experiment_id" in value:
                        state_arg = value
                        break
            
            # Log function entry
            logger.debug(f"Entering function: {func.__name__}")
            
            try:
                with performance_context(func.__name__, debugger):
                    result = func(*args, **kwargs)
                
                # Log state change if state was modified
                if state_arg:
                    debugger.log_state_change(
                        state_arg,
                        f"function_{func.__name__}",
                        {"function": func.__name__, "args_count": len(args), "kwargs_count": len(kwargs)}
                    )
                
                return result
                
            except Exception as e:
                logger.error(f"Function {func.__name__} failed: {str(e)}")
                if state_arg:
                    debugger.log_state_change(
                        state_arg,
                        f"function_{func.__name__}_error",
                        {"function": func.__name__, "error": str(e)}
                    )
                raise
        
        return wrapper
    return decorator


def log_agent_interaction(
    agent_name: str,
    state: ExperimentPlanState,
    input_data: Dict[str, Any],
    output_data: Dict[str, Any],
    duration: float,
    debugger: Optional[StateDebugger] = None
) -> None:
    """Log agent interaction with comprehensive details.
    
    Args:
        agent_name: Name of the agent
        state: Current state
        input_data: Input data to the agent
        output_data: Output data from the agent
        duration: Execution duration
        debugger: Optional StateDebugger instance
    """
    interaction_log = {
        "agent": agent_name,
        "experiment_id": state.get("experiment_id"),
        "stage": state.get("current_stage"),
        "duration": duration,
        "input_size": len(json.dumps(input_data, default=str)),
        "output_size": len(json.dumps(output_data, default=str)),
        "timestamp": datetime.utcnow().isoformat()
    }
    
    logger.info(f"Agent interaction: {agent_name}", extra=interaction_log)
    
    if debugger:
        debugger.log_state_change(
            state,
            f"agent_{agent_name}",
            interaction_log
        )


def create_error_report(
    error: Exception,
    state: Optional[ExperimentPlanState] = None,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create a comprehensive error report.
    
    Args:
        error: The exception that occurred
        state: Optional current state
        context: Optional additional context
        
    Returns:
        Error report dictionary
    """
    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "error_type": type(error).__name__,
        "error_message": str(error),
        "traceback": traceback.format_exc(),
        "context": context or {}
    }
    
    if state:
        report["state_info"] = {
            "experiment_id": state.get("experiment_id"),
            "current_stage": state.get("current_stage"),
            "completed_stages": state.get("completed_stages", []),
            "errors": state.get("errors", [])
        }
    
    return report


def save_debug_snapshot(
    state: ExperimentPlanState,
    filename: Optional[str] = None,
    directory: str = "debug_snapshots"
) -> str:
    """Save a debug snapshot of the state to disk.
    
    Args:
        state: State to save
        filename: Optional filename (auto-generated if not provided)
        directory: Directory to save to
        
    Returns:
        Path to saved file
    """
    try:
        # Create directory if it doesn't exist
        Path(directory).mkdir(parents=True, exist_ok=True)
        
        # Generate filename if not provided
        if not filename:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            experiment_id = state.get("experiment_id", "unknown")[:8]
            filename = f"debug_{experiment_id}_{timestamp}.json"
        
        filepath = Path(directory) / filename
        
        # Create debugger and export report
        debugger = StateDebugger()
        debug_report = debugger.export_debug_report(state)
        
        # Save to file
        with open(filepath, 'w') as f:
            f.write(debug_report)
        
        logger.info(f"Debug snapshot saved to: {filepath}")
        return str(filepath)
        
    except Exception as e:
        logger.error(f"Failed to save debug snapshot: {str(e)}")
        raise


# Global debugger instance
_global_debugger = StateDebugger()


def get_global_debugger() -> StateDebugger:
    """Get the global debugger instance."""
    return _global_debugger 