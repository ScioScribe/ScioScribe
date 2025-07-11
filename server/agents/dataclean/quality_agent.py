"""
Data Quality Agent for AI-powered data analysis and suggestion generation.

This agent uses OpenAI's LLM to analyze data quality issues and generate
intelligent suggestions for data cleaning and improvement.
"""

import asyncio
import json
import uuid
from typing import List, Dict, Any, Optional
import pandas as pd
import logging
from openai import AsyncOpenAI

from .models import (
    QualityIssue, 
    Suggestion, 
    SuggestionType, 
    ProcessingResult
)

logger = logging.getLogger(__name__)


class DataQualityAgent:
    """
    AI-powered agent for data quality analysis and suggestion generation.
    
    This agent analyzes datasets to identify quality issues and generates
    actionable suggestions for data cleaning.
    """
    
    def __init__(self, openai_client: AsyncOpenAI):
        """
        Initialize the Data Quality Agent.
        
        Args:
            openai_client: AsyncOpenAI client instance
        """
        self.client = openai_client
        self.model = "gpt-4o-mini"  # Cost-effective model for data analysis
        
    async def analyze_data(self, df: pd.DataFrame) -> List[QualityIssue]:
        """
        Analyze a DataFrame for data quality issues.
        
        Args:
            df: DataFrame to analyze
            
        Returns:
            List of identified quality issues
        """
        try:
            logger.info(f"Analyzing data quality for DataFrame with shape: {df.shape}")
            
            # Generate data summary for AI analysis
            data_summary = self._generate_data_summary(df)
            
            # Analyze different types of quality issues
            issues = []
            
            # 1. Data type issues
            type_issues = await self._analyze_data_types(df, data_summary)
            issues.extend(type_issues)
            
            # 2. Missing value issues
            missing_issues = await self._analyze_missing_values(df, data_summary)
            issues.extend(missing_issues)
            
            # 3. Inconsistency issues
            consistency_issues = await self._analyze_consistency(df, data_summary)
            issues.extend(consistency_issues)
            
            # 4. Outlier detection
            outlier_issues = await self._analyze_outliers(df, data_summary)
            issues.extend(outlier_issues)
            
            logger.info(f"Found {len(issues)} quality issues")
            return issues
            
        except Exception as e:
            logger.error(f"Error analyzing data quality: {str(e)}")
            return []
    
    async def generate_suggestions(self, issues: List[QualityIssue], df: pd.DataFrame) -> List[Suggestion]:
        """
        Generate actionable suggestions based on quality issues.
        
        Args:
            issues: List of quality issues
            df: Original DataFrame
            
        Returns:
            List of AI-generated suggestions
        """
        try:
            suggestions = []
            
            for issue in issues:
                suggestion = await self._generate_suggestion_for_issue(issue, df)
                if suggestion:
                    suggestions.append(suggestion)
                    
            # Rank suggestions by priority
            ranked_suggestions = self._rank_suggestions(suggestions)
            
            logger.info(f"Generated {len(ranked_suggestions)} suggestions")
            return ranked_suggestions
            
        except Exception as e:
            logger.error(f"Error generating suggestions: {str(e)}")
            return []
    
    def _generate_data_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Generate a summary of the DataFrame for AI analysis.
        
        Args:
            df: DataFrame to summarize
            
        Returns:
            Dictionary containing data summary
        """
        summary = {
            'shape': df.shape,
            'columns': list(df.columns),
            'dtypes': df.dtypes.astype(str).to_dict(),
            'null_counts': df.isnull().sum().to_dict(),
            'unique_counts': df.nunique().to_dict(),
            'sample_data': {}
        }
        
        # Add sample data for each column (first 5 unique values)
        for col in df.columns:
            unique_values = df[col].dropna().unique()[:5]
            # Convert to native Python types for JSON serialization
            summary['sample_data'][col] = [
                val.item() if hasattr(val, 'item') else val 
                for val in unique_values
            ]
        
        return summary
    
    async def _analyze_data_types(self, df: pd.DataFrame, summary: Dict[str, Any]) -> List[QualityIssue]:
        """
        Analyze data types for potential issues.
        
        Args:
            df: DataFrame to analyze
            summary: Data summary
            
        Returns:
            List of data type related issues
        """
        prompt = f"""
        Analyze the following dataset for data type issues:
        
        Dataset Summary:
        - Shape: {summary['shape']}
        - Columns: {summary['columns']}
        - Data Types: {summary['dtypes']}
        - Sample Data: {summary['sample_data']}
        
        Look for columns that might have incorrect data types, such as:
        - Numeric data stored as strings
        - Dates stored as strings
        - Categorical data that should be standardized
        
        Respond with a JSON array of issues, each with:
        {{
            "column": "column_name",
            "issue_type": "data_type_mismatch",
            "description": "Brief description of the issue",
            "severity": "low|medium|high",
            "affected_rows": number_of_affected_rows
        }}
        
        If no issues found, return an empty array [].
        """
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a data quality expert. Analyze data and respond only with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=1000
            )
            
            content = response.choices[0].message.content.strip()
            # Clean up the response to extract JSON
            if content.startswith('```json'):
                content = content[7:-3]
            elif content.startswith('```'):
                content = content[3:-3]
            
            issues_data = json.loads(content)
            
            issues = []
            for issue_data in issues_data:
                issue = QualityIssue(
                    issue_id=str(uuid.uuid4()),
                    column=issue_data['column'],
                    issue_type=issue_data['issue_type'],
                    description=issue_data['description'],
                    severity=issue_data['severity'],
                    affected_rows=issue_data['affected_rows']
                )
                issues.append(issue)
            
            return issues
            
        except Exception as e:
            logger.error(f"Error analyzing data types: {str(e)}")
            return []
    
    async def _analyze_missing_values(self, df: pd.DataFrame, summary: Dict[str, Any]) -> List[QualityIssue]:
        """
        Analyze missing values in the dataset.
        
        Args:
            df: DataFrame to analyze
            summary: Data summary
            
        Returns:
            List of missing value related issues
        """
        issues = []
        
        for col, null_count in summary['null_counts'].items():
            if null_count > 0:
                missing_percentage = (null_count / df.shape[0]) * 100
                
                severity = "low"
                if missing_percentage > 20:
                    severity = "high"
                elif missing_percentage > 10:
                    severity = "medium"
                
                issue = QualityIssue(
                    issue_id=str(uuid.uuid4()),
                    column=col,
                    issue_type="missing_values",
                    description=f"Column has {null_count} missing values ({missing_percentage:.1f}%)",
                    severity=severity,
                    affected_rows=null_count
                )
                issues.append(issue)
        
        return issues
    
    async def _analyze_consistency(self, df: pd.DataFrame, summary: Dict[str, Any]) -> List[QualityIssue]:
        """
        Analyze data consistency issues.
        
        Args:
            df: DataFrame to analyze
            summary: Data summary
            
        Returns:
            List of consistency related issues
        """
        prompt = f"""
        Analyze the following dataset for consistency issues:
        
        Sample Data for each column:
        {summary['sample_data']}
        
        Data Types:
        {summary['dtypes']}
        
        Look for inconsistencies such as:
        - Inconsistent categorical values (e.g., 'Yes', 'Y', 'yes')
        - Inconsistent formats (e.g., dates, phone numbers)
        - Inconsistent capitalization
        - Inconsistent spacing or special characters
        
        Respond with a JSON array of issues, each with:
        {{
            "column": "column_name",
            "issue_type": "inconsistent_values",
            "description": "Brief description of the inconsistency",
            "severity": "low|medium|high",
            "affected_rows": estimated_number_of_affected_rows
        }}
        
        If no issues found, return an empty array [].
        """
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a data quality expert. Analyze data and respond only with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=1000
            )
            
            content = response.choices[0].message.content.strip()
            # Clean up the response to extract JSON
            if content.startswith('```json'):
                content = content[7:-3]
            elif content.startswith('```'):
                content = content[3:-3]
            
            issues_data = json.loads(content)
            
            issues = []
            for issue_data in issues_data:
                issue = QualityIssue(
                    issue_id=str(uuid.uuid4()),
                    column=issue_data['column'],
                    issue_type=issue_data['issue_type'],
                    description=issue_data['description'],
                    severity=issue_data['severity'],
                    affected_rows=issue_data['affected_rows']
                )
                issues.append(issue)
            
            return issues
            
        except Exception as e:
            logger.error(f"Error analyzing consistency: {str(e)}")
            return []
    
    async def _analyze_outliers(self, df: pd.DataFrame, summary: Dict[str, Any]) -> List[QualityIssue]:
        """
        Analyze for outliers in numeric columns.
        
        Args:
            df: DataFrame to analyze
            summary: Data summary
            
        Returns:
            List of outlier related issues
        """
        issues = []
        
        numeric_columns = df.select_dtypes(include=['number']).columns
        
        for col in numeric_columns:
            if col in df.columns:
                # Simple outlier detection using IQR method
                Q1 = df[col].quantile(0.25)
                Q3 = df[col].quantile(0.75)
                IQR = Q3 - Q1
                
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                
                outliers = df[(df[col] < lower_bound) | (df[col] > upper_bound)]
                
                if len(outliers) > 0:
                    outlier_percentage = (len(outliers) / len(df)) * 100
                    
                    severity = "low"
                    if outlier_percentage > 10:
                        severity = "high"
                    elif outlier_percentage > 5:
                        severity = "medium"
                    
                    issue = QualityIssue(
                        issue_id=str(uuid.uuid4()),
                        column=col,
                        issue_type="outliers",
                        description=f"Column has {len(outliers)} potential outliers ({outlier_percentage:.1f}%)",
                        severity=severity,
                        affected_rows=len(outliers)
                    )
                    issues.append(issue)
        
        return issues
    
    async def _generate_suggestion_for_issue(self, issue: QualityIssue, df: pd.DataFrame) -> Optional[Suggestion]:
        """
        Generate a suggestion for a specific quality issue.
        
        Args:
            issue: Quality issue to address
            df: Original DataFrame
            
        Returns:
            AI-generated suggestion or None
        """
        # Get sample data for the problematic column
        sample_data = df[issue.column].dropna().unique()[:10].tolist()
        
        prompt = f"""
        Generate a specific, actionable suggestion to fix this data quality issue:
        
        Issue Details:
        - Column: {issue.column}
        - Issue Type: {issue.issue_type}
        - Description: {issue.description}
        - Severity: {issue.severity}
        - Affected Rows: {issue.affected_rows}
        
        Sample Data from Column:
        {sample_data}
        
        Provide a suggestion with:
        1. A clear action to take
        2. The confidence level (0.0-1.0)
        3. The risk level (low/medium/high)
        4. A brief explanation of why this suggestion helps
        
        Respond with JSON:
        {{
            "action": "specific_action_to_take",
            "confidence": confidence_score,
            "risk_level": "low|medium|high",
            "explanation": "Brief explanation of the suggestion"
        }}
        """
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a data quality expert. Provide actionable suggestions and respond only with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=500
            )
            
            content = response.choices[0].message.content.strip()
            # Clean up the response to extract JSON
            if content.startswith('```json'):
                content = content[7:-3]
            elif content.startswith('```'):
                content = content[3:-3]
            
            suggestion_data = json.loads(content)
            
            # Map issue type to suggestion type
            suggestion_type = self._map_issue_to_suggestion_type(issue.issue_type)
            
            suggestion = Suggestion(
                suggestion_id=str(uuid.uuid4()),
                type=suggestion_type,
                column=issue.column,
                description=suggestion_data['action'],
                confidence=suggestion_data['confidence'],
                risk_level=suggestion_data['risk_level'],
                transformation={'action': suggestion_data['action']},
                explanation=suggestion_data['explanation']
            )
            
            return suggestion
            
        except Exception as e:
            logger.error(f"Error generating suggestion for issue {issue.issue_id}: {str(e)}")
            return None
    
    def _map_issue_to_suggestion_type(self, issue_type: str) -> SuggestionType:
        """
        Map issue type to suggestion type.
        
        Args:
            issue_type: Type of quality issue
            
        Returns:
            Corresponding suggestion type
        """
        mapping = {
            'data_type_mismatch': SuggestionType.CONVERT_DATATYPE,
            'missing_values': SuggestionType.FILL_MISSING_VALUES,
            'inconsistent_values': SuggestionType.STANDARDIZE_CATEGORICAL,
            'outliers': SuggestionType.HANDLE_OUTLIERS,
            'format_issues': SuggestionType.FORMAT_STANDARDIZATION
        }
        
        return mapping.get(issue_type, SuggestionType.STANDARDIZE_CATEGORICAL)
    
    def _rank_suggestions(self, suggestions: List[Suggestion]) -> List[Suggestion]:
        """
        Rank suggestions by priority (confidence * severity).
        
        Args:
            suggestions: List of suggestions to rank
            
        Returns:
            Ranked list of suggestions
        """
        def priority_score(suggestion: Suggestion) -> float:
            # Higher confidence and lower risk = higher priority
            risk_multiplier = {'low': 1.0, 'medium': 0.8, 'high': 0.6}
            return suggestion.confidence * risk_multiplier.get(suggestion.risk_level, 0.5)
        
        return sorted(suggestions, key=priority_score, reverse=True)
    
    async def understand_data_semantics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Understand the semantic meaning and context of the data, especially for biomedical research.
        
        Args:
            df: DataFrame to analyze semantically
            
        Returns:
            Dictionary containing semantic understanding of the data
        """
        try:
            logger.info(f"Performing semantic analysis of DataFrame with shape: {df.shape}")
            
            # Generate enhanced data summary for semantic analysis
            semantic_summary = self._generate_semantic_data_summary(df)
            
            # Analyze the data semantically using AI
            semantic_analysis = await self._analyze_data_semantically(semantic_summary)
            
            return {
                "success": True,
                "data_understanding": semantic_analysis.get("data_understanding", "Unable to determine data context"),
                "research_context": semantic_analysis.get("research_context", "Context unclear"),
                "experimental_design": semantic_analysis.get("experimental_design", "Design not apparent"),
                "key_variables": semantic_analysis.get("key_variables", []),
                "data_type_classification": semantic_analysis.get("data_type_classification", "Unknown"),
                "research_domain": semantic_analysis.get("research_domain", "General"),
                "analysis_confidence": semantic_analysis.get("confidence", 0.0)
            }
            
        except Exception as e:
            logger.error(f"Error in semantic data understanding: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "data_understanding": "Unable to analyze data semantically",
                "research_context": "Analysis failed",
                "experimental_design": "Could not determine",
                "key_variables": [],
                "data_type_classification": "Unknown",
                "research_domain": "Unknown",
                "analysis_confidence": 0.0
            }
    
    async def detect_row_operations(self, user_message: str, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Detect if the user wants to add or delete rows from the dataset.
        
        Args:
            user_message: User's natural language message
            df: Current DataFrame
            
        Returns:
            Dictionary containing row operation detection results
        """
        try:
            logger.info(f"Detecting row operations in message: {user_message}")
            
            # Generate context about the current data
            data_context = {
                'shape': df.shape,
                'columns': list(df.columns),
                'sample_data': df.head(3).to_dict('records') if not df.empty else []
            }
            
            prompt = f"""
            Analyze this user message to detect if they want to add or delete rows from their dataset.
            
            User Message: "{user_message}"
            
            Current Dataset Context:
            - Shape: {data_context['shape']} (rows, columns)
            - Columns: {data_context['columns']}
            - Sample Data: {json.dumps(data_context['sample_data'], indent=2)}
            
            Look for intentions to:
            1. Add new rows (e.g., "add a row", "insert a new entry", "create a new record")
            2. Delete rows (e.g., "remove rows", "delete entries", "drop records")
            
            Respond with JSON:
            {{
                "operation_detected": true/false,
                "operation_type": "add_row|delete_row|none",
                "confidence": 0.0-1.0,
                "intent_description": "Brief description of what the user wants to do"
            }}
            """
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a data manipulation expert. Analyze user messages to detect row operations. Respond only with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=500
            )
            
            content = response.choices[0].message.content.strip()
            if content.startswith('```json'):
                content = content[7:-3]
            elif content.startswith('```'):
                content = content[3:-3]
            
            detection_result = json.loads(content)
            logger.info(f"Row operation detection result: {detection_result}")
            
            return detection_result
            
        except Exception as e:
            logger.error(f"Error detecting row operations: {str(e)}")
            return {
                "operation_detected": False,
                "operation_type": "none",
                "confidence": 0.0,
                "intent_description": "Error analyzing message"
            }
    
    async def parse_row_operation_details(self, user_message: str, operation_type: str, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Parse specific details about the row operation the user wants to perform.
        
        Args:
            user_message: User's natural language message
            operation_type: Type of operation (add_row or delete_row)
            df: Current DataFrame
            
        Returns:
            Dictionary containing parsed operation details
        """
        try:
            logger.info(f"Parsing details for {operation_type} operation")
            
            data_context = {
                'columns': list(df.columns),
                'dtypes': df.dtypes.astype(str).to_dict(),
                'sample_data': df.head(3).to_dict('records') if not df.empty else []
            }
            
            if operation_type == "add_row":
                prompt = f"""
                Parse the details for adding a new row to the dataset.
                
                User Message: "{user_message}"
                
                Dataset Context:
                - Columns: {data_context['columns']}
                - Data Types: {data_context['dtypes']}
                - Sample Data: {json.dumps(data_context['sample_data'], indent=2)}
                
                Extract:
                1. Specific column values to set
                2. Any columns that should be left empty/null
                3. Any patterns or references to existing data
                
                Respond with JSON:
                {{
                    "success": true/false,
                    "row_data": {{"column_name": "value", ...}},
                    "missing_columns": ["column1", "column2"],
                    "operation_description": "Description of the row to be added",
                    "confidence": 0.0-1.0
                }}
                """
                
            else:  # delete_row
                prompt = f"""
                Parse the details for deleting rows from the dataset.
                
                User Message: "{user_message}"
                
                Dataset Context:
                - Columns: {data_context['columns']}
                - Data Types: {data_context['dtypes']}
                - Sample Data: {json.dumps(data_context['sample_data'], indent=2)}
                
                Extract:
                1. Specific conditions for row deletion
                2. Row indices if specified
                3. Column-value criteria
                
                Respond with JSON:
                {{
                    "success": true/false,
                    "deletion_criteria": {{"column": "value", ...}},
                    "row_indices": [1, 2, 3] or null,
                    "operation_description": "Description of rows to be deleted",
                    "confidence": 0.0-1.0
                }}
                """
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a data manipulation expert. Parse row operation details accurately. Respond only with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=800
            )
            
            content = response.choices[0].message.content.strip()
            if content.startswith('```json'):
                content = content[7:-3]
            elif content.startswith('```'):
                content = content[3:-3]
            
            parsed_details = json.loads(content)
            logger.info(f"Parsed row operation details: {parsed_details}")
            
            return parsed_details
            
        except Exception as e:
            logger.error(f"Error parsing row operation details: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "operation_description": "Failed to parse operation details",
                "confidence": 0.0
            }
    
    async def validate_row_operation(self, operation_type: str, operation_details: Dict[str, Any], df: pd.DataFrame) -> Dict[str, Any]:
        """
        Validate that the requested row operation is valid for the current dataset.
        
        Args:
            operation_type: Type of operation (add_row or delete_row)
            operation_details: Parsed operation details
            df: Current DataFrame
            
        Returns:
            Dictionary containing validation results
        """
        try:
            logger.info(f"Validating {operation_type} operation")
            
            if operation_type == "add_row":
                return self._validate_add_row(operation_details, df)
            else:  # delete_row
                return self._validate_delete_row(operation_details, df)
                
        except Exception as e:
            logger.error(f"Error validating row operation: {str(e)}")
            return {
                "valid": False,
                "error": str(e),
                "warnings": [],
                "preview": None
            }
    
    def _validate_add_row(self, operation_details: Dict[str, Any], df: pd.DataFrame) -> Dict[str, Any]:
        """
        Validate add row operation with intelligent recommendations.
        
        Args:
            operation_details: Parsed operation details
            df: Current DataFrame
            
        Returns:
            Validation results with helpful recommendations
        """
        warnings = []
        recommendations = []
        
        if not operation_details.get("success", False):
            return {
                "valid": False,
                "error": "Failed to parse row data",
                "warnings": [],
                "recommendations": ["Please specify the data more clearly, for example: 'Add a row with Name=John, Age=30'"],
                "preview": None
            }
        
        row_data = operation_details.get("row_data", {})
        
        # Enhanced column validation with intelligent suggestions
        unknown_columns = set(row_data.keys()) - set(df.columns)
        corrected_row_data = {}
        
        if unknown_columns:
            for unknown_col in unknown_columns:
                # Try to find similar column names
                suggestion = self._suggest_column_correction(unknown_col, df.columns)
                if suggestion:
                    corrected_row_data[suggestion] = row_data[unknown_col]
                    recommendations.append(f"Did you mean '{suggestion}' instead of '{unknown_col}'? I'll use '{suggestion}'.")
                else:
                    available_cols = "', '".join(df.columns)
                    recommendations.append(f"Column '{unknown_col}' doesn't exist. Available columns: '{available_cols}'")
            
            # Use corrected columns
            for known_col, value in row_data.items():
                if known_col not in unknown_columns:
                    corrected_row_data[known_col] = value
                    
            row_data = corrected_row_data
        
        # Check for missing columns and provide helpful guidance
        missing_columns = set(df.columns) - set(row_data.keys())
        if missing_columns:
            # Provide intelligent suggestions for missing values
            missing_suggestions = self._suggest_missing_value_defaults(missing_columns, df)
            if missing_suggestions:
                recommendations.extend(missing_suggestions)
            else:
                warnings.append(f"Missing values for columns: {list(missing_columns)} (will be set to empty)")
        
        # Data type validation and suggestions
        type_warnings = self._validate_data_types(row_data, df)
        if type_warnings:
            recommendations.extend(type_warnings)
        
        # Create preview of new row
        new_row_preview = {}
        for col in df.columns:
            if col in row_data:
                new_row_preview[col] = row_data[col]
            else:
                new_row_preview[col] = None
        
        return {
            "valid": True,
            "warnings": warnings,
            "recommendations": recommendations,
            "preview": new_row_preview,
            "row_data": row_data
        }
    
    def _validate_delete_row(self, operation_details: Dict[str, Any], df: pd.DataFrame) -> Dict[str, Any]:
        """
        Validate delete row operation with intelligent recommendations.
        
        Args:
            operation_details: Parsed operation details
            df: Current DataFrame
            
        Returns:
            Validation results with helpful recommendations
        """
        warnings = []
        recommendations = []
        
        if not operation_details.get("success", False):
            return {
                "valid": False,
                "error": "Failed to parse deletion criteria",
                "warnings": [],
                "recommendations": ["Please specify what to delete more clearly, for example: 'Delete the row where Name is John Doe'"],
                "preview": None
            }
        
        deletion_criteria = operation_details.get("deletion_criteria", {})
        row_indices = operation_details.get("row_indices")
        
        # Validate row indices if provided
        if row_indices:
            invalid_indices = [i for i in row_indices if i < 0 or i >= len(df)]
            if invalid_indices:
                recommendations.append(f"Row indices {invalid_indices} are invalid. Valid range: 0-{len(df)-1}")
                recommendations.append(f"Current data has {len(df)} rows. You can delete rows 0 through {len(df)-1}")
                return {
                    "valid": False,
                    "error": f"Invalid row indices: {invalid_indices}",
                    "warnings": [],
                    "recommendations": recommendations,
                    "preview": None
                }
            
            rows_to_delete = df.iloc[row_indices]
            
        elif deletion_criteria:
            # Enhanced criteria validation with intelligent suggestions
            corrected_criteria = {}
            rows_to_delete = None
            
            for col, value in deletion_criteria.items():
                if col not in df.columns:
                    # Try to find similar column names
                    suggestion = self._suggest_column_correction(col, df.columns)
                    if suggestion:
                        corrected_criteria[suggestion] = value
                        recommendations.append(f"Did you mean '{suggestion}' instead of '{col}'? I'll search in '{suggestion}'.")
                    else:
                        available_cols = "', '".join(df.columns)
                        recommendations.append(f"Column '{col}' doesn't exist. Available columns: '{available_cols}'")
                        return {
                            "valid": False,
                            "error": f"Column '{col}' not found",
                            "warnings": [],
                            "recommendations": recommendations,
                            "preview": None
                        }
                else:
                    corrected_criteria[col] = value
            
            # Find rows matching corrected criteria
            mask = pd.Series([True] * len(df))
            for col, value in corrected_criteria.items():
                # Case-insensitive matching for string values
                if df[col].dtype == 'object':
                    # Try exact match first
                    exact_match = df[col] == value
                    if not exact_match.any():
                        # Try case-insensitive match
                        case_insensitive_match = df[col].astype(str).str.lower() == str(value).lower()
                        if case_insensitive_match.any():
                            mask = mask & case_insensitive_match
                            recommendations.append(f"Found case-insensitive match for '{value}' in column '{col}'")
                        else:
                            # Suggest similar values ONLY for categorical/text data
                            similar_values = self._suggest_similar_values(value, df[col].dropna().unique())
                            if similar_values:
                                recommendations.append(f"No exact match for '{value}' in '{col}'. Did you mean: {', '.join(similar_values[:3])}?")
                            else:
                                available_values = df[col].dropna().unique()[:5]
                                recommendations.append(f"No match for '{value}' in '{col}'. Available values include: {', '.join(map(str, available_values))}{'...' if len(df[col].unique()) > 5 else ''}")
                            
                            return {
                                "valid": False,
                                "error": f"No matching rows found for {col}='{value}'",
                                "warnings": [],
                                "recommendations": recommendations,
                                "preview": None
                            }
                    else:
                        mask = mask & exact_match
                else:
                    # Enhanced handling for NUMERICAL columns
                    try:
                        numeric_value = float(value)
                        numeric_match = df[col] == numeric_value
                        if not numeric_match.any():
                            # For numerical data, provide range/statistical information instead of specific values
                            col_min = df[col].min()
                            col_max = df[col].max()
                            col_mean = df[col].mean()
                            
                            recommendations.append(f"No rows found with {col}={value}")
                            recommendations.append(f"📊 {col} range in your data: {col_min} to {col_max} (average: {col_mean:.1f})")
                            
                            # Check if the value is within a reasonable range
                            if col_min <= numeric_value <= col_max * 2:  # Allow up to 2x max as reasonable
                                recommendations.append(f"✅ {col}={value} is a reasonable value and can be used for adding new rows")
                            else:
                                recommendations.append(f"⚠️  {col}={value} is outside the typical range of your data")
                            
                            return {
                                "valid": False,
                                "error": f"No matching rows found for {col}={value}",
                                "warnings": [],
                                "recommendations": recommendations,
                                "preview": None
                            }
                        mask = mask & numeric_match
                    except (ValueError, TypeError):
                        recommendations.append(f"'{value}' is not a valid number for column '{col}'")
                        recommendations.append(f"📊 {col} should contain numerical values like: {', '.join(map(str, df[col].dropna().unique()[:3]))}")
                        return {
                            "valid": False,
                            "error": f"Invalid numerical value for {col}='{value}'",
                            "warnings": [],
                            "recommendations": recommendations,
                            "preview": None
                        }
            
            rows_to_delete = df[mask]
            
            if rows_to_delete.empty:
                recommendations.append("No rows match your deletion criteria.")
                recommendations.append("Try checking the exact values in your data or using different criteria.")
        
        else:
            return {
                "valid": False,
                "error": "No deletion criteria or row indices provided",
                "warnings": [],
                "recommendations": ["Please specify what to delete, for example: 'Delete the row where Name is John' or 'Delete row at index 0'"],
                "preview": None
            }
        
        # Create preview
        preview = {
            "rows_to_delete": rows_to_delete.head(5).to_dict('records') if not rows_to_delete.empty else [],
            "total_rows_to_delete": len(rows_to_delete),
            "remaining_rows": len(df) - len(rows_to_delete)
        }
        
        # Add helpful information about what will be deleted
        if len(rows_to_delete) > 0:
            if len(rows_to_delete) == 1:
                recommendations.append(f"This will delete 1 row from your data.")
            else:
                recommendations.append(f"This will delete {len(rows_to_delete)} rows from your data.")
        
        return {
            "valid": True,
            "warnings": warnings,
            "recommendations": recommendations,
            "preview": preview,
            "deletion_criteria": corrected_criteria if 'corrected_criteria' in locals() else deletion_criteria,
            "row_indices": row_indices
        }
    
    def _suggest_column_correction(self, wrong_column: str, available_columns: List[str]) -> Optional[str]:
        """
        Suggest a correction for a mistyped column name using fuzzy matching.
        
        Args:
            wrong_column: The incorrect column name
            available_columns: List of available column names
            
        Returns:
            Best matching column name or None
        """
        from difflib import SequenceMatcher
        
        wrong_column_lower = wrong_column.lower()
        best_match = None
        best_ratio = 0.0
        
        for col in available_columns:
            # Calculate similarity ratio
            ratio = SequenceMatcher(None, wrong_column_lower, col.lower()).ratio()
            
            # Also check if wrong_column is contained in col or vice versa
            if wrong_column_lower in col.lower() or col.lower() in wrong_column_lower:
                ratio = max(ratio, 0.8)
            
            if ratio > best_ratio and ratio > 0.6:  # Threshold for similarity
                best_ratio = ratio
                best_match = col
        
        return best_match
    
    def _suggest_similar_values(self, wrong_value: str, available_values: List[Any]) -> List[str]:
        """
        Suggest similar values for a mistyped value.
        
        Args:
            wrong_value: The incorrect value
            available_values: List of available values
            
        Returns:
            List of similar values
        """
        from difflib import SequenceMatcher
        
        wrong_value_str = str(wrong_value).lower()
        suggestions = []
        
        for value in available_values:
            value_str = str(value).lower()
            ratio = SequenceMatcher(None, wrong_value_str, value_str).ratio()
            
            # Also check partial matches
            if wrong_value_str in value_str or value_str in wrong_value_str:
                ratio = max(ratio, 0.7)
            
            if ratio > 0.6:  # Threshold for similarity
                suggestions.append((str(value), ratio))
        
        # Sort by similarity and return top matches
        suggestions.sort(key=lambda x: x[1], reverse=True)
        return [s[0] for s in suggestions[:3]]
    
    def _suggest_missing_value_defaults(self, missing_columns: set, df: pd.DataFrame) -> List[str]:
        """
        Suggest default values for missing columns with data-type aware recommendations.
        
        Args:
            missing_columns: Set of missing column names
            df: Current DataFrame
            
        Returns:
            List of suggestions for missing values
        """
        suggestions = []
        
        for col in missing_columns:
            col_data = df[col].dropna()
            
            if len(col_data) == 0:
                suggestions.append(f"Column '{col}' has no existing data to suggest a default value.")
                continue
            
            # Enhanced handling for numeric columns
            if pd.api.types.is_numeric_dtype(col_data):
                col_min = col_data.min()
                col_max = col_data.max()
                mean_val = col_data.mean()
                median_val = col_data.median()
                
                suggestions.append(f"📊 '{col}' statistics: Range {col_min}-{col_max}, Average {mean_val:.1f}, Median {median_val:.1f}")
                suggestions.append(f"💡 You can use any reasonable number for '{col}' (suggestion: use a value between {col_min} and {col_max})")
                
                # Show a few common values as examples, but emphasize flexibility
                common_values = col_data.mode()
                if len(common_values) > 0:
                    suggestions.append(f"📈 Most common {col} values: {', '.join(map(str, common_values[:3]))}")
            
            # For categorical/text columns, show actual options
            else:
                common_values = col_data.value_counts().head(3)
                if len(common_values) > 0:
                    value_list = ', '.join([f"'{val}'" for val in common_values.index])
                    suggestions.append(f"🏷️  '{col}' available options: {value_list}")
                    
                    total_unique = col_data.nunique()
                    if total_unique > 3:
                        suggestions.append(f"📝 '{col}' has {total_unique} different values total")
        
        return suggestions
    
    def _validate_data_types(self, row_data: Dict[str, Any], df: pd.DataFrame) -> List[str]:
        """
        Validate data types and suggest corrections.
        
        Args:
            row_data: Row data to validate
            df: Current DataFrame
            
        Returns:
            List of type-related recommendations
        """
        recommendations = []
        
        for col, value in row_data.items():
            if col not in df.columns:
                continue
                
            expected_dtype = df[col].dtype
            
            # Check numeric columns
            if pd.api.types.is_numeric_dtype(expected_dtype):
                try:
                    float(value)  # Try to convert to number
                except (ValueError, TypeError):
                    # Suggest numeric conversion
                    recommendations.append(f"'{col}' should be a number, but got '{value}'. Please provide a numeric value.")
                    
                    # Try to suggest a numeric interpretation
                    value_str = str(value).lower()
                    number_words = {
                        'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
                        'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
                        'twenty': 20, 'thirty': 30, 'forty': 40, 'fifty': 50
                    }
                    
                    for word, num in number_words.items():
                        if word in value_str:
                            recommendations.append(f"Did you mean {num} for '{col}'?")
                            break
            
            # Check date columns (if column name suggests it's a date)
            elif 'date' in col.lower() or 'time' in col.lower():
                # Basic date format validation could be added here
                pass
        
        return recommendations
    
    async def execute_row_operation(self, operation_type: str, operation_details: Dict[str, Any], df: pd.DataFrame) -> Dict[str, Any]:
        """
        Execute the validated row operation on the DataFrame.
        
        Args:
            operation_type: Type of operation (add_row or delete_row)
            operation_details: Validated operation details
            df: Current DataFrame
            
        Returns:
            Dictionary containing execution results and modified DataFrame
        """
        try:
            logger.info(f"Executing {operation_type} operation")
            
            if operation_type == "add_row":
                return self._execute_add_row(operation_details, df)
            else:  # delete_row
                return self._execute_delete_row(operation_details, df)
                
        except Exception as e:
            logger.error(f"Error executing row operation: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "modified_df": df,
                "changes_made": []
            }
    
    def _execute_add_row(self, operation_details: Dict[str, Any], df: pd.DataFrame) -> Dict[str, Any]:
        """
        Execute add row operation.
        
        Args:
            operation_details: Validated operation details
            df: Current DataFrame
            
        Returns:
            Execution results
        """
        row_data = operation_details.get("row_data", {})
        
        # Create new row with all columns
        new_row = {}
        for col in df.columns:
            if col in row_data:
                new_row[col] = row_data[col]
            else:
                new_row[col] = None
        
        # Add the new row
        modified_df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        
        changes_made = [f"Added 1 new row with data: {row_data}"]
        
        return {
            "success": True,
            "modified_df": modified_df,
            "changes_made": changes_made,
            "rows_added": 1,
            "new_shape": modified_df.shape
        }
    
    def _execute_delete_row(self, operation_details: Dict[str, Any], df: pd.DataFrame) -> Dict[str, Any]:
        """
        Execute delete row operation.
        
        Args:
            operation_details: Validated operation details
            df: Current DataFrame
            
        Returns:
            Execution results
        """
        deletion_criteria = operation_details.get("deletion_criteria", {})
        row_indices = operation_details.get("row_indices")
        
        if row_indices:
            # Delete by indices
            modified_df = df.drop(df.index[row_indices]).reset_index(drop=True)
            changes_made = [f"Deleted {len(row_indices)} rows by index: {row_indices}"]
            rows_deleted = len(row_indices)
            
        elif deletion_criteria:
            # Delete by criteria
            mask = pd.Series([True] * len(df))
            for col, value in deletion_criteria.items():
                if col in df.columns:
                    mask = mask & (df[col] == value)
            
            rows_to_delete = df[mask]
            modified_df = df[~mask].reset_index(drop=True)
            changes_made = [f"Deleted {len(rows_to_delete)} rows matching criteria: {deletion_criteria}"]
            rows_deleted = len(rows_to_delete)
            
        else:
            return {
                "success": False,
                "error": "No valid deletion criteria provided",
                "modified_df": df,
                "changes_made": []
            }
        
        return {
            "success": True,
            "modified_df": modified_df,
            "changes_made": changes_made,
            "rows_deleted": rows_deleted,
            "new_shape": modified_df.shape
        }

    def _generate_semantic_data_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Generate an enhanced summary focused on semantic understanding.
        
        Args:
            df: DataFrame to summarize
            
        Returns:
            Dictionary containing semantic-focused data summary
        """
        summary = {
            'shape': df.shape,
            'columns': list(df.columns),
            'column_analysis': {},
            'potential_measurements': [],
            'potential_conditions': [],
            'potential_subjects': []
        }
        
        # Analyze each column for semantic clues
        for col in df.columns:
            col_lower = col.lower()
            sample_values = df[col].dropna().unique()[:10]
            
            # Convert to native Python types for JSON serialization
            sample_values_clean = []
            for val in sample_values:
                if hasattr(val, 'item'):
                    sample_values_clean.append(val.item())
                else:
                    sample_values_clean.append(str(val))
            
            column_info = {
                'name': col,
                'sample_values': sample_values_clean,
                'data_type': str(df[col].dtype),
                'unique_count': int(df[col].nunique()),
                'null_count': int(df[col].isnull().sum()),
                'potential_role': self._infer_column_role(col, df[col])
            }
            
            summary['column_analysis'][col] = column_info
            
            # Categorize potential research elements
            if any(keyword in col_lower for keyword in ['concentration', 'dose', 'level', 'amount', 'intensity', 'expression', 'activity']):
                summary['potential_measurements'].append(col)
            elif any(keyword in col_lower for keyword in ['treatment', 'condition', 'group', 'strain', 'genotype', 'drug']):
                summary['potential_conditions'].append(col)
            elif any(keyword in col_lower for keyword in ['subject', 'animal', 'patient', 'sample', 'id', 'specimen']):
                summary['potential_subjects'].append(col)
        
        return summary
    
    def _infer_column_role(self, col_name: str, series: pd.Series) -> str:
        """
        Infer the likely role of a column in a research context.
        
        Args:
            col_name: Name of the column
            series: Pandas Series for the column
            
        Returns:
            Inferred role of the column
        """
        col_lower = col_name.lower()
        
        # Check for common biomedical patterns
        if any(keyword in col_lower for keyword in ['id', 'subject', 'sample', 'specimen']):
            return "identifier"
        elif any(keyword in col_lower for keyword in ['treatment', 'condition', 'group', 'strain', 'genotype']):
            return "experimental_condition"
        elif any(keyword in col_lower for keyword in ['concentration', 'dose', 'level', 'amount']):
            return "measurement_value"
        elif any(keyword in col_lower for keyword in ['time', 'day', 'hour', 'date']):
            return "temporal"
        elif any(keyword in col_lower for keyword in ['response', 'outcome', 'result', 'score']):
            return "dependent_variable"
        elif series.dtype in ['int64', 'float64'] and series.nunique() > 10:
            return "continuous_measurement"
        elif series.dtype == 'object' and series.nunique() < 10:
            return "categorical_factor"
        else:
            return "unknown"
    
    async def _analyze_data_semantically(self, semantic_summary: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use AI to analyze the semantic meaning of the data.
        
        Args:
            semantic_summary: Enhanced data summary
            
        Returns:
            Semantic analysis results
        """
        prompt = f"""
        You are a biomedical research expert. Analyze this dataset to understand what research it represents.
        
        Dataset Information:
        - Shape: {semantic_summary['shape']} (rows: subjects/observations, columns: variables)
        - Columns: {semantic_summary['columns']}
        - Potential Measurements: {semantic_summary['potential_measurements']}
        - Potential Conditions: {semantic_summary['potential_conditions']}
        - Potential Subjects: {semantic_summary['potential_subjects']}
        
        Column Analysis:
        {json.dumps(semantic_summary['column_analysis'], indent=2)}
        
        Based on column names, data types, and sample values, provide insight into:
        1. What type of research/experiment this data represents
        2. What the main research question or hypothesis might be
        3. What experimental design was likely used
        4. What are the key variables (independent, dependent, control)
        5. What research domain this belongs to (e.g., neuroscience, molecular biology, pharmacology)
        
        Respond with JSON:
        {{
            "data_understanding": "A clear, concise description of what this data represents (e.g., 'This appears to be data from a C. elegans study examining the effects of CO2 concentration on behavioral responses')",
            "research_context": "The broader research context and potential research question",
            "experimental_design": "The likely experimental design and methodology",
            "key_variables": [
                {{
                    "name": "variable_name",
                    "role": "independent|dependent|control|confounding",
                    "description": "what this variable measures"
                }}
            ],
            "data_type_classification": "Type of study (e.g., dose-response, time-series, comparative, screening)",
            "research_domain": "Primary research domain",
            "confidence": 0.85
        }}
        """
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a biomedical research expert who can intelligently interpret research data. Respond only with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=1500
            )
            
            content = response.choices[0].message.content.strip()
            # Clean up the response to extract JSON
            if content.startswith('```json'):
                content = content[7:-3]
            elif content.startswith('```'):
                content = content[3:-3]
            
            semantic_analysis = json.loads(content)
            return semantic_analysis
            
        except Exception as e:
            logger.error(f"Error in semantic analysis: {str(e)}")
            return {
                "data_understanding": "Unable to determine data context due to analysis error",
                "research_context": "Analysis failed",
                "experimental_design": "Could not determine",
                "key_variables": [],
                "data_type_classification": "Unknown",
                "research_domain": "Unknown",
                "confidence": 0.0
            } 