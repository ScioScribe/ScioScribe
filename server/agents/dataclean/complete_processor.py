"""
Complete File Processor for end-to-end data cleaning workflow.

This module provides a single orchestrated workflow that handles:
1. File upload and processing
2. AI quality analysis  
3. Suggestion generation
4. Automatic suggestion application
5. Final data export

This combines all existing agents into a streamlined single-call workflow.
"""

import os
import uuid
import tempfile
import time
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import logging
from pathlib import Path

from .models import (
    ProcessFileCompleteRequest,
    ProcessFileCompleteResponse,
    ProcessingSummary,
    DataArtifact,
    ProcessingStatus,
    FileMetadata,
    Suggestion,
    QualityIssue
)
from .file_processor import FileProcessingAgent
from .quality_agent import DataQualityAgent
from .suggestion_converter import SuggestionConverter
from .transformation_engine import TransformationEngine
from .memory_store import get_data_store

logger = logging.getLogger(__name__)


class CompleteFileProcessor:
    """
    Orchestrates the complete file processing workflow in a single operation.
    
    This class coordinates all the existing agents to provide a seamless
    end-to-end data cleaning experience.
    """
    
    def __init__(self, openai_client=None):
        """
        Initialize the complete file processor.
        
        Args:
            openai_client: Optional OpenAI client for AI features
        """
        self.data_store = get_data_store()
        self.file_processor = FileProcessingAgent()
        self.quality_agent = DataQualityAgent(openai_client) if openai_client else None
        self.suggestion_converter = SuggestionConverter()
        self.transformation_engine = TransformationEngine()
        
        logger.info("CompleteFileProcessor initialized")
    
    async def process_file_complete(
        self,
        file_path: str,
        filename: str,
        file_size: int,
        mime_type: str,
        request: ProcessFileCompleteRequest
    ) -> ProcessFileCompleteResponse:
        """
        Process a file completely from upload to cleaned JSON data.
        
        Args:
            file_path: Path to the uploaded file
            filename: Original filename
            file_size: File size in bytes
            mime_type: MIME type of the file
            request: Processing configuration
            
        Returns:
            ProcessFileCompleteResponse with cleaned data and processing summary
        """
        start_time = time.time()
        processing_summary = ProcessingSummary(
            file_processing={},
            quality_analysis={},
            suggestions_generated=0,
            suggestions_applied=0,
            suggestions_skipped=0,
            transformations_performed=[],
            processing_time_seconds=0.0
        )
        
        artifact_id = str(uuid.uuid4())
        warnings = []
        
        try:
            logger.info(f"Starting complete file processing for {filename}")
            
            # Step 1: Create artifact and process file
            artifact, df = await self._process_file_step(
                file_path, filename, file_size, mime_type, 
                artifact_id, request, processing_summary
            )
            
            if df is None or df.empty:
                return ProcessFileCompleteResponse(
                    success=False,
                    artifact_id=artifact_id,
                    cleaned_data=[],
                    data_shape=[0, 0],
                    column_names=[],
                    processing_summary=processing_summary,
                    error_message="No data extracted from file",
                    warnings=warnings,
                    metadata={"original_filename": filename}
                )
            
            # Step 2: AI Quality Analysis
            suggestions = await self._quality_analysis_step(
                df, artifact, processing_summary
            )
            
            # Step 3: Apply suggestions automatically (if enabled)
            final_df = df.copy()
            if request.auto_apply_suggestions and suggestions:
                final_df = await self._apply_suggestions_step(
                    final_df, suggestions, artifact_id, request, 
                    processing_summary, warnings
                )
            
            # Step 4: Save final data and prepare response
            await self.data_store.save_dataframe(artifact_id, final_df)
            
            # Calculate final processing time
            processing_summary.processing_time_seconds = time.time() - start_time
            
            # Prepare cleaned data for response
            cleaned_data = self._prepare_cleaned_data(final_df)
            
            # Get unapplied suggestions
            unapplied_suggestions = []
            if not request.auto_apply_suggestions:
                unapplied_suggestions = suggestions
            else:
                # Only suggestions that weren't applied due to filters
                unapplied_suggestions = [
                    s for s in suggestions 
                    if s.confidence < request.confidence_threshold
                ]
            
            # Update final artifact status
            artifact.status = ProcessingStatus.READY_FOR_ANALYSIS
            artifact.updated_at = datetime.now()
            await self.data_store.update_data_artifact(artifact)
            
            logger.info(f"Complete file processing finished for {filename}")
            
            return ProcessFileCompleteResponse(
                success=True,
                artifact_id=artifact_id,
                cleaned_data=cleaned_data,
                data_shape=[final_df.shape[0], final_df.shape[1]],
                column_names=list(final_df.columns),
                processing_summary=processing_summary,
                unapplied_suggestions=unapplied_suggestions,
                warnings=warnings,
                metadata={
                    "original_filename": filename,
                    "file_size": file_size,
                    "mime_type": mime_type,
                    "processing_date": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Complete file processing failed: {str(e)}")
            processing_summary.processing_time_seconds = time.time() - start_time
            
            return ProcessFileCompleteResponse(
                success=False,
                artifact_id=artifact_id,
                cleaned_data=[],
                data_shape=[0, 0],
                column_names=[],
                processing_summary=processing_summary,
                error_message=f"Processing failed: {str(e)}",
                warnings=warnings,
                metadata={"original_filename": filename}
            )
        
        finally:
            # Cleanup temporary file
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logger.info(f"Cleaned up temporary file: {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup temporary file: {str(e)}")
    
    async def _process_file_step(
        self,
        file_path: str,
        filename: str,
        file_size: int,
        mime_type: str,
        artifact_id: str,
        request: ProcessFileCompleteRequest,
        processing_summary: ProcessingSummary
    ) -> Tuple[DataArtifact, Optional[pd.DataFrame]]:
        """Process the uploaded file and create artifact."""
        logger.info("Step 1: Processing file")
        
        # Process the file
        result = await self.file_processor.process_file(file_path, mime_type)
        
        # Create file metadata
        file_metadata = FileMetadata(
            name=filename,
            path=file_path,
            size=file_size,
            mime_type=mime_type,
            uploaded_at=datetime.now()
        )
        
        # Create data artifact
        artifact = DataArtifact(
            artifact_id=artifact_id,
            experiment_id=request.experiment_id,
            owner_id=request.user_id,
            status=ProcessingStatus.PROCESSING,
            original_file=file_metadata,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Store artifact
        await self.data_store.save_data_artifact(artifact)
        
        # Extract DataFrame
        df = None
        if result.success and result.data_preview:
            # Load full DataFrame
            try:
                if file_path.endswith('.csv'):
                    df = pd.read_csv(file_path)
                elif file_path.endswith(('.xlsx', '.xls')):
                    df = pd.read_excel(file_path)
                else:
                    # Fallback to sample data
                    df = pd.DataFrame(result.data_preview['sample_rows'])
                
                # Store DataFrame
                await self.data_store.save_dataframe(artifact_id, df)
                logger.info(f"DataFrame loaded: {df.shape}")
                
            except Exception as e:
                logger.error(f"Failed to load DataFrame: {str(e)}")
                df = None
        
        # Update processing summary
        processing_summary.file_processing = {
            "success": result.success,
            "rows_extracted": df.shape[0] if df is not None else 0,
            "columns_extracted": df.shape[1] if df is not None else 0,
            "file_type": mime_type,
            "error_message": result.error_message
        }
        
        return artifact, df
    
    async def _quality_analysis_step(
        self,
        df: pd.DataFrame,
        artifact: DataArtifact,
        processing_summary: ProcessingSummary
    ) -> List[Suggestion]:
        """Perform AI quality analysis and generate suggestions."""
        logger.info("Step 2: AI Quality Analysis")
        
        suggestions = []
        
        if self.quality_agent:
            try:
                # Analyze data quality
                quality_issues = await self.quality_agent.analyze_data(df)
                logger.info(f"Found {len(quality_issues)} quality issues")
                
                # Generate suggestions
                suggestions = await self.quality_agent.generate_suggestions(quality_issues, df)
                logger.info(f"Generated {len(suggestions)} suggestions")
                
                # Update artifact
                artifact.suggestions = suggestions
                
                # Calculate quality score
                quality_score = self._calculate_quality_score(quality_issues, df)
                artifact.quality_score = quality_score
                processing_summary.quality_score_before = quality_score
                
                await self.data_store.update_data_artifact(artifact)
                
            except Exception as e:
                logger.error(f"AI quality analysis failed: {str(e)}")
                # Continue without AI analysis
        
        else:
            logger.warning("No OpenAI client available - skipping AI analysis")
        
        # Update processing summary
        processing_summary.quality_analysis = {
            "ai_analysis_enabled": self.quality_agent is not None,
            "quality_issues_found": len(quality_issues) if 'quality_issues' in locals() else 0,
            "quality_score": processing_summary.quality_score_before or 0.0
        }
        processing_summary.suggestions_generated = len(suggestions)
        
        return suggestions
    
    async def _apply_suggestions_step(
        self,
        df: pd.DataFrame,
        suggestions: List[Suggestion],
        artifact_id: str,
        request: ProcessFileCompleteRequest,
        processing_summary: ProcessingSummary,
        warnings: List[str]
    ) -> pd.DataFrame:
        """Apply AI suggestions automatically based on configuration."""
        logger.info("Step 3: Applying suggestions automatically")
        
        current_df = df.copy()
        applied_count = 0
        skipped_count = 0
        transformations_performed = []
        
        # Filter suggestions based on configuration
        applicable_suggestions = [
            s for s in suggestions
            if s.confidence >= request.confidence_threshold
        ]
        
        # Limit number of suggestions to apply
        if len(applicable_suggestions) > request.max_suggestions_to_apply:
            applicable_suggestions = applicable_suggestions[:request.max_suggestions_to_apply]
            warnings.append(f"Limited to {request.max_suggestions_to_apply} suggestions")
        
        logger.info(f"Applying {len(applicable_suggestions)} suggestions")
        
        for suggestion in applicable_suggestions:
            try:
                # Convert suggestion to transformation
                transformation = await self.suggestion_converter.convert_suggestion_to_transformation(
                    suggestion, current_df, request.user_id
                )
                
                # Apply transformation
                transformed_df, data_version = await self.transformation_engine.apply_transformation(
                    current_df, transformation, artifact_id, request.user_id
                )
                
                current_df = transformed_df
                applied_count += 1
                transformations_performed.append(transformation.description)
                
                logger.info(f"Applied suggestion: {suggestion.description}")
                
            except Exception as e:
                logger.error(f"Failed to apply suggestion {suggestion.suggestion_id}: {str(e)}")
                skipped_count += 1
                warnings.append(f"Failed to apply suggestion: {suggestion.description}")
        
        # Update processing summary
        processing_summary.suggestions_applied = applied_count
        processing_summary.suggestions_skipped = skipped_count
        processing_summary.transformations_performed = transformations_performed
        
        # Calculate quality score after transformations
        if self.quality_agent:
            try:
                post_issues = await self.quality_agent.analyze_data(current_df)
                processing_summary.quality_score_after = self._calculate_quality_score(post_issues, current_df)
            except Exception as e:
                logger.error(f"Post-transformation quality analysis failed: {str(e)}")
        
        logger.info(f"Applied {applied_count} suggestions, skipped {skipped_count}")
        
        return current_df
    
    def _calculate_quality_score(self, issues: List[QualityIssue], df: pd.DataFrame) -> float:
        """Calculate a quality score based on issues found."""
        if not issues:
            return 1.0
        
        # Simple scoring: 0.05 penalty per issue, minimum 0.1
        num_issues = len(issues)
        quality_score = max(0.1, 1.0 - (num_issues * 0.05))
        return round(quality_score, 2)
    
    def _prepare_cleaned_data(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Prepare DataFrame for JSON response."""
        try:
            # Clean data for JSON serialization
            df_clean = df.copy()
            
            # Handle different data types appropriately
            for col in df_clean.columns:
                if df_clean[col].dtype == 'Int64':
                    # For integer columns, fill NaN with 0 or convert to string
                    df_clean[col] = df_clean[col].fillna(0)
                elif df_clean[col].dtype == 'Float64':
                    # For float columns, fill NaN with 0.0 or keep as NaN
                    df_clean[col] = df_clean[col].fillna(0.0)
                elif df_clean[col].dtype == 'object':
                    # For object columns, fill NaN with empty string
                    df_clean[col] = df_clean[col].fillna('')
                else:
                    # For other types, try to fill with appropriate default
                    try:
                        df_clean[col] = df_clean[col].fillna('')
                    except:
                        # If fillna('') fails, try with None
                        df_clean[col] = df_clean[col].fillna(None)
            
            # Convert to dictionary
            records = df_clean.to_dict(orient='records')
            
            # Clean up any remaining NaN/None values for JSON serialization
            cleaned_records = []
            for record in records:
                cleaned_record = {}
                for key, value in record.items():
                    if pd.isna(value) or value is None:
                        cleaned_record[key] = ''
                    else:
                        cleaned_record[key] = value
                cleaned_records.append(cleaned_record)
            
            return cleaned_records
            
        except Exception as e:
            logger.error(f"Failed to prepare cleaned data: {str(e)}")
            # Fallback: convert to string representation
            try:
                # Convert all columns to string first
                df_str = df.astype(str).fillna('')
                return df_str.to_dict(orient='records')
            except Exception as fallback_e:
                logger.error(f"Fallback also failed: {str(fallback_e)}")
                return [] 