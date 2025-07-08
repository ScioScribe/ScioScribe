"""
Memory Data Store for ScioScribe Data Cleaning System.

This module provides in-memory storage for data artifacts, transformation rules,
and data versions. It serves as a lightweight, no-dependency storage solution.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
import pandas as pd

from .models import (
    DataArtifact,
    TransformationRule,
    CustomTransformation,
    DataVersion,
    TransformationHistory,
    ProcessingStatus
)

logger = logging.getLogger(__name__)


class MemoryDataStore:
    """
    In-memory data store for storage of data artifacts, transformation rules,
    and data versions using Python dictionaries.
    """
    
    def __init__(self):
        """Initialize in-memory data store."""
        self.memory_artifacts: Dict[str, DataArtifact] = {}
        self.memory_rules: Dict[str, TransformationRule] = {}
        self.memory_versions: Dict[str, List[pd.DataFrame]] = {}
        self.memory_dataframes: Dict[str, pd.DataFrame] = {}
        
        logger.info("Initialized in-memory data store")
    
    # === Data Artifact Operations ===
    
    async def save_data_artifact(self, artifact: DataArtifact) -> bool:
        """
        Save a data artifact to memory.
        
        Args:
            artifact: The data artifact to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.memory_artifacts[artifact.artifact_id] = artifact
            logger.info(f"Saved artifact {artifact.artifact_id} to memory")
            return True
            
        except Exception as e:
            logger.error(f"Error saving artifact {artifact.artifact_id}: {str(e)}")
            return False
    
    async def get_data_artifact(self, artifact_id: str) -> Optional[DataArtifact]:
        """
        Retrieve a data artifact from memory.
        
        Args:
            artifact_id: ID of the artifact to retrieve
            
        Returns:
            DataArtifact if found, None otherwise
        """
        try:
            return self.memory_artifacts.get(artifact_id)
            
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
            artifacts = list(self.memory_artifacts.values())
            if experiment_id:
                artifacts = [a for a in artifacts if a.experiment_id == experiment_id]
            return artifacts
            
        except Exception as e:
            logger.error(f"Error listing artifacts: {str(e)}")
            return []
    
    # === DataFrame Operations ===
    
    async def save_dataframe(self, artifact_id: str, dataframe: pd.DataFrame) -> bool:
        """
        Save a DataFrame to memory.
        
        Args:
            artifact_id: ID of the artifact
            dataframe: The DataFrame to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.memory_dataframes[artifact_id] = dataframe.copy()
            logger.info(f"Saved DataFrame for artifact {artifact_id} to memory")
            return True
            
        except Exception as e:
            logger.error(f"Error saving DataFrame for artifact {artifact_id}: {str(e)}")
            return False
    
    async def get_dataframe(self, artifact_id: str) -> Optional[pd.DataFrame]:
        """
        Retrieve a DataFrame from memory.
        
        Args:
            artifact_id: ID of the artifact
            
        Returns:
            DataFrame if found, None otherwise
        """
        try:
            return self.memory_dataframes.get(artifact_id)
            
        except Exception as e:
            logger.error(f"Error retrieving DataFrame for artifact {artifact_id}: {str(e)}")
            return None
    
    # === Transformation Rules Operations ===
    
    async def save_transformation_rule(self, rule: TransformationRule) -> bool:
        """
        Save a transformation rule to memory.
        
        Args:
            rule: The transformation rule to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.memory_rules[rule.rule_id] = rule
            logger.info(f"Saved transformation rule {rule.rule_id} to memory")
            return True
            
        except Exception as e:
            logger.error(f"Error saving transformation rule {rule.rule_id}: {str(e)}")
            return False
    
    async def get_transformation_rule(self, rule_id: str) -> Optional[TransformationRule]:
        """
        Retrieve a transformation rule from memory.
        
        Args:
            rule_id: ID of the rule to retrieve
            
        Returns:
            TransformationRule if found, None otherwise
        """
        try:
            return self.memory_rules.get(rule_id)
            
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
            rules = list(self.memory_rules.values())
            # Simple pattern matching for in-memory storage
            matching_rules = []
            for rule in rules:
                if (rule.created_by == user_id and 
                    (pattern.lower() in rule.name.lower() or 
                     pattern.lower() in rule.column_pattern.lower())):
                    matching_rules.append(rule)
            return matching_rules
            
        except Exception as e:
            logger.error(f"Error searching transformation rules: {str(e)}")
            return []
    
    # === Data Version Operations ===
    
    async def save_data_version(self, artifact_id: str, version: int, dataframe: pd.DataFrame) -> bool:
        """
        Save a data version to memory.
        
        Args:
            artifact_id: ID of the artifact
            version: Version number
            dataframe: The DataFrame to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if artifact_id not in self.memory_versions:
                self.memory_versions[artifact_id] = []
            
            # Ensure we have enough space for the version
            while len(self.memory_versions[artifact_id]) <= version:
                self.memory_versions[artifact_id].append(pd.DataFrame())
            
            self.memory_versions[artifact_id][version] = dataframe.copy()
            logger.info(f"Saved data version {version} for artifact {artifact_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving data version {version} for artifact {artifact_id}: {str(e)}")
            return False
    
    async def get_data_version(self, artifact_id: str, version: int) -> Optional[pd.DataFrame]:
        """
        Retrieve a specific data version from memory.
        
        Args:
            artifact_id: ID of the artifact
            version: Version number
            
        Returns:
            DataFrame if found, None otherwise
        """
        try:
            if artifact_id not in self.memory_versions:
                return None
            
            if version < 0 or version >= len(self.memory_versions[artifact_id]):
                return None
            
            return self.memory_versions[artifact_id][version].copy()
            
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
            # Clean up memory storage
            self.memory_artifacts.pop(artifact_id, None)
            self.memory_dataframes.pop(artifact_id, None)
            self.memory_versions.pop(artifact_id, None)
            
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
            return {
                "storage_type": "in_memory",
                "artifacts_count": len(self.memory_artifacts),
                "dataframes_count": len(self.memory_dataframes),
                "rules_count": len(self.memory_rules),
                "versions_count": sum(len(versions) for versions in self.memory_versions.values())
            }
            
        except Exception as e:
            logger.error(f"Error getting storage stats: {str(e)}")
            return {"error": str(e)}


# Global instance
_data_store = None


def get_data_store() -> MemoryDataStore:
    """Get the global data store instance."""
    global _data_store
    if _data_store is None:
        _data_store = MemoryDataStore()
    return _data_store 