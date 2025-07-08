"""
State serialization and deserialization utilities for the experiment planning agent system.

This module provides functions to convert ExperimentPlanState objects to and from
various formats (JSON, Firestore documents) while handling datetime serialization
and maintaining data integrity through validation.
"""

from typing import Dict, Any, Optional
from datetime import datetime
import json
import logging
from copy import deepcopy

from .state import ExperimentPlanState
from .validation import validate_experiment_plan_state, StateValidationError
from .factory import create_default_state

logger = logging.getLogger(__name__)


class SerializationError(Exception):
    """Exception raised for serialization/deserialization errors.
    
    Args:
        message: Error description
        operation: The operation that failed (serialize/deserialize)
        data_type: The data type being processed
        context: Additional error context
    """
    
    def __init__(
        self,
        message: str,
        operation: str = None,
        data_type: str = None,
        context: Dict[str, Any] = None
    ) -> None:
        self.message = message
        self.operation = operation
        self.data_type = data_type
        self.context = context or {}
        super().__init__(self.message)


def datetime_to_iso_string(dt: datetime) -> str:
    """Convert datetime to ISO string format.
    
    Args:
        dt: Datetime object to convert
        
    Returns:
        ISO formatted string
    """
    return dt.isoformat() + 'Z' if dt.tzinfo is None else dt.isoformat()


def iso_string_to_datetime(iso_string: str) -> datetime:
    """Convert ISO string to datetime object.
    
    Args:
        iso_string: ISO formatted datetime string
        
    Returns:
        Datetime object
        
    Raises:
        SerializationError: If string format is invalid
    """
    try:
        # Handle Z suffix for UTC timezone
        if iso_string.endswith('Z'):
            iso_string = iso_string[:-1] + '+00:00'
        
        return datetime.fromisoformat(iso_string)
    except ValueError as e:
        raise SerializationError(
            f"Invalid ISO datetime format: {iso_string}",
            operation="deserialize",
            data_type="datetime",
            context={"original_error": str(e)}
        )


def serialize_state_to_dict(state: ExperimentPlanState) -> Dict[str, Any]:
    """
    Serialize ExperimentPlanState to a dictionary with datetime handling.
    
    Args:
        state: The state object to serialize
        
    Returns:
        Dictionary representation with serialized datetime objects
        
    Raises:
        SerializationError: If serialization fails
    """
    try:
        # Validate state before serialization
        validate_experiment_plan_state(state)
        
        # Deep copy to avoid modifying original state
        serialized = deepcopy(dict(state))
        
        # Convert datetime objects to ISO strings
        serialized['created_at'] = datetime_to_iso_string(state['created_at'])
        serialized['updated_at'] = datetime_to_iso_string(state['updated_at'])
        
        # Handle chat history timestamps
        for message in serialized['chat_history']:
            if 'timestamp' in message and isinstance(message['timestamp'], datetime):
                message['timestamp'] = datetime_to_iso_string(message['timestamp'])
        
        return serialized
        
    except StateValidationError as e:
        raise SerializationError(
            f"State validation failed during serialization: {e.message}",
            operation="serialize",
            data_type="ExperimentPlanState",
            context={"validation_error": str(e)}
        )
    except Exception as e:
        raise SerializationError(
            f"Unexpected error during serialization: {str(e)}",
            operation="serialize",
            data_type="ExperimentPlanState",
            context={"error_type": type(e).__name__}
        )


def deserialize_dict_to_state(data: Dict[str, Any]) -> ExperimentPlanState:
    """
    Deserialize dictionary to ExperimentPlanState with datetime handling.
    
    Args:
        data: Dictionary to deserialize
        
    Returns:
        ExperimentPlanState object
        
    Raises:
        SerializationError: If deserialization fails
    """
    try:
        # Deep copy to avoid modifying original data
        deserialized = deepcopy(data)
        
        # Convert ISO strings back to datetime objects
        if 'created_at' in deserialized:
            deserialized['created_at'] = iso_string_to_datetime(deserialized['created_at'])
        
        if 'updated_at' in deserialized:
            deserialized['updated_at'] = iso_string_to_datetime(deserialized['updated_at'])
        
        # Handle chat history timestamps
        for message in deserialized.get('chat_history', []):
            if 'timestamp' in message and isinstance(message['timestamp'], str):
                message['timestamp'] = iso_string_to_datetime(message['timestamp'])
        
        # Validate deserialized state
        validate_experiment_plan_state(deserialized)
        
        return ExperimentPlanState(deserialized)
        
    except SerializationError:
        raise  # Re-raise serialization errors
    except StateValidationError as e:
        raise SerializationError(
            f"State validation failed during deserialization: {e.message}",
            operation="deserialize",
            data_type="ExperimentPlanState",
            context={"validation_error": str(e)}
        )
    except Exception as e:
        raise SerializationError(
            f"Unexpected error during deserialization: {str(e)}",
            operation="deserialize",
            data_type="ExperimentPlanState",
            context={"error_type": type(e).__name__}
        )


