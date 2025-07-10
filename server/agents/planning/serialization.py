"""
State serialization utilities for the experiment planning agent system.

This module provides functions to serialize and deserialize ExperimentPlanState
objects for storage, transmission, and debugging purposes with proper handling
of datetime objects and complex nested structures.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import json
import logging

from .state import ExperimentPlanState

logger = logging.getLogger(__name__)


def datetime_to_iso_string(dt: datetime) -> str:
    """Convert datetime to ISO string format.
    
    Args:
        dt: Datetime object to convert
        
    Returns:
        ISO formatted string
    """
    return dt.isoformat()


def iso_string_to_datetime(iso_string: str) -> datetime:
    """Convert ISO string to datetime object.
    
    Args:
        iso_string: ISO formatted datetime string
        
    Returns:
        Datetime object
    """
    # Handle various ISO formats
    if iso_string.endswith('Z'):
        iso_string = iso_string[:-1] + '+00:00'
    return datetime.fromisoformat(iso_string)


def serialize_chat_message(message: Dict[str, Any]) -> Dict[str, Any]:
    """Serialize a chat message with proper datetime handling.
    
    Args:
        message: Chat message dictionary
        
    Returns:
        Serialized message dictionary
    """
    serialized = message.copy()
    if 'timestamp' in serialized and isinstance(serialized['timestamp'], datetime):
        serialized['timestamp'] = datetime_to_iso_string(serialized['timestamp'])
    return serialized


def deserialize_chat_message(message: Dict[str, Any]) -> Dict[str, Any]:
    """Deserialize a chat message with proper datetime handling.
    
    Args:
        message: Serialized message dictionary
        
    Returns:
        Deserialized message dictionary
    """
    deserialized = message.copy()
    if 'timestamp' in deserialized and isinstance(deserialized['timestamp'], str):
        deserialized['timestamp'] = iso_string_to_datetime(deserialized['timestamp'])
    return deserialized


def serialize_state_to_dict(state: ExperimentPlanState) -> Dict[str, Any]:
    """Serialize ExperimentPlanState to a JSON-serializable dictionary.
    
    Args:
        state: ExperimentPlanState to serialize
        
    Returns:
        JSON-serializable dictionary
    """
    try:
        serialized = {}
        
        # Copy all fields from state
        for key, value in state.items():
            if key == 'chat_history' and isinstance(value, list):
                # Handle chat history serialization
                serialized[key] = [serialize_chat_message(msg) for msg in value]
            elif key == 'errors' and isinstance(value, list):
                # Handle errors list
                serialized[key] = []
                for error in value:
                    if isinstance(error, dict):
                        error_copy = error.copy()
                        if 'timestamp' in error_copy and isinstance(error_copy['timestamp'], datetime):
                            error_copy['timestamp'] = datetime_to_iso_string(error_copy['timestamp'])
                        serialized[key].append(error_copy)
                    else:
                        serialized[key].append(error)
            else:
                # Copy other fields as-is
                serialized[key] = value
        
        return serialized
        
    except Exception as e:
        logger.error(f"Failed to serialize state: {e}")
        raise


def deserialize_dict_to_state(data: Dict[str, Any]) -> ExperimentPlanState:
    """Deserialize a dictionary to ExperimentPlanState.
    
    Args:
        data: Dictionary to deserialize
        
    Returns:
        ExperimentPlanState object
    """
    try:
        deserialized = {}
        
        # Process each field
        for key, value in data.items():
            if key == 'chat_history' and isinstance(value, list):
                # Handle chat history deserialization
                deserialized[key] = [deserialize_chat_message(msg) for msg in value]
            elif key == 'errors' and isinstance(value, list):
                # Handle errors list
                deserialized[key] = []
                for error in value:
                    if isinstance(error, dict):
                        error_copy = error.copy()
                        if 'timestamp' in error_copy and isinstance(error_copy['timestamp'], str):
                            error_copy['timestamp'] = iso_string_to_datetime(error_copy['timestamp'])
                        deserialized[key].append(error_copy)
                    else:
                        deserialized[key].append(error)
            else:
                # Copy other fields as-is
                deserialized[key] = value
        
        return deserialized
        
    except Exception as e:
        logger.error(f"Failed to deserialize state: {e}")
        raise


def serialize_state_to_json(state: ExperimentPlanState) -> str:
    """Serialize ExperimentPlanState to JSON string.
    
    Args:
        state: ExperimentPlanState to serialize
        
    Returns:
        JSON string
    """
    try:
        serialized = serialize_state_to_dict(state)
        return json.dumps(serialized, indent=2)
    except Exception as e:
        logger.error(f"Failed to serialize state to JSON: {e}")
        raise


def deserialize_json_to_state(json_str: str) -> ExperimentPlanState:
    """Deserialize JSON string to ExperimentPlanState.
    
    Args:
        json_str: JSON string to deserialize
        
    Returns:
        ExperimentPlanState object
    """
    try:
        data = json.loads(json_str)
        return deserialize_dict_to_state(data)
    except Exception as e:
        logger.error(f"Failed to deserialize JSON to state: {e}")
        raise


def get_state_summary(state: ExperimentPlanState) -> Dict[str, Any]:
    """Get a summary of the state for debugging purposes.
    
    Args:
        state: ExperimentPlanState to summarize
        
    Returns:
        State summary dictionary
    """
    try:
        summary = {
            "experiment_id": state.get("experiment_id"),
            "current_stage": state.get("current_stage"),
            "research_query": state.get("research_query", "")[:100] + "..." if len(state.get("research_query", "")) > 100 else state.get("research_query", ""),
            "chat_history_length": len(state.get("chat_history", [])),
            "errors_count": len(state.get("errors", [])),
            "has_objective": bool(state.get("objective")),
            "has_variables": bool(state.get("variables")),
            "has_design": bool(state.get("design")),
            "has_methodology": bool(state.get("methodology")),
            "has_data_plan": bool(state.get("data_plan")),
            "has_review": bool(state.get("review"))
        }
        
        return summary
        
    except Exception as e:
        logger.error(f"Failed to create state summary: {e}")
        return {"error": str(e)}


def validate_serialized_state(serialized_state: Dict[str, Any]) -> bool:
    """Validate that a serialized state contains required fields.
    
    Args:
        serialized_state: Serialized state dictionary
        
    Returns:
        True if valid, False otherwise
    """
    required_fields = [
        "experiment_id",
        "research_query", 
        "current_stage",
        "chat_history",
        "errors"
    ]
    
    for field in required_fields:
        if field not in serialized_state:
            logger.error(f"Missing required field in serialized state: {field}")
            return False
    
    return True 