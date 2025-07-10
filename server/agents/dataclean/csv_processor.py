"""
CSV Direct Processor for artifact-free data cleaning.

This module provides direct CSV string processing without the complexity
of data artifacts, enabling streamlined conversation-based data cleaning.
"""

import io
import uuid
import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from .models import (
    CSVMessageRequest, 
    CSVProcessingResponse, 
    CSVConversationState,
    CSVAnalysisResult
)
from .quality_agent import DataQualityAgent

logger = logging.getLogger(__name__)


class CSVDirectProcessor:
    """
    Direct CSV processor that works with CSV strings without artifacts.
    
    This processor handles:
    - CSV string parsing and validation
    - Quality analysis using existing quality agent
    - Direct transformations on CSV data
    - Response generation for conversation flow
    """
    
    def __init__(self, openai_client=None):
        """Initialize the CSV processor."""
        self.openai_client = openai_client
        self.quality_agent = DataQualityAgent(openai_client) if openai_client else None
        self.session_states: Dict[str, CSVConversationState] = {}
    
    async def process_csv_message(self, request: CSVMessageRequest) -> CSVProcessingResponse:
        """
        Process a CSV message request through the conversation flow.
        
        Args:
            request: CSV message request with CSV data and user message
            
        Returns:
            CSVProcessingResponse with processing results
        """
        try:
            # Validate CSV data
            if not request.csv_data.strip():
                return CSVProcessingResponse(
                    success=False,
                    original_csv=request.csv_data,
                    session_id=request.session_id,
                    error_message="Empty CSV data provided"
                )
            
            # Parse CSV to DataFrame
            df = self._parse_csv_string(request.csv_data)
            if df is None:
                return CSVProcessingResponse(
                    success=False,
                    original_csv=request.csv_data,
                    session_id=request.session_id,
                    error_message="Invalid CSV format"
                )
            
            # Update or create session state
            state = self._get_or_create_session_state(request, df)
            
            # Analyze CSV quality
            analysis_result = await self.analyze_csv_quality(request.csv_data)
            
            # Determine response based on user message
            if request.user_message.lower().strip() in ["hi", "hello", "hey"]:
                response_message = await self._generate_greeting_response(df, analysis_result)
            else:
                response_message = await self._generate_processing_response(
                    request.user_message, df, analysis_result
                )
            
            # Update session state
            state.user_message = request.user_message
            state.response = response_message
            state.quality_issues = analysis_result.quality_issues
            state.confidence_score = analysis_result.confidence_score
            state.updated_at = datetime.now()
            
            # Build response
            response = CSVProcessingResponse(
                success=True,
                original_csv=request.csv_data,
                cleaned_csv=None,  # No changes yet for initial processing
                changes_made=[],
                suggestions=analysis_result.suggestions,
                requires_approval=False,
                confidence_score=analysis_result.confidence_score,
                session_id=request.session_id,
                conversation_active=True,
                response_message=response_message,
                intent="greeting" if request.user_message.lower().strip() in ["hi", "hello", "hey"] else "analysis"
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing CSV message: {str(e)}")
            return CSVProcessingResponse(
                success=False,
                original_csv=request.csv_data,
                session_id=request.session_id,
                error_message=f"Processing failed: {str(e)}"
            )
    
    async def analyze_csv_quality(self, csv_data: str) -> CSVAnalysisResult:
        """
        Analyze CSV quality without creating artifacts.
        
        Args:
            csv_data: CSV data as string
            
        Returns:
            CSVAnalysisResult with quality analysis
        """
        try:
            # Parse CSV
            df = self._parse_csv_string(csv_data)
            if df is None:
                return CSVAnalysisResult(
                    data_shape=[0, 0],
                    column_names=[],
                    quality_issues=["Invalid CSV format"],
                    suggestions=["Please provide valid CSV data"],
                    confidence_score=0.0,
                    analysis_notes=["CSV parsing failed"]
                )
            
            # Basic analysis
            data_shape = [len(df), len(df.columns)]
            column_names = df.columns.tolist()
            quality_issues = []
            suggestions = []
            analysis_notes = []
            
            # Check for common issues
            if df.isnull().any().any():
                null_counts = df.isnull().sum().to_dict()
                missing_columns = [col for col, count in null_counts.items() if count > 0]
                quality_issues.append(f"Missing values found in columns: {', '.join(missing_columns)}")
                suggestions.append("Consider filling or removing missing values")
            
            if df.duplicated().any():
                duplicate_count = df.duplicated().sum()
                quality_issues.append(f"Found {duplicate_count} duplicate rows")
                suggestions.append("Consider removing duplicate rows")
            
            # Check for mixed data types
            for col in df.columns:
                if df[col].dtype == 'object':
                    try:
                        pd.to_numeric(df[col], errors='raise')
                    except:
                        # Mixed types detected
                        unique_vals = df[col].unique()
                        if len(unique_vals) < 10:  # Likely categorical
                            analysis_notes.append(f"Column '{col}' appears to be categorical")
                        else:
                            analysis_notes.append(f"Column '{col}' contains mixed text data")
            
            # Use AI quality agent if available
            if self.quality_agent:
                try:
                    ai_issues = await self.quality_agent.analyze_data(df)
                    # Merge AI-detected issues into overall quality issues list
                    for issue in ai_issues:
                        if hasattr(issue, "description"):
                            quality_issues.append(issue.description)
                        elif isinstance(issue, dict) and "description" in issue:
                            quality_issues.append(issue["description"])
                        else:
                            # Fallback – string representation
                            quality_issues.append(str(issue))

                    ai_suggestions = await self.quality_agent.generate_suggestions(ai_issues, df)
                    
                    # Extract suggestions from AI response
                    for suggestion in ai_suggestions:
                        if hasattr(suggestion, 'description'):
                            suggestions.append(suggestion.description)
                        elif isinstance(suggestion, dict) and 'description' in suggestion:
                            suggestions.append(suggestion['description'])
                    
                    analysis_notes.append(f"AI analysis completed with {len(ai_issues)} issues identified")
                    
                except Exception as e:
                    analysis_notes.append(f"AI analysis failed: {str(e)}")
            
            # Calculate confidence score
            confidence_score = self._calculate_confidence_score(df, quality_issues)
            
            return CSVAnalysisResult(
                data_shape=data_shape,
                column_names=column_names,
                quality_issues=quality_issues,
                suggestions=suggestions,
                confidence_score=confidence_score,
                analysis_notes=analysis_notes
            )
            
        except Exception as e:
            logger.error(f"Error analyzing CSV quality: {str(e)}")
            return CSVAnalysisResult(
                data_shape=[0, 0],
                column_names=[],
                quality_issues=[f"Analysis failed: {str(e)}"],
                suggestions=["Please check CSV format and try again"],
                confidence_score=0.0,
                analysis_notes=["Quality analysis failed"]
            )
    
    async def apply_csv_transformations(self, csv_data: str, transformations: List[str]) -> str:
        """
        Apply transformations directly to CSV data.
        
        Args:
            csv_data: Original CSV data
            transformations: List of transformation descriptions
            
        Returns:
            Transformed CSV data as string
        """
        try:
            df = self._parse_csv_string(csv_data)
            if df is None:
                return csv_data
            
            original_shape = df.shape
            applied_changes = []
            
            # Apply transformations in order
            for transformation in transformations:
                if "remove duplicate" in transformation.lower():
                    before_count = len(df)
                    df = df.drop_duplicates()
                    after_count = len(df)
                    if before_count != after_count:
                        applied_changes.append(f"Removed {before_count - after_count} duplicate rows")
                        
                elif "fill missing" in transformation.lower():
                    # Count missing values before
                    missing_before = df.isnull().sum().sum()
                    
                    # Fill missing values with appropriate strategies
                    for col in df.columns:
                        if df[col].isnull().any():
                            # For numeric columns, fill with median
                            if df[col].dtype in ['int64', 'float64']:
                                df[col] = df[col].fillna(df[col].median())
                            else:
                                # For text columns, fill with empty string or mode
                                mode_val = df[col].mode()
                                if len(mode_val) > 0 and pd.notna(mode_val.iloc[0]):
                                    df[col] = df[col].fillna(mode_val.iloc[0])
                                else:
                                    df[col] = df[col].fillna("")
                    
                    missing_after = df.isnull().sum().sum()
                    if missing_before != missing_after:
                        applied_changes.append(f"Filled {missing_before - missing_after} missing values")
                        
                elif "remove empty rows" in transformation.lower():
                    before_count = len(df)
                    df = df.dropna(how='all')
                    after_count = len(df)
                    if before_count != after_count:
                        applied_changes.append(f"Removed {before_count - after_count} empty rows")
                        
                elif "clean whitespace" in transformation.lower():
                    # Trim whitespace from string columns
                    for col in df.columns:
                        if df[col].dtype == 'object':
                            df[col] = df[col].astype(str).str.strip()
                    applied_changes.append("Cleaned whitespace from text columns")

                elif "standardize categorical" in transformation.lower() or "standardize" in transformation.lower():
                    # Standardize string columns: convert all categorical/text columns to lowercase
                    for col in df.select_dtypes(include=['object']).columns:
                        df[col] = df[col].astype(str).str.strip().str.lower()
                    applied_changes.append("Standardized categorical text values to lowercase")

                elif "handle outlier" in transformation.lower() or "outlier" in transformation.lower():
                    # Remove rows with numeric outliers using 3*std rule
                    numeric_cols = df.select_dtypes(include=['number']).columns
                    before_count = len(df)
                    for col in numeric_cols:
                        col_mean = df[col].mean()
                        col_std = df[col].std()
                        df = df[(df[col] >= col_mean - 3 * col_std) & (df[col] <= col_mean + 3 * col_std)]
                    after_count = len(df)
                    if before_count != after_count:
                        applied_changes.append(f"Removed {before_count - after_count} outlier rows")
            
            # Log transformation results
            new_shape = df.shape
            logger.info(f"Applied {len(transformations)} transformations. Shape: {original_shape} → {new_shape}")
            logger.info(f"Changes applied: {applied_changes}")
            
            # Convert back to CSV string
            return self._dataframe_to_csv_string(df)
            
        except Exception as e:
            logger.error(f"Error applying transformations: {str(e)}")
            return csv_data
    
    def _parse_csv_string(self, csv_data: str) -> Optional[pd.DataFrame]:
        """Parse CSV string to DataFrame."""
        try:
            # Try different parsing options
            for separator in [',', ';', '\t']:
                try:
                    df = pd.read_csv(io.StringIO(csv_data), sep=separator)
                    if len(df.columns) > 1:  # Multiple columns indicate success
                        return df
                except:
                    continue
            
            # Fallback to comma separator
            return pd.read_csv(io.StringIO(csv_data))
            
        except Exception as e:
            logger.error(f"Error parsing CSV: {str(e)}")
            return None
    
    def _dataframe_to_csv_string(self, df: pd.DataFrame) -> str:
        """Convert DataFrame to CSV string."""
        try:
            return df.to_csv(index=False)
        except Exception as e:
            logger.error(f"Error converting DataFrame to CSV: {str(e)}")
            return ""
    
    def _get_or_create_session_state(self, request: CSVMessageRequest, df: pd.DataFrame) -> CSVConversationState:
        """Get or create session state."""
        if request.session_id not in self.session_states:
            self.session_states[request.session_id] = CSVConversationState(
                session_id=request.session_id,
                user_id=request.user_id,
                original_csv=request.csv_data,
                current_csv=request.csv_data,
                user_message=request.user_message
            )
        return self.session_states[request.session_id]
    
    def _calculate_confidence_score(self, df: pd.DataFrame, quality_issues: List[str]) -> float:
        """Calculate confidence score based on data quality."""
        if df.empty:
            return 0.0
        
        # Base score
        score = 1.0
        
        # Penalize for issues
        score -= len(quality_issues) * 0.1
        
        # Penalize for missing data
        missing_ratio = df.isnull().sum().sum() / (len(df) * len(df.columns))
        score -= missing_ratio * 0.5
        
        # Ensure score is between 0 and 1
        return max(0.0, min(1.0, score))
    
    async def _generate_greeting_response(self, df: pd.DataFrame, analysis: CSVAnalysisResult) -> str:
        """Generate greeting response with data overview."""
        rows, cols = analysis.data_shape
        
        response = f"Hello! I can see you have a dataset with {rows} rows and {cols} columns."
        
        if analysis.quality_issues:
            response += f"\n\nI've identified {len(analysis.quality_issues)} potential issues:"
            for issue in analysis.quality_issues[:3]:  # Show first 3 issues
                response += f"\n• {issue}"
        
        if analysis.suggestions:
            response += f"\n\nI can help you with:"
            for suggestion in analysis.suggestions[:3]:  # Show first 3 suggestions
                response += f"\n• {suggestion}"
        
        response += "\n\nWhat would you like to do with your data?"
        
        return response
    
    async def _generate_processing_response(self, user_message: str, df: pd.DataFrame, analysis: CSVAnalysisResult) -> str:
        """Generate processing response based on user message."""
        # Simple intent detection
        if "clean" in user_message.lower():
            return "I can help clean your data. Let me know what specific issues you'd like to address."
        elif "missing" in user_message.lower() or "null" in user_message.lower():
            return "I can help you handle missing values. Would you like me to fill them or remove rows with missing data?"
        elif "duplicate" in user_message.lower():
            return "I can help remove duplicate rows. Shall I proceed with removing duplicates?"
        else:
            return "I'm here to help with your data cleaning needs. What would you like me to do?" 