
"""
Firebase Data Store for ScioScribe Data Cleaning System.

This module provides persistent storage using Firebase Firestore and Storage
to replace the in-memory storage used during development.
"""

import json
import pickle
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd
from google.cloud import firestore
from google.cloud import storage
import uuid

from .models import (
    DataArtifact,
    TransformationRule,
    CustomTransformation,
    DataVersion,
    TransformationHistory,
    ProcessingStatus
)
from config import get_firestore_client, get_storage_client

logger = logging.getLogger(__name__)


class FirebaseDataStore:
    """
    Firebase-based data store for persistent storage of data artifacts,
    transformation rules, and data versions.
    """
    
    def __init__(self):
        """Initialize Firebase data store."""
        self.firestore_client = get_firestore_client()
        self.storage_client = get_storage_client()
        
        # Collection names
        self.ARTIFACTS_COLLECTION = "data_artifacts"
        self.RULES_COLLECTION = "transformation_rules"
        self.VERSIONS_COLLECTION = "data_versions"
        self.DATAFRAMES_COLLECTION = "dataframes"
        
        # Storage bucket paths
        self.DATAFRAMES_PATH = "dataframes"
        self.PROCESSED_FILES_PATH = "processed_files"
        
        # Fallback to in-memory storage if Firebase not configured
        self.use_firebase = self.firestore_client is not None and self.storage_client is not None
        
        if not self.use_firebase:
            logger.warning("Firebase not configured. Using in-memory storage.")
            self._init_memory_storage()
    
    def _init_memory_storage(self):
        """Initialize in-memory storage as fallback."""
        self.memory_artifacts: Dict[str, DataArtifact] = {}
        self.memory_rules: Dict[str, TransformationRule] = {}
        self.memory_versions: Dict[str, List[pd.DataFrame]] = {}
        self.memory_dataframes: Dict[str, pd.DataFrame] = {}
    
    # === Data Artifact Operations ===
    
    async def save_data_artifact(self, artifact: DataArtifact) -> bool:
        """
        Save a data artifact to Firestore.
        
        Args:
            artifact: The data artifact to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.use_firebase:
                self.memory_artifacts[artifact.artifact_id] = artifact
                return True
            
            # Convert artifact to dictionary for Firestore
            artifact_dict = artifact.dict()
            
            # Handle datetime serialization
            artifact_dict['created_at'] = artifact.created_at
            artifact_dict['updated_at'] = artifact.updated_at
            
            # Save to Firestore
            doc_ref = self.firestore_client.collection(self.ARTIFACTS_COLLECTION).document(artifact.artifact_id)
            doc_ref.set(artifact_dict)
            
            logger.info(f"Saved artifact {artifact.artifact_id} to Firestore")
            return True
            
        except Exception as e:
            logger.error(f"Error saving artifact {artifact.artifact_id}: {str(e)}")
            return False
    
    async def get_data_artifact(self, artifact_id: str) -> Optional[DataArtifact]:
        """
        Retrieve a data artifact from Firestore.
        
        Args:
            artifact_id: ID of the artifact to retrieve
            
        Returns:
            DataArtifact if found, None otherwise
        """
        try:
            if not self.use_firebase:
                return self.memory_artifacts.get(artifact_id)
            
            doc_ref = self.firestore_client.collection(self.ARTIFACTS_COLLECTION).document(artifact_id)
            doc = doc_ref.get()
            
            if doc.exists:
                data = doc.to_dict()
                return DataArtifact(**data)
            
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving artifact {artifact_id}: {str(e)}")
            return None
    
    async def update_data_artifact(self, artifact: DataArtifact) -> bool:
        """
        Update an existing data artifact.
        
        Args:
            artifact: The updated artifact
            
        Returns:
            True if successful, False otherwise
        """
        artifact.updated_at = datetime.now()
        return await self.save_data_artifact(artifact)
    
    async def list_data_artifacts(self, experiment_id: Optional[str] = None) -> List[DataArtifact]:
        """
        List all data artifacts, optionally filtered by experiment.
        
        Args:
            experiment_id: Optional experiment ID to filter by
            
        Returns:
            List of data artifacts
        """
        try:
            if not self.use_firebase:
                artifacts = list(self.memory_artifacts.values())
                if experiment_id:
                    artifacts = [a for a in artifacts if a.experiment_id == experiment_id]
                return artifacts
            
            query = self.firestore_client.collection(self.ARTIFACTS_COLLECTION)
            if experiment_id:
                query = query.where('experiment_id', '==', experiment_id)
            
            docs = query.stream()
            artifacts = []
            
            for doc in docs:
                data = doc.to_dict()
                artifacts.append(DataArtifact(**data))
            
            return artifacts
            
        except Exception as e:
            logger.error(f"Error listing artifacts: {str(e)}")
            return []
    
    # === DataFrame Operations ===
    
    async def save_dataframe(self, artifact_id: str, dataframe: pd.DataFrame) -> bool:
        """
        Save a DataFrame to Firebase Storage.
        
        Args:
            artifact_id: ID of the artifact
            dataframe: The DataFrame to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.use_firebase:
                self.memory_dataframes[artifact_id] = dataframe.copy()
                return True
            
            # Convert DataFrame to pickle for efficient storage
            df_pickle = pickle.dumps(dataframe)
            
            # Upload to Firebase Storage
            blob_name = f"{self.DATAFRAMES_PATH}/{artifact_id}.pkl"
            blob = self.storage_client.blob(blob_name)
            blob.upload_from_string(df_pickle)
            
            logger.info(f"Saved DataFrame for artifact {artifact_id} to Storage")
            return True
            
        except Exception as e:
            logger.error(f"Error saving DataFrame for artifact {artifact_id}: {str(e)}")
            return False
    
    async def get_dataframe(self, artifact_id: str) -> Optional[pd.DataFrame]:
        """
        Retrieve a DataFrame from Firebase Storage.
        
        Args:
            artifact_id: ID of the artifact
            
        Returns:
            DataFrame if found, None otherwise
        """
        try:
            if not self.use_firebase:
                return self.memory_dataframes.get(artifact_id)
            
            blob_name = f"{self.DATAFRAMES_PATH}/{artifact_id}.pkl"
            blob = self.storage_client.blob(blob_name)
            
            if not blob.exists():
                return None
            
            # Download and deserialize DataFrame
            df_pickle = blob.download_as_bytes()
            dataframe = pickle.loads(df_pickle)
            
            return dataframe
            
        except Exception as e:
            logger.error(f"Error retrieving DataFrame for artifact {artifact_id}: {str(e)}")
            return None
    
    # === Transformation Rules Operations ===
    
    async def save_transformation_rule(self, rule: TransformationRule) -> bool:
        """
        Save a transformation rule to Firestore.
        
        Args:
            rule: The transformation rule to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.use_firebase:
                self.memory_rules[rule.rule_id] = rule
                return True
            
            # Convert rule to dictionary
            rule_dict = rule.dict()
            rule_dict['created_at'] = rule.created_at
            
            # Save to Firestore
            doc_ref = self.firestore_client.collection(self.RULES_COLLECTION).document(rule.rule_id)
            doc_ref.set(rule_dict)
            
            logger.info(f"Saved transformation rule {rule.rule_id} to Firestore")
            return True
            
        except Exception as e:
            logger.error(f"Error saving transformation rule {rule.rule_id}: {str(e)}")
            return False
    
    async def get_transformation_rule(self, rule_id: str) -> Optional[TransformationRule]:
        """
        Retrieve a transformation rule from Firestore.
        
        Args:
            rule_id: ID of the rule to retrieve
            
        Returns:
            TransformationRule if found, None otherwise
        """
        try:
            if not self.use_firebase:
                return self.memory_rules.get(rule_id)
            
            doc_ref = self.firestore_client.collection(self.RULES_COLLECTION).document(rule_id)
            doc = doc_ref.get()
            
            if doc.exists:
                data = doc.to_dict()
                return TransformationRule(**data)
            
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving transformation rule {rule_id}: {str(e)}")
            return None
    
    async def search_transformation_rules(self, pattern: str, user_id: str) -> List[TransformationRule]:
        """
        Search for transformation rules by pattern.
        
        Args:
            pattern: Pattern to search for
            user_id: User ID to filter by
            
        Returns:
            List of matching transformation rules
        """
        try:
            if not self.use_firebase:
                rules = list(self.memory_rules.values())
                # Simple pattern matching for in-memory storage
                matching_rules = []
                for rule in rules:
                    if (rule.created_by == user_id and 
                        (pattern.lower() in rule.name.lower() or 
                         pattern.lower() in rule.column_pattern.lower())):
                        matching_rules.append(rule)
                return matching_rules
            
            # For Firebase, we'll do a simple query and filter in memory
            # In production, you might want to use full-text search
            query = self.firestore_client.collection(self.RULES_COLLECTION).where('created_by', '==', user_id)
            docs = query.stream()
            
            matching_rules = []
            for doc in docs:
                data = doc.to_dict()
                rule = TransformationRule(**data)
                if (pattern.lower() in rule.name.lower() or 
                    pattern.lower() in rule.column_pattern.lower()):
                    matching_rules.append(rule)
            
            return matching_rules
            
        except Exception as e:
            logger.error(f"Error searching transformation rules: {str(e)}")
            return []
    
    # === Data Version Operations ===
    
    async def save_data_version(self, artifact_id: str, version: int, dataframe: pd.DataFrame) -> bool:
        """
        Save a data version to Firebase Storage.
        
        Args:
            artifact_id: ID of the artifact
            version: Version number
            dataframe: The DataFrame to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.use_firebase:
                if artifact_id not in self.memory_versions:
                    self.memory_versions[artifact_id] = []
                
                # Ensure we have enough space for the version
                while len(self.memory_versions[artifact_id]) <= version:
                    self.memory_versions[artifact_id].append(pd.DataFrame())
                
                self.memory_versions[artifact_id][version] = dataframe.copy()
                return True
            
            # Convert DataFrame to pickle
            df_pickle = pickle.dumps(dataframe)
            
            # Upload to Firebase Storage
            blob_name = f"{self.DATAFRAMES_PATH}/versions/{artifact_id}_v{version}.pkl"
            blob = self.storage_client.blob(blob_name)
            blob.upload_from_string(df_pickle)
            
            logger.info(f"Saved data version {version} for artifact {artifact_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving data version {version} for artifact {artifact_id}: {str(e)}")
            return False
    
    async def get_data_version(self, artifact_id: str, version: int) -> Optional[pd.DataFrame]:
        """
        Retrieve a specific data version from Firebase Storage.
        
        Args:
            artifact_id: ID of the artifact
            version: Version number
            
        Returns:
            DataFrame if found, None otherwise
        """
        try:
            if not self.use_firebase:
                if artifact_id not in self.memory_versions:
                    return None
                
                if version < 0 or version >= len(self.memory_versions[artifact_id]):
                    return None
                
                return self.memory_versions[artifact_id][version].copy()
            
            blob_name = f"{self.DATAFRAMES_PATH}/versions/{artifact_id}_v{version}.pkl"
            blob = self.storage_client.blob(blob_name)
            
            if not blob.exists():
                return None
            
            # Download and deserialize DataFrame
            df_pickle = blob.download_as_bytes()
            dataframe = pickle.loads(df_pickle)
            
            return dataframe
            
        except Exception as e:
            logger.error(f"Error retrieving data version {version} for artifact {artifact_id}: {str(e)}")
            return None
    
    # === Utility Methods ===
    
    async def delete_data_artifact(self, artifact_id: str) -> bool:
        """
        Delete a data artifact and all associated data.
        
        Args:
            artifact_id: ID of the artifact to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.use_firebase:
                # Clean up memory storage
                self.memory_artifacts.pop(artifact_id, None)
                self.memory_dataframes.pop(artifact_id, None)
                self.memory_versions.pop(artifact_id, None)
                return True
            
            # Delete from Firestore
            doc_ref = self.firestore_client.collection(self.ARTIFACTS_COLLECTION).document(artifact_id)
            doc_ref.delete()
            
            # Delete associated files from Storage
            blobs_to_delete = [
                f"{self.DATAFRAMES_PATH}/{artifact_id}.pkl",
            ]
            
            # Delete version files
            for blob in self.storage_client.list_blobs(prefix=f"{self.DATAFRAMES_PATH}/versions/{artifact_id}_v"):
                blobs_to_delete.append(blob.name)
            
            for blob_name in blobs_to_delete:
                blob = self.storage_client.blob(blob_name)
                if blob.exists():
                    blob.delete()
            
            logger.info(f"Deleted artifact {artifact_id} and associated data")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting artifact {artifact_id}: {str(e)}")
            return False
    
    async def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get storage statistics.
        
        Returns:
            Dictionary with storage statistics
        """
        try:
            if not self.use_firebase:
                return {
                    "storage_type": "in_memory",
                    "artifacts_count": len(self.memory_artifacts),
                    "dataframes_count": len(self.memory_dataframes),
                    "rules_count": len(self.memory_rules),
                    "versions_count": sum(len(versions) for versions in self.memory_versions.values())
                }
            
            # Get Firestore collection counts
            artifacts_count = len(list(self.firestore_client.collection(self.ARTIFACTS_COLLECTION).stream()))
            rules_count = len(list(self.firestore_client.collection(self.RULES_COLLECTION).stream()))
            
            # Get Storage blob counts
            dataframes_count = len(list(self.storage_client.list_blobs(prefix=f"{self.DATAFRAMES_PATH}/")))
            
            return {
                "storage_type": "firebase",
                "artifacts_count": artifacts_count,
                "rules_count": rules_count,
                "dataframes_count": dataframes_count,
                "firestore_project": self.firestore_client.project,
                "storage_bucket": self.storage_client.name
            }
            
        except Exception as e:
            logger.error(f"Error getting storage stats: {str(e)}")
            return {"error": str(e)}


# Global instance
_data_store = None


def get_data_store() -> FirebaseDataStore:
    """Get the global data store instance."""
    global _data_store
    if _data_store is None:
        _data_store = FirebaseDataStore()
    return _data_store 