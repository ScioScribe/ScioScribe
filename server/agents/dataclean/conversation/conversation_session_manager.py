"""
Conversation Session Manager for LangGraph Data Cleaning

This module manages conversation sessions, state persistence, and integration
with existing DataArtifact and MemoryDataStore systems.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
import uuid
from pathlib import Path

from .state_schema import ConversationState, Intent, FileFormat
from ..models import DataArtifact, ProcessingStatus, FileMetadata
from ..memory_store import MemoryDataStore, get_data_store

logger = logging.getLogger(__name__)


class ConversationSessionManager:
    """
    Manages conversation sessions with state persistence and data integration.
    
    This class handles:
    - Session creation and recovery
    - State persistence across conversations
    - Integration with existing DataArtifact system
    - Conversation history management
    - CSV/Excel specific state tracking
    """
    
    def __init__(self, memory_store: Optional[MemoryDataStore] = None):
        """
        Initialize the conversation session manager.
        
        Args:
            memory_store: Optional memory store instance. If None, uses global instance.
        """
        self.memory_store = memory_store or get_data_store()
        self.active_sessions: Dict[str, ConversationState] = {}
        self.session_metadata: Dict[str, Dict[str, Any]] = {}
        
        logger.info("Initialized conversation session manager")
    
    async def create_session(
        self,
        user_id: str,
        session_id: Optional[str] = None,
        artifact_id: Optional[str] = None,
        file_path: Optional[str] = None
    ) -> ConversationState:
        """
        Create a new conversation session.
        
        Args:
            user_id: User identifier
            session_id: Optional session ID. If None, generates new UUID
            artifact_id: Optional existing data artifact ID
            file_path: Optional file path for new data processing
            
        Returns:
            ConversationState: The initialized conversation state
        """
        try:
            # Generate session ID if not provided
            if not session_id:
                session_id = f"session_{uuid.uuid4().hex[:8]}"
            
            logger.info(f"Creating conversation session {session_id} for user {user_id}")
            
            # Load existing artifact if provided
            data_context = None
            dataframe_info = None
            file_format = None
            
            if artifact_id:
                data_context = await self._load_artifact_context(artifact_id)
                dataframe_info = await self._get_dataframe_info(artifact_id)
                
            # Determine file format from path
            if file_path:
                file_format = self._detect_file_format(file_path)
            
            # Create initial conversation state
            initial_state = ConversationState(
                # Session Management
                session_id=session_id,
                user_id=user_id,
                artifact_id=artifact_id,
                
                # File Context (CSV/Excel focused)
                file_format=file_format,
                file_path=file_path,
                sheet_name=None,
                delimiter=None,
                encoding=None,
                
                # Conversation Flow
                user_message="",
                intent=Intent.UNKNOWN,
                response="",
                conversation_history=[],
                extracted_parameters={},
                
                # Data Context
                data_context=data_context,
                current_dataframe=None,
                dataframe_info=dataframe_info,
                
                # Processing State
                pending_operation=None,
                confirmation_required=False,
                operation_result=None,
                last_operation=None,
                
                # Error Handling
                error_message=None,
                error_type=None,
                retry_count=0,
                
                # Response Context
                response_type="info",
                next_steps=None,
                suggestions=None
            )
            
            # Store session
            self.active_sessions[session_id] = initial_state
            self.session_metadata[session_id] = {
                "created_at": datetime.now().isoformat(),
                "user_id": user_id,
                "artifact_id": artifact_id,
                "file_path": file_path,
                "last_activity": datetime.now().isoformat()
            }
            
            logger.info(f"Created conversation session {session_id}")
            return initial_state
            
        except Exception as e:
            logger.error(f"Error creating conversation session: {str(e)}")
            raise
    
    async def get_session(self, session_id: str) -> Optional[ConversationState]:
        """
        Retrieve an existing conversation session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            ConversationState if found, None otherwise
        """
        try:
            session = self.active_sessions.get(session_id)
            if session:
                # Update last activity
                if session_id in self.session_metadata:
                    self.session_metadata[session_id]["last_activity"] = datetime.now().isoformat()
                logger.info(f"Retrieved conversation session {session_id}")
            return session
            
        except Exception as e:
            logger.error(f"Error retrieving conversation session {session_id}: {str(e)}")
            return None
    
    async def update_session(self, session_id: str, state: ConversationState) -> bool:
        """
        Update an existing conversation session.
        
        Args:
            session_id: Session identifier
            state: Updated conversation state
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.active_sessions[session_id] = state
            
            # Update metadata
            if session_id in self.session_metadata:
                self.session_metadata[session_id]["last_activity"] = datetime.now().isoformat()
                
            logger.info(f"Updated conversation session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating conversation session {session_id}: {str(e)}")
            return False
    
    async def link_artifact_to_session(
        self,
        session_id: str,
        artifact_id: str,
        file_path: Optional[str] = None
    ) -> bool:
        """
        Link a data artifact to an existing conversation session.
        
        Args:
            session_id: Session identifier
            artifact_id: Data artifact ID
            file_path: Optional file path
            
        Returns:
            True if successful, False otherwise
        """
        try:
            session = self.active_sessions.get(session_id)
            if not session:
                logger.error(f"Session {session_id} not found")
                return False
            
            # Load artifact context
            data_context = await self._load_artifact_context(artifact_id)
            dataframe_info = await self._get_dataframe_info(artifact_id)
            
            # Determine file format
            file_format = None
            if file_path:
                file_format = self._detect_file_format(file_path)
            
            # Update session state
            updated_state = {
                **session,
                "artifact_id": artifact_id,
                "file_path": file_path,
                "file_format": file_format,
                "data_context": data_context,
                "dataframe_info": dataframe_info
            }
            
            self.active_sessions[session_id] = updated_state
            
            # Update metadata
            if session_id in self.session_metadata:
                self.session_metadata[session_id]["artifact_id"] = artifact_id
                self.session_metadata[session_id]["file_path"] = file_path
                self.session_metadata[session_id]["last_activity"] = datetime.now().isoformat()
            
            logger.info(f"Linked artifact {artifact_id} to session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error linking artifact to session: {str(e)}")
            return False
    
    async def add_conversation_turn(
        self,
        session_id: str,
        user_message: str,
        assistant_response: str,
        intent: Intent,
        response_type: str = "info",
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Add a conversation turn to the session history.
        
        Args:
            session_id: Session identifier
            user_message: User's message
            assistant_response: Assistant's response
            intent: Classified intent
            response_type: Type of response
            metadata: Optional metadata
            
        Returns:
            True if successful, False otherwise
        """
        try:
            session = self.active_sessions.get(session_id)
            if not session:
                logger.error(f"Session {session_id} not found")
                return False
            
            # Add user message
            conversation_history = session.get("conversation_history", [])
            conversation_history.append({
                "timestamp": datetime.now().isoformat(),
                "role": "user",
                "content": user_message,
                "intent": intent.value,
                "metadata": metadata or {}
            })
            
            # Add assistant response
            conversation_history.append({
                "timestamp": datetime.now().isoformat(),
                "role": "assistant",
                "content": assistant_response,
                "type": response_type,
                "metadata": metadata or {}
            })
            
            # Update session
            updated_state = {
                **session,
                "conversation_history": conversation_history,
                "user_message": user_message,
                "response": assistant_response,
                "intent": intent,
                "response_type": response_type
            }
            
            self.active_sessions[session_id] = updated_state
            
            logger.info(f"Added conversation turn to session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding conversation turn: {str(e)}")
            return False
    
    async def update_csv_excel_context(
        self,
        session_id: str,
        delimiter: Optional[str] = None,
        encoding: Optional[str] = None,
        sheet_name: Optional[str] = None
    ) -> bool:
        """
        Update CSV/Excel specific context for a session.
        
        Args:
            session_id: Session identifier
            delimiter: CSV delimiter
            encoding: File encoding
            sheet_name: Excel sheet name
            
        Returns:
            True if successful, False otherwise
        """
        try:
            session = self.active_sessions.get(session_id)
            if not session:
                logger.error(f"Session {session_id} not found")
                return False
            
            # Update CSV/Excel context
            updated_state = {
                **session,
                "delimiter": delimiter if delimiter is not None else session.get("delimiter"),
                "encoding": encoding if encoding is not None else session.get("encoding"),
                "sheet_name": sheet_name if sheet_name is not None else session.get("sheet_name")
            }
            
            self.active_sessions[session_id] = updated_state
            
            logger.info(f"Updated CSV/Excel context for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating CSV/Excel context: {str(e)}")
            return False
    
    async def get_session_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a summary of the conversation session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Dictionary with session summary or None if not found
        """
        try:
            session = self.active_sessions.get(session_id)
            metadata = self.session_metadata.get(session_id)
            
            if not session or not metadata:
                return None
            
            conversation_history = session.get("conversation_history", [])
            
            return {
                "session_id": session_id,
                "user_id": session.get("user_id"),
                "artifact_id": session.get("artifact_id"),
                "file_path": session.get("file_path"),
                "file_format": session.get("file_format"),
                "created_at": metadata.get("created_at"),
                "last_activity": metadata.get("last_activity"),
                "conversation_turns": len(conversation_history),
                "current_intent": session.get("intent"),
                "has_pending_operation": session.get("pending_operation") is not None,
                "confirmation_required": session.get("confirmation_required", False),
                "csv_excel_context": {
                    "delimiter": session.get("delimiter"),
                    "encoding": session.get("encoding"),
                    "sheet_name": session.get("sheet_name")
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting session summary: {str(e)}")
            return None
    
    async def list_user_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """
        List all sessions for a specific user.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of session summaries
        """
        try:
            user_sessions = []
            for session_id, metadata in self.session_metadata.items():
                if metadata.get("user_id") == user_id:
                    summary = await self.get_session_summary(session_id)
                    if summary:
                        user_sessions.append(summary)
            
            return user_sessions
            
        except Exception as e:
            logger.error(f"Error listing user sessions: {str(e)}")
            return []
    
    async def cleanup_inactive_sessions(self, hours_threshold: int = 24) -> int:
        """
        Clean up inactive sessions older than the threshold.
        
        Args:
            hours_threshold: Hours of inactivity before cleanup
            
        Returns:
            Number of sessions cleaned up
        """
        try:
            from datetime import datetime, timedelta
            
            current_time = datetime.now()
            cleanup_count = 0
            sessions_to_remove = []
            
            for session_id, metadata in self.session_metadata.items():
                last_activity = datetime.fromisoformat(metadata["last_activity"])
                if current_time - last_activity > timedelta(hours=hours_threshold):
                    sessions_to_remove.append(session_id)
            
            # Remove inactive sessions
            for session_id in sessions_to_remove:
                self.active_sessions.pop(session_id, None)
                self.session_metadata.pop(session_id, None)
                cleanup_count += 1
            
            logger.info(f"Cleaned up {cleanup_count} inactive sessions")
            return cleanup_count
            
        except Exception as e:
            logger.error(f"Error cleaning up inactive sessions: {str(e)}")
            return 0
    
    # Private helper methods
    
    async def _load_artifact_context(self, artifact_id: str) -> Optional[Dict[str, Any]]:
        """Load data artifact context from memory store."""
        try:
            artifact = await self.memory_store.get_data_artifact(artifact_id)
            if not artifact:
                return None
            
            return {
                "artifact_id": artifact_id,
                "experiment_id": artifact.experiment_id,
                "owner_id": artifact.owner_id,
                "status": artifact.status.value,
                "created_at": artifact.created_at.isoformat(),
                "updated_at": artifact.updated_at.isoformat(),
                "quality_score": artifact.quality_score,
                "suggestions_count": len(artifact.suggestions),
                "transformations_count": len(artifact.custom_transformations),
                "original_file": {
                    "name": artifact.original_file.name,
                    "path": artifact.original_file.path,
                    "size": artifact.original_file.size
                } if artifact.original_file else None
            }
            
        except Exception as e:
            logger.error(f"Error loading artifact context: {str(e)}")
            return None
    
    async def _get_dataframe_info(self, artifact_id: str) -> Optional[Dict[str, Any]]:
        """Get dataframe information from memory store."""
        try:
            dataframe = await self.memory_store.get_dataframe(artifact_id)
            if dataframe is None:
                return None
            
            return {
                "shape": dataframe.shape,
                "columns": dataframe.columns.tolist(),
                "dtypes": dataframe.dtypes.astype(str).to_dict(),
                "null_counts": dataframe.isnull().sum().to_dict(),
                "memory_usage": dataframe.memory_usage(deep=True).sum()
            }
            
        except Exception as e:
            logger.error(f"Error getting dataframe info: {str(e)}")
            return None
    
    def _detect_file_format(self, file_path: str) -> Optional[FileFormat]:
        """Detect file format from file path."""
        try:
            path = Path(file_path)
            suffix = path.suffix.lower()
            
            if suffix == '.csv':
                return FileFormat.CSV
            elif suffix in ['.xlsx', '.xls']:
                return FileFormat.EXCEL
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error detecting file format: {str(e)}")
            return None 