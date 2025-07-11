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
        self.model = "gpt-4.1"  # Using consistent model across codebase
        
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