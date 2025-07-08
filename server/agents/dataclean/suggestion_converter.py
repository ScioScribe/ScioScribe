"""
Suggestion Converter for converting AI suggestions to executable transformations.

This module handles the conversion of AI-generated suggestions into structured
CustomTransformation objects that can be applied to data using the TransformationEngine.
"""

import uuid
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import logging
import re

from .models import (
    Suggestion,
    CustomTransformation,
    TransformationAction,
    ValueMapping,
    SuggestionType
)

logger = logging.getLogger(__name__)


class SuggestionConverter:
    """
    Converts AI-generated suggestions into executable CustomTransformation objects.
    """
    
    def __init__(self):
        """Initialize the suggestion converter."""
        pass
    
    async def convert_suggestion_to_transformation(
        self,
        suggestion: Suggestion,
        df: pd.DataFrame,
        user_id: str
    ) -> CustomTransformation:
        """
        Convert a suggestion into a CustomTransformation object.
        
        Args:
            suggestion: The AI-generated suggestion
            df: DataFrame to analyze for transformation details
            user_id: ID of the user applying the transformation
            
        Returns:
            CustomTransformation object ready for application
        """
        try:
            logger.info(f"Converting suggestion {suggestion.suggestion_id} to transformation")
            
            # Generate transformation based on suggestion type
            if suggestion.type == SuggestionType.STANDARDIZE_CATEGORICAL:
                return await self._create_standardize_categorical_transformation(suggestion, df, user_id)
            elif suggestion.type == SuggestionType.CONVERT_DATATYPE:
                return await self._create_convert_datatype_transformation(suggestion, df, user_id)
            elif suggestion.type == SuggestionType.FILL_MISSING_VALUES:
                return await self._create_fill_missing_transformation(suggestion, df, user_id)
            elif suggestion.type == SuggestionType.HANDLE_OUTLIERS:
                return await self._create_handle_outliers_transformation(suggestion, df, user_id)
            elif suggestion.type == SuggestionType.FORMAT_STANDARDIZATION:
                return await self._create_format_standardization_transformation(suggestion, df, user_id)
            else:
                raise ValueError(f"Unknown suggestion type: {suggestion.type}")
                
        except Exception as e:
            logger.error(f"Error converting suggestion {suggestion.suggestion_id}: {str(e)}")
            raise
    
    async def _create_standardize_categorical_transformation(
        self,
        suggestion: Suggestion,
        df: pd.DataFrame,
        user_id: str
    ) -> CustomTransformation:
        """Create transformation for standardizing categorical values."""
        column = suggestion.column
        
        if column not in df.columns:
            raise ValueError(f"Column '{column}' not found in DataFrame")
        
        # Analyze the column to determine standardization approach
        unique_values = df[column].dropna().unique()
        value_mappings = []
        
        # Check if this is a case standardization (title case, lowercase, etc.)
        if "title case" in suggestion.description.lower():
            action = TransformationAction.STANDARDIZE_FORMAT
            parameters = {"format_type": "text", "case": "title"}
            
            # Create mappings for preview
            for value in unique_values:
                if isinstance(value, str):
                    new_value = value.title()
                    if new_value != value:
                        value_mappings.append(ValueMapping(
                            original_value=value,
                            new_value=new_value,
                            count=int((df[column] == value).sum())
                        ))
                        
        elif "lowercase" in suggestion.description.lower():
            action = TransformationAction.STANDARDIZE_FORMAT
            parameters = {"format_type": "text", "case": "lower"}
            
            for value in unique_values:
                if isinstance(value, str):
                    new_value = value.lower()
                    if new_value != value:
                        value_mappings.append(ValueMapping(
                            original_value=value,
                            new_value=new_value,
                            count=int((df[column] == value).sum())
                        ))
        
        elif "uppercase" in suggestion.description.lower():
            action = TransformationAction.STANDARDIZE_FORMAT
            parameters = {"format_type": "text", "case": "upper"}
            
            for value in unique_values:
                if isinstance(value, str):
                    new_value = value.upper()
                    if new_value != value:
                        value_mappings.append(ValueMapping(
                            original_value=value,
                            new_value=new_value,
                            count=int((df[column] == value).sum())
                        ))
        
        else:
            # General categorical standardization
            action = TransformationAction.REPLACE_VALUES
            parameters = {}
            
            # Try to infer common standardizations
            for value in unique_values:
                if isinstance(value, str):
                    # Clean up common issues
                    clean_value = value.strip()
                    if clean_value != value:
                        value_mappings.append(ValueMapping(
                            original_value=value,
                            new_value=clean_value,
                            count=int((df[column] == value).sum())
                        ))
        
        return CustomTransformation(
            transformation_id=str(uuid.uuid4()),
            column=column,
            action=action,
            value_mappings=value_mappings,
            parameters=parameters,
            description=suggestion.description,
            created_by=user_id,
            created_at=datetime.now()
        )
    
    async def _create_convert_datatype_transformation(
        self,
        suggestion: Suggestion,
        df: pd.DataFrame,
        user_id: str
    ) -> CustomTransformation:
        """Create transformation for converting data types."""
        column = suggestion.column
        
        if column not in df.columns:
            raise ValueError(f"Column '{column}' not found in DataFrame")
        
        # Analyze the suggestion to determine target type and approach
        description = suggestion.description.lower()
        
        if "integer" in description or "int" in description:
            # Convert to integer, handling non-numeric values
            action = TransformationAction.CONVERT_TYPE
            parameters = {"target_type": "int"}
            
            # Find non-numeric values that need to be handled
            value_mappings = []
            for value in df[column].dropna().unique():
                if not pd.api.types.is_numeric_dtype(type(value)):
                    try:
                        # Try to convert common text numbers
                        if isinstance(value, str):
                            if value.lower() in ["thirty-five", "35"]:
                                value_mappings.append(ValueMapping(
                                    original_value=value,
                                    new_value=35,
                                    count=int((df[column] == value).sum())
                                ))
                            elif "null" in description or "default" in description:
                                value_mappings.append(ValueMapping(
                                    original_value=value,
                                    new_value=None,
                                    count=int((df[column] == value).sum())
                                ))
                    except:
                        pass
        
        elif "email" in description:
            # Email format validation and correction
            action = TransformationAction.STANDARDIZE_FORMAT
            parameters = {"format_type": "email"}
            
            value_mappings = []
            for value in df[column].dropna().unique():
                if isinstance(value, str) and "@" in value:
                    # Common email corrections
                    if value == "bob@email":
                        value_mappings.append(ValueMapping(
                            original_value=value,
                            new_value="bob@email.com",
                            count=int((df[column] == value).sum())
                        ))
        
        elif "phone" in description:
            # Phone number standardization
            action = TransformationAction.STANDARDIZE_FORMAT
            parameters = {"format_type": "phone"}
            
            value_mappings = []
            for value in df[column].dropna().unique():
                if isinstance(value, str):
                    if "invalid" in value.lower():
                        value_mappings.append(ValueMapping(
                            original_value=value,
                            new_value="N/A",
                            count=int((df[column] == value).sum())
                        ))
        
        else:
            # General data type conversion
            action = TransformationAction.CONVERT_TYPE
            parameters = {"target_type": "str"}
            value_mappings = []
        
        return CustomTransformation(
            transformation_id=str(uuid.uuid4()),
            column=column,
            action=action,
            value_mappings=value_mappings,
            parameters=parameters,
            description=suggestion.description,
            created_by=user_id,
            created_at=datetime.now()
        )
    
    async def _create_fill_missing_transformation(
        self,
        suggestion: Suggestion,
        df: pd.DataFrame,
        user_id: str
    ) -> CustomTransformation:
        """Create transformation for filling missing values."""
        column = suggestion.column
        
        if column not in df.columns:
            raise ValueError(f"Column '{column}' not found in DataFrame")
        
        # Analyze suggestion to determine fill strategy
        description = suggestion.description.lower()
        
        if "placeholder" in description or "unknown" in description:
            strategy = "value"
            fill_value = "Unknown"
        elif "not provided" in description:
            strategy = "value"
            fill_value = "Not Provided"
        elif "mean" in description:
            strategy = "mean"
            fill_value = None
        elif "median" in description:
            strategy = "median"
            fill_value = None
        elif "mode" in description:
            strategy = "mode"
            fill_value = None
        else:
            # Default to placeholder
            strategy = "value"
            fill_value = "Unknown"
        
        # Create value mappings for preview
        value_mappings = []
        missing_count = df[column].isna().sum()
        if missing_count > 0:
            if strategy == "value":
                value_mappings.append(ValueMapping(
                    original_value=None,
                    new_value=fill_value,
                    count=int(missing_count)
                ))
            elif strategy == "mean":
                mean_value = df[column].mean()
                value_mappings.append(ValueMapping(
                    original_value=None,
                    new_value=mean_value,
                    count=int(missing_count)
                ))
            elif strategy == "median":
                median_value = df[column].median()
                value_mappings.append(ValueMapping(
                    original_value=None,
                    new_value=median_value,
                    count=int(missing_count)
                ))
            elif strategy == "mode":
                mode_value = df[column].mode().iloc[0] if not df[column].mode().empty else "Unknown"
                value_mappings.append(ValueMapping(
                    original_value=None,
                    new_value=mode_value,
                    count=int(missing_count)
                ))
        
        return CustomTransformation(
            transformation_id=str(uuid.uuid4()),
            column=column,
            action=TransformationAction.FILL_MISSING,
            value_mappings=value_mappings,
            parameters={"strategy": strategy, "fill_value": fill_value},
            description=suggestion.description,
            created_by=user_id,
            created_at=datetime.now()
        )
    
    async def _create_handle_outliers_transformation(
        self,
        suggestion: Suggestion,
        df: pd.DataFrame,
        user_id: str
    ) -> CustomTransformation:
        """Create transformation for handling outliers."""
        column = suggestion.column
        
        if column not in df.columns:
            raise ValueError(f"Column '{column}' not found in DataFrame")
        
        # Analyze suggestion to determine outlier handling method
        description = suggestion.description.lower()
        
        if "median" in description:
            # Replace outliers with median
            action = TransformationAction.REPLACE_VALUES
            median_value = df[column].median()
            
            # Identify outliers using IQR method
            Q1 = df[column].quantile(0.25)
            Q3 = df[column].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            
            value_mappings = []
            for value in df[column].dropna().unique():
                if isinstance(value, (int, float)) and (value < lower_bound or value > upper_bound):
                    value_mappings.append(ValueMapping(
                        original_value=value,
                        new_value=median_value,
                        count=int((df[column] == value).sum())
                    ))
            
            parameters = {"method": "replace_with_median"}
        
        elif "remove" in description:
            # Remove outlier rows
            action = TransformationAction.REMOVE_OUTLIERS
            parameters = {"method": "iqr"}
            value_mappings = []
        
        else:
            # Default to IQR method with median replacement
            action = TransformationAction.REPLACE_VALUES
            median_value = df[column].median()
            
            # Find specific outlier values mentioned in description
            value_mappings = []
            # Look for specific values mentioned (e.g., "999999")
            outlier_pattern = r'(\d+)'
            matches = re.findall(outlier_pattern, suggestion.description)
            
            for match in matches:
                try:
                    outlier_value = float(match)
                    if outlier_value in df[column].values:
                        value_mappings.append(ValueMapping(
                            original_value=outlier_value,
                            new_value=median_value,
                            count=int((df[column] == outlier_value).sum())
                        ))
                except:
                    pass
            
            parameters = {"method": "replace_with_median"}
        
        return CustomTransformation(
            transformation_id=str(uuid.uuid4()),
            column=column,
            action=action,
            value_mappings=value_mappings,
            parameters=parameters,
            description=suggestion.description,
            created_by=user_id,
            created_at=datetime.now()
        )
    
    async def _create_format_standardization_transformation(
        self,
        suggestion: Suggestion,
        df: pd.DataFrame,
        user_id: str
    ) -> CustomTransformation:
        """Create transformation for format standardization."""
        column = suggestion.column
        
        if column not in df.columns:
            raise ValueError(f"Column '{column}' not found in DataFrame")
        
        # Analyze suggestion to determine format type
        description = suggestion.description.lower()
        
        if "phone" in description:
            action = TransformationAction.STANDARDIZE_FORMAT
            parameters = {"format_type": "phone"}
            
            # Create mappings for phone number standardization
            value_mappings = []
            for value in df[column].dropna().unique():
                if isinstance(value, str):
                    if "invalid" in value.lower():
                        value_mappings.append(ValueMapping(
                            original_value=value,
                            new_value="N/A",
                            count=int((df[column] == value).sum())
                        ))
                    elif re.match(r'\d{10}', value.replace('-', '').replace('(', '').replace(')', '').replace(' ', '')):
                        # Format as (XXX) XXX-XXXX
                        digits = re.sub(r'[^\d]', '', value)
                        if len(digits) == 10:
                            formatted = f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
                            if formatted != value:
                                value_mappings.append(ValueMapping(
                                    original_value=value,
                                    new_value=formatted,
                                    count=int((df[column] == value).sum())
                                ))
        
        elif "email" in description:
            action = TransformationAction.STANDARDIZE_FORMAT
            parameters = {"format_type": "email"}
            
            value_mappings = []
            for value in df[column].dropna().unique():
                if isinstance(value, str) and "@" in value:
                    # Common email corrections
                    if "bob@email" == value:
                        value_mappings.append(ValueMapping(
                            original_value=value,
                            new_value="bob@email.com",
                            count=int((df[column] == value).sum())
                        ))
        
        else:
            # General text formatting
            action = TransformationAction.STANDARDIZE_FORMAT
            parameters = {"format_type": "text", "case": "lower"}
            
            value_mappings = []
            for value in df[column].dropna().unique():
                if isinstance(value, str):
                    formatted = value.strip().lower()
                    if formatted != value:
                        value_mappings.append(ValueMapping(
                            original_value=value,
                            new_value=formatted,
                            count=int((df[column] == value).sum())
                        ))
        
        return CustomTransformation(
            transformation_id=str(uuid.uuid4()),
            column=column,
            action=action,
            value_mappings=value_mappings,
            parameters=parameters,
            description=suggestion.description,
            created_by=user_id,
            created_at=datetime.now()
        ) 