def serialize_state_to_json(state: ExperimentPlanState, indent: Optional[int] = None) -> str:
    """
    Serialize ExperimentPlanState to JSON string.
    
    Args:
        state: The state object to serialize
        indent: JSON indentation level (None for compact format)
        
    Returns:
        JSON string representation
        
    Raises:
        SerializationError: If serialization fails
    """
    try:
        serialized_dict = serialize_state_to_dict(state)
        return json.dumps(serialized_dict, indent=indent, ensure_ascii=False)
        
    except SerializationError:
        raise  # Re-raise serialization errors
    except Exception as e:
        raise SerializationError(
            f"JSON serialization failed: {str(e)}",
            operation="serialize",
            data_type="JSON",
            context={"error_type": type(e).__name__}
        )


def deserialize_json_to_state(json_string: str) -> ExperimentPlanState:
    """
    Deserialize JSON string to ExperimentPlanState.
    
    Args:
        json_string: JSON string to deserialize
        
    Returns:
        ExperimentPlanState object
        
    Raises:
        SerializationError: If deserialization fails
    """
    try:
        data = json.loads(json_string)
        return deserialize_dict_to_state(data)
        
    except json.JSONDecodeError as e:
        raise SerializationError(
            f"Invalid JSON format: {str(e)}",
            operation="deserialize",
            data_type="JSON",
            context={"json_error": str(e)}
        )
    except SerializationError:
        raise  # Re-raise serialization errors


def serialize_state_to_firestore(state: ExperimentPlanState) -> Dict[str, Any]:
    """
    Serialize ExperimentPlanState for Firestore storage.
    
    Firestore has specific requirements for datetime objects and field names.
    
    Args:
        state: The state object to serialize
        
    Returns:
        Dictionary formatted for Firestore storage
        
    Raises:
        SerializationError: If serialization fails
    """
    try:
        # Use the standard serialization but keep datetimes as datetime objects
        # since Firestore handles them natively
        serialized = serialize_state_to_dict(state)
        
        # Convert ISO strings back to datetime objects for Firestore
        serialized['created_at'] = state['created_at']
        serialized['updated_at'] = state['updated_at']
        
        # Handle chat history timestamps for Firestore
        for message in serialized['chat_history']:
            if 'timestamp' in message:
                # Find corresponding original message for datetime
                original_message = next(
                    (msg for msg in state['chat_history'] 
                     if msg.get('content') == message.get('content')),
                    None
                )
                if original_message and 'timestamp' in original_message:
                    message['timestamp'] = original_message['timestamp']
        
        return serialized
        
    except Exception as e:
        raise SerializationError(
            f"Firestore serialization failed: {str(e)}",
            operation="serialize",
            data_type="Firestore",
            context={"error_type": type(e).__name__}
        )


def deserialize_firestore_to_state(firestore_data: Dict[str, Any]) -> ExperimentPlanState:
    """
    Deserialize Firestore document to ExperimentPlanState.
    
    Args:
        firestore_data: Firestore document data
        
    Returns:
        ExperimentPlanState object
        
    Raises:
        SerializationError: If deserialization fails
    """
    try:
        # Firestore returns datetime objects directly, so we can use them as-is
        # Just need to validate the structure
        validate_experiment_plan_state(firestore_data)
        
        return ExperimentPlanState(firestore_data)
        
    except StateValidationError as e:
        raise SerializationError(
            f"Firestore data validation failed: {e.message}",
            operation="deserialize",
            data_type="Firestore",
            context={"validation_error": str(e)}
        )
    except Exception as e:
        raise SerializationError(
            f"Firestore deserialization failed: {str(e)}",
            operation="deserialize",
            data_type="Firestore",
            context={"error_type": type(e).__name__}
        )


def create_state_backup(state: ExperimentPlanState) -> str:
    """
    Create a backup of the state as a JSON string.
    
    Args:
        state: The state to backup
        
    Returns:
        JSON string backup
    """
    try:
        return serialize_state_to_json(state, indent=2)
    except Exception as e:
        logger.error(f"Failed to create state backup: {str(e)}")
        raise SerializationError(
            f"Backup creation failed: {str(e)}",
            operation="backup",
            data_type="ExperimentPlanState"
        )


def restore_state_from_backup(backup_json: str) -> ExperimentPlanState:
    """
    Restore state from a JSON backup.
    
    Args:
        backup_json: JSON backup string
        
    Returns:
        Restored ExperimentPlanState object
    """
    try:
        return deserialize_json_to_state(backup_json)
    except Exception as e:
        logger.error(f"Failed to restore state from backup: {str(e)}")
        raise SerializationError(
            f"Backup restoration failed: {str(e)}",
            operation="restore",
            data_type="ExperimentPlanState"
        ) 