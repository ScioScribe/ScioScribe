"""
Transformation Engine for Phase 2.5 Interactive Data Transformations.

This module provides the core logic for applying custom transformations,
generating previews, and managing transformation rules.
"""

import uuid
import hashlib
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import logging
import copy
import re

from .models import (
    CustomTransformation,
    TransformationPreview,
    TransformationRule,
    DataVersion,
    TransformationHistory,
    ValueMapping,
    TransformationAction
)

logger = logging.getLogger(__name__)


class TransformationEngine:
    """
    Engine responsible for applying custom data transformations and managing
    transformation history for undo/redo functionality.
    """
    
    def __init__(self):
        """Initialize the transformation engine."""
        # In-memory storage for transformation rules (replace with database later)
        self.transformation_rules: Dict[str, TransformationRule] = {}
        
        # Storage for data versions (replace with persistent storage later)
        self.data_versions: Dict[str, List[pd.DataFrame]] = {}
        
    async def create_transformation_preview(
        self,
        df: pd.DataFrame,
        transformation: CustomTransformation
    ) -> TransformationPreview:
        """
        Generate a preview of how a transformation will affect the data.
        
        Args:
            df: Original DataFrame
            transformation: Transformation to preview
            
        Returns:
            TransformationPreview showing the impact
        """
        try:
            logger.info(f"Creating preview for transformation: {transformation.transformation_id}")
            
            # Create a copy for preview
            preview_df = df.copy()
            
            # Apply transformation to the copy
            transformed_df = await self._apply_transformation_to_dataframe(
                preview_df, transformation
            )
            
            # Calculate impact
            total_rows = len(df)
            affected_rows = self._count_affected_rows(df, transformation)
            
            # Get sample data (before and after)
            sample_size = min(10, total_rows)
            before_sample = df.head(sample_size).to_dict('records')
            after_sample = transformed_df.head(sample_size).to_dict('records')
            
            # Generate impact summary
            impact_summary = self._generate_impact_summary(
                df, transformed_df, transformation
            )
            
            preview = TransformationPreview(
                transformation_id=transformation.transformation_id,
                column=transformation.column,
                total_rows=total_rows,
                affected_rows=affected_rows,
                before_sample=before_sample,
                after_sample=after_sample,
                impact_summary=impact_summary
            )
            
            logger.info(f"Preview created: {affected_rows}/{total_rows} rows affected")
            return preview
            
        except Exception as e:
            logger.error(f"Error creating transformation preview: {str(e)}")
            raise
    
    async def apply_transformation(
        self,
        df: pd.DataFrame,
        transformation: CustomTransformation,
        artifact_id: str,
        user_id: str
    ) -> Tuple[pd.DataFrame, DataVersion]:
        """
        Apply a transformation to the DataFrame and create a version history entry.
        
        Args:
            df: Original DataFrame
            transformation: Transformation to apply
            artifact_id: ID of the data artifact
            user_id: ID of the user applying the transformation
            
        Returns:
            Tuple of (transformed_df, data_version)
        """
        try:
            logger.info(f"Applying transformation: {transformation.transformation_id}")
            
            # Create version history entry
            version_id = str(uuid.uuid4())
            current_version = self._get_next_version_number(artifact_id)
            
            # Store the current state before transformation
            self._store_version(artifact_id, df, current_version - 1)
            
            # Apply transformation
            transformed_df = await self._apply_transformation_to_dataframe(
                df.copy(), transformation
            )
            
            # Create version record
            data_version = DataVersion(
                version_id=version_id,
                artifact_id=artifact_id,
                version_number=current_version,
                description=f"Applied: {transformation.description}",
                transformations_applied=[transformation.transformation_id],
                data_hash=self._calculate_data_hash(transformed_df),
                created_at=datetime.now(),
                created_by=user_id
            )
            
            # Store the new version
            self._store_version(artifact_id, transformed_df, current_version)
            
            logger.info(f"Transformation applied successfully. New version: {current_version}")
            return transformed_df, data_version
            
        except Exception as e:
            logger.error(f"Error applying transformation: {str(e)}")
            raise
    
    async def _apply_transformation_to_dataframe(
        self,
        df: pd.DataFrame,
        transformation: CustomTransformation
    ) -> pd.DataFrame:
        """
        Apply a specific transformation to a DataFrame.
        
        Args:
            df: DataFrame to transform
            transformation: Transformation to apply
            
        Returns:
            Transformed DataFrame
        """
        column = transformation.column
        
        if column not in df.columns:
            raise ValueError(f"Column '{column}' not found in DataFrame")
        
        if transformation.action == TransformationAction.REPLACE_VALUES:
            return self._apply_value_replacement(df, transformation)
        elif transformation.action == TransformationAction.CONVERT_TYPE:
            return self._apply_type_conversion(df, transformation)
        elif transformation.action == TransformationAction.FILL_MISSING:
            return self._apply_missing_value_fill(df, transformation)
        elif transformation.action == TransformationAction.REMOVE_OUTLIERS:
            return self._apply_outlier_removal(df, transformation)
        elif transformation.action == TransformationAction.STANDARDIZE_FORMAT:
            return self._apply_format_standardization(df, transformation)
        else:
            raise ValueError(f"Unknown transformation action: {transformation.action}")
    
    def _apply_value_replacement(
        self,
        df: pd.DataFrame,
        transformation: CustomTransformation
    ) -> pd.DataFrame:
        """Apply value replacement transformation."""
        column = transformation.column
        
        for mapping in transformation.value_mappings:
            # Handle different types of original values
            if pd.isna(mapping.original_value):
                # Replace NaN values
                df[column] = df[column].fillna(mapping.new_value)
            else:
                # Replace specific values
                df[column] = df[column].replace(mapping.original_value, mapping.new_value)
        
        return df
    
    def _apply_type_conversion(
        self,
        df: pd.DataFrame,
        transformation: CustomTransformation
    ) -> pd.DataFrame:
        """Apply data type conversion transformation."""
        column = transformation.column
        target_type = transformation.parameters.get('target_type', 'str')
        
        try:
            if target_type == 'int':
                df[column] = pd.to_numeric(df[column], errors='coerce').astype('Int64')
            elif target_type == 'float':
                df[column] = pd.to_numeric(df[column], errors='coerce')
            elif target_type == 'datetime':
                df[column] = pd.to_datetime(df[column], errors='coerce')
            elif target_type == 'str':
                df[column] = df[column].astype(str)
            elif target_type == 'bool':
                df[column] = df[column].astype(bool)
            
        except Exception as e:
            logger.warning(f"Type conversion failed: {str(e)}")
            # Keep original values if conversion fails
            
        return df
    
    def _apply_missing_value_fill(
        self,
        df: pd.DataFrame,
        transformation: CustomTransformation
    ) -> pd.DataFrame:
        """Apply missing value filling transformation."""
        column = transformation.column
        fill_strategy = transformation.parameters.get('strategy', 'value')
        
        if fill_strategy == 'value':
            fill_value = transformation.parameters.get('fill_value', 'Unknown')
            df[column] = df[column].fillna(fill_value)
        elif fill_strategy == 'mean':
            df[column] = df[column].fillna(df[column].mean())
        elif fill_strategy == 'median':
            df[column] = df[column].fillna(df[column].median())
        elif fill_strategy == 'mode':
            mode_value = df[column].mode().iloc[0] if not df[column].mode().empty else 'Unknown'
            df[column] = df[column].fillna(mode_value)
        elif fill_strategy == 'forward':
            df[column] = df[column].fillna(method='ffill')
        elif fill_strategy == 'backward':
            df[column] = df[column].fillna(method='bfill')
        
        return df
    
    def _apply_outlier_removal(
        self,
        df: pd.DataFrame,
        transformation: CustomTransformation
    ) -> pd.DataFrame:
        """Apply outlier removal transformation."""
        column = transformation.column
        method = transformation.parameters.get('method', 'iqr')
        
        if method == 'iqr':
            Q1 = df[column].quantile(0.25)
            Q3 = df[column].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            
            # Remove outliers
            df = df[(df[column] >= lower_bound) & (df[column] <= upper_bound)]
        elif method == 'zscore':
            from scipy import stats
            z_threshold = transformation.parameters.get('z_threshold', 3)
            z_scores = stats.zscore(df[column].dropna())
            df = df[abs(z_scores) <= z_threshold]
        
        return df
    
    def _apply_format_standardization(
        self,
        df: pd.DataFrame,
        transformation: CustomTransformation
    ) -> pd.DataFrame:
        """Apply format standardization transformation."""
        column = transformation.column
        format_type = transformation.parameters.get('format_type', 'text')
        
        if format_type == 'text':
            # Common text standardizations
            case_style = transformation.parameters.get('case', 'lower')
            if case_style == 'lower':
                df[column] = df[column].str.lower()
            elif case_style == 'upper':
                df[column] = df[column].str.upper()
            elif case_style == 'title':
                df[column] = df[column].str.title()
            
            # Remove extra whitespace
            df[column] = df[column].str.strip()
            
        elif format_type == 'phone':
            # Standardize phone numbers
            df[column] = df[column].str.replace(r'[^\d]', '', regex=True)
            
        elif format_type == 'email':
            # Standardize email addresses
            df[column] = df[column].str.lower().str.strip()
        
        return df
    
    def _count_affected_rows(
        self,
        df: pd.DataFrame,
        transformation: CustomTransformation
    ) -> int:
        """Count how many rows will be affected by the transformation."""
        column = transformation.column
        
        if transformation.action == TransformationAction.REPLACE_VALUES:
            affected = 0
            for mapping in transformation.value_mappings:
                if pd.isna(mapping.original_value):
                    affected += df[column].isna().sum()
                else:
                    affected += (df[column] == mapping.original_value).sum()
            return affected
        elif transformation.action == TransformationAction.FILL_MISSING:
            return df[column].isna().sum()
        elif transformation.action == TransformationAction.CONVERT_TYPE:
            return len(df)  # Type conversion affects all rows
        else:
            return len(df)  # Conservative estimate
    
    def _generate_impact_summary(
        self,
        original_df: pd.DataFrame,
        transformed_df: pd.DataFrame,
        transformation: CustomTransformation
    ) -> Dict[str, Any]:
        """Generate a summary of the transformation impact."""
        column = transformation.column
        
        summary = {
            'transformation_type': transformation.action.value,
            'column': column,
            'original_shape': original_df.shape,
            'transformed_shape': transformed_df.shape,
            'rows_changed': len(original_df) - len(transformed_df),
        }
        
        if column in original_df.columns and column in transformed_df.columns:
            # Value distribution changes
            original_unique = original_df[column].nunique()
            transformed_unique = transformed_df[column].nunique()
            
            summary.update({
                'original_unique_values': original_unique,
                'transformed_unique_values': transformed_unique,
                'unique_values_change': transformed_unique - original_unique,
                'original_null_count': original_df[column].isna().sum(),
                'transformed_null_count': transformed_df[column].isna().sum(),
            })
            
            # Sample of value changes
            if transformation.action == TransformationAction.REPLACE_VALUES:
                value_changes = {}
                for mapping in transformation.value_mappings:
                    original_count = (original_df[column] == mapping.original_value).sum()
                    if original_count > 0:
                        value_changes[str(mapping.original_value)] = {
                            'new_value': mapping.new_value,
                            'count': original_count
                        }
                summary['value_changes'] = value_changes
        
        return summary
    
    def _get_next_version_number(self, artifact_id: str) -> int:
        """Get the next version number for an artifact."""
        if artifact_id not in self.data_versions:
            return 1
        return len(self.data_versions[artifact_id]) + 1
    
    def _store_version(self, artifact_id: str, df: pd.DataFrame, version: int):
        """Store a data version."""
        if artifact_id not in self.data_versions:
            self.data_versions[artifact_id] = []
        
        # Ensure we have enough space for the version
        while len(self.data_versions[artifact_id]) <= version:
            self.data_versions[artifact_id].append(pd.DataFrame())
        
        self.data_versions[artifact_id][version] = df.copy()
    
    def _calculate_data_hash(self, df: pd.DataFrame) -> str:
        """Calculate a hash of the DataFrame for integrity checking."""
        # Convert DataFrame to string and hash it
        df_string = df.to_string()
        return hashlib.md5(df_string.encode()).hexdigest()
    
    async def get_data_version(self, artifact_id: str, version: int) -> Optional[pd.DataFrame]:
        """Retrieve a specific version of the data."""
        if artifact_id not in self.data_versions:
            return None
        
        if version < 0 or version >= len(self.data_versions[artifact_id]):
            return None
        
        return self.data_versions[artifact_id][version].copy()
    
    async def undo_transformation(
        self,
        artifact_id: str,
        current_version: int,
        user_id: str
    ) -> Tuple[pd.DataFrame, DataVersion]:
        """
        Undo the last transformation by reverting to the previous version.
        
        Args:
            artifact_id: ID of the data artifact
            current_version: Current version number
            user_id: ID of the user performing the undo
            
        Returns:
            Tuple of (reverted_df, data_version)
        """
        if current_version <= 1:
            raise ValueError("Cannot undo: already at the first version")
        
        # Get the previous version
        previous_version = current_version - 1
        reverted_df = await self.get_data_version(artifact_id, previous_version)
        
        if reverted_df is None:
            raise ValueError(f"Cannot find version {previous_version} for artifact {artifact_id}")
        
        # Create a new version entry for the undo
        version_id = str(uuid.uuid4())
        new_version = current_version + 1
        
        data_version = DataVersion(
            version_id=version_id,
            artifact_id=artifact_id,
            version_number=new_version,
            description=f"Undo: reverted to version {previous_version}",
            transformations_applied=[],  # Undo doesn't apply new transformations
            data_hash=self._calculate_data_hash(reverted_df),
            created_at=datetime.now(),
            created_by=user_id
        )
        
        # Store the reverted version
        self._store_version(artifact_id, reverted_df, new_version)
        
        return reverted_df, data_version
    
    async def save_transformation_rule(
        self,
        transformation: CustomTransformation,
        rule_name: str,
        rule_description: str,
        column_pattern: str,
        user_id: str
    ) -> TransformationRule:
        """
        Save a transformation as a reusable rule.
        
        Args:
            transformation: The transformation to save
            rule_name: Name for the rule
            rule_description: Description of the rule
            column_pattern: Pattern for matching columns
            user_id: ID of the user saving the rule
            
        Returns:
            The saved transformation rule
        """
        rule_id = str(uuid.uuid4())
        
        rule = TransformationRule(
            rule_id=rule_id,
            name=rule_name,
            description=rule_description,
            column_pattern=column_pattern,
            action=transformation.action,
            value_mappings=transformation.value_mappings,
            parameters=transformation.parameters,
            created_by=user_id,
            created_at=datetime.now(),
            usage_count=0
        )
        
        self.transformation_rules[rule_id] = rule
        logger.info(f"Saved transformation rule: {rule_name}")
        
        return rule
    
    async def search_transformation_rules(
        self,
        column_name: Optional[str] = None,
        action: Optional[TransformationAction] = None,
        search_term: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> List[TransformationRule]:
        """
        Search for transformation rules based on criteria.
        
        Args:
            column_name: Column name to match against patterns
            action: Type of transformation action
            search_term: Text to search in name/description
            user_id: Filter by rule creator
            
        Returns:
            List of matching transformation rules
        """
        matching_rules = []
        
        for rule in self.transformation_rules.values():
            # Check column pattern match
            if column_name and not self._matches_column_pattern(column_name, rule.column_pattern):
                continue
            
            # Check action match
            if action and rule.action != action:
                continue
            
            # Check search term
            if search_term and not (
                search_term.lower() in rule.name.lower() or
                search_term.lower() in rule.description.lower()
            ):
                continue
            
            # Check user filter
            if user_id and rule.created_by != user_id:
                continue
            
            matching_rules.append(rule)
        
        # Sort by usage count (most used first)
        matching_rules.sort(key=lambda r: r.usage_count, reverse=True)
        
        return matching_rules
    
    def _matches_column_pattern(self, column_name: str, pattern: str) -> bool:
        """Check if a column name matches a pattern."""
        # Simple pattern matching with wildcards
        if pattern == "*":
            return True
        
        # Convert pattern to regex
        regex_pattern = pattern.replace("*", ".*")
        return bool(re.match(regex_pattern, column_name, re.IGNORECASE)) 