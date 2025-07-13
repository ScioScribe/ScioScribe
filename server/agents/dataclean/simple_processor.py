"""
Simple Data Processor for ScioScribe with LLM Integration

This module provides a simplified data processing service with 5 core tools,
each enhanced with LLM capabilities for intelligent processing:
- Analyze: LLM identifies data quality issues
- Clean: LLM determines best cleaning strategies  
- Describe: LLM provides intelligent insights
- Add Row: LLM understands natural language instructions
- Delete Row: LLM interprets deletion criteria
"""

import pandas as pd
import numpy as np
from io import StringIO
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime
import os
import re
from openai import AsyncOpenAI
import json

logger = logging.getLogger(__name__)


class SimpleDataProcessor:
    """
    Simplified data processor with 5 core LLM-enhanced tools.
    Uses GPT-4o-mini for fast, intelligent operations.
    """
    
    def __init__(self):
        """Initialize the processor with tool mapping and LLM client."""
        self.tools = {
            'analyze': self.analyze_data,
            'clean': self.clean_data,
            'describe': self.describe_data,
            'add_row': self.add_row,
            'delete_row': self.delete_row
        }
        
        # Initialize OpenAI client
        api_key = os.getenv('OPENAI_API_KEY')
        logger.info(f"Checking for OpenAI API key... {'Found' if api_key else 'Not found'}")
        if api_key:
            logger.info(f"API key starts with: {api_key[:10]}...")
            self.llm = AsyncOpenAI(api_key=api_key)
            self.model = "gpt-4o-mini"  # Fast, lightweight model
            logger.info("✅ LLM initialized with GPT-4o-mini")
        else:
            self.llm = None
            logger.warning("❌ No OpenAI API key found - running without LLM")
    
    async def process(self, action: str, csv_data: str, experiment_id: Optional[str] = None, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Main entry point - routes to appropriate tool.
        
        Args:
            action: One of 'analyze', 'clean', 'describe', 'add_row', 'delete_row'
            csv_data: CSV string data
            experiment_id: Optional experiment ID for context
            params: Optional parameters for the action
            
        Returns:
            Dict with results including csv_data, changes, analysis, ai_message
        """
        try:
            # Validate action
            if action not in self.tools:
                raise ValueError(f"Unknown action: {action}. Valid actions: {list(self.tools.keys())}")
            
            # Load context if experiment_id provided
            context = await self.load_context(experiment_id) if experiment_id else {}
            
            # Route to tool
            tool = self.tools[action]
            result = await tool(csv_data, params or {}, context)
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing {action}: {str(e)}")
            raise
    
    async def load_context(self, experiment_id: str) -> Dict[str, Any]:
        """Load context from experiment plan."""
        return {'experiment_id': experiment_id}
    
    async def analyze_data(self, csv_data: str, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze data for quality issues using LLM intelligence.
        """
        try:
            df = pd.read_csv(StringIO(csv_data))
            
            # Basic statistical analysis
            missing_counts = df.isnull().sum().to_dict()
            duplicate_count = df.duplicated().sum()
            
            # Use LLM to analyze data quality
            if self.llm:
                # Prepare data summary for LLM
                data_summary = {
                    "shape": df.shape,
                    "columns": df.columns.tolist(),
                    "dtypes": df.dtypes.astype(str).to_dict(),
                    "missing_values": {k: v for k, v in missing_counts.items() if v > 0},
                    "duplicates": int(duplicate_count),
                    "sample_data": df.head(3).to_dict('records')
                }
                
                prompt = f"""Rate this data's readiness for analysis (Jupyter, data science tools).

Data Summary:
{json.dumps(data_summary, indent=2)}

QUALITY SCORE (0-100) based on analysis readiness:
- 90-100: Ready for analysis (clean, consistent)
- 70-89: Minor issues but usable
- 50-69: Some problems, needs cleaning
- 30-49: Major issues, significant cleaning needed
- 0-29: Poor quality, extensive work required

Only report OBVIOUS problems that would break analysis:
- Clear spelling errors or typos
- Inconsistent formats (dates, numbers)
- Impossible/extreme values
- Critical missing data

Be conservative. If data is mostly usable, score it higher.

Format:
"Quality Score: [X]/100

[List obvious issues OR say "Data looks clean"]"

Focus on what would actually cause problems in a data analysis workflow."""

                response = await self.llm.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=300
                )
                
                llm_analysis = response.choices[0].message.content
                
                # Extract LLM-generated quality score
                quality_score = 75  # Default fallback
                score_match = re.search(r'Quality Score:\s*(\d+)/100', llm_analysis)
                if score_match:
                    quality_score = int(score_match.group(1))
                
                # Parse issues from LLM response
                issues = []
                lines = llm_analysis.strip().split('\n')
                issue_count = 0
                
                for line in lines:
                    if line.strip() and line.strip().startswith('-') and 'fix' in line.lower():
                        # Extract issue description
                        clean_line = line.strip().lstrip('- ').strip()
                        
                        if clean_line and issue_count < 4:
                            issues.append({
                                'type': 'data_quality',
                                'description': clean_line,
                                'severity': 'medium' if quality_score > 60 else 'high',
                                'fix': 'Address as described'
                            })
                            issue_count += 1
                
                return {
                    'csv_data': csv_data,
                    'issues': issues[:6],  # Limit to most important issues
                    'total_issues': len(issues),
                    'data_quality_score': quality_score,
                    'ai_message': f"📊 **Data Quality Analysis**\n\n{llm_analysis}"
                }
            else:
                # Fallback without LLM
                return await self._analyze_data_basic(df, csv_data)
                
        except Exception as e:
            logger.error(f"Error analyzing data: {str(e)}")
            raise
    
    async def clean_data(self, csv_data: str, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply intelligent cleaning operations using LLM to identify and fix data issues.
        """
        try:
            df = pd.read_csv(StringIO(csv_data))
            original_shape = df.shape
            changes = []
            
            if self.llm:
                # Prepare sample data for LLM analysis
                sample_rows = df.head(10).to_dict('records')
                column_info = {col: df[col].dtype.name for col in df.columns}
                
                prompt = f"""Analyze this CSV data and identify specific data quality issues. Then provide exact corrections.

Column Types: {json.dumps(column_info)}

Sample Data (first 10 rows):
{json.dumps(sample_rows, indent=2)}

Identify and fix these issues:
1. Spelling errors in text values
2. Inconsistent formatting (capitalization, spacing)
3. Invalid data formats
4. Obvious typos or errors

For each issue found, provide the correction in this format:
CORRECTION: column_name: "old_value" -> "new_value"

Be specific and only suggest corrections for obvious errors. Focus on:
- Spelling mistakes
- Inconsistent capitalization
- Extra/missing spaces
- Clear data entry errors

Return your response as:
ISSUES_FOUND: Brief description of issues
CORRECTIONS:
CORRECTION: column_name: "old_value" -> "new_value"
CORRECTION: column_name: "old_value" -> "new_value"
END_CORRECTIONS"""

                response = await self.llm.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=500
                )
                
                llm_response = response.choices[0].message.content
                logger.info(f"LLM cleaning response: {llm_response}")
                
                # Parse LLM corrections and apply them
                corrections_applied = 0
                if "CORRECTIONS:" in llm_response and "END_CORRECTIONS" in llm_response:
                    corrections_section = llm_response.split("CORRECTIONS:")[1].split("END_CORRECTIONS")[0]
                    correction_lines = [line.strip() for line in corrections_section.split('\n') if line.strip().startswith('CORRECTION:')]
                    
                    for correction_line in correction_lines:
                        try:
                            # Parse: CORRECTION: column_name: "old_value" -> "new_value"
                            parts = correction_line.replace('CORRECTION:', '').strip()
                            if ':' in parts and '->' in parts:
                                column_part, value_part = parts.split(':', 1)
                                column_name = column_part.strip()
                                
                                if '->' in value_part:
                                    old_val, new_val = value_part.split('->', 1)
                                    old_value = old_val.strip().strip('"')
                                    new_value = new_val.strip().strip('"')
                                    
                                    # Apply correction if column exists
                                    if column_name in df.columns:
                                        mask = df[column_name].astype(str) == old_value
                                        if mask.any():
                                            df.loc[mask, column_name] = new_value
                                            corrections_applied += 1
                                            changes.append(f"Fixed '{old_value}' -> '{new_value}' in column '{column_name}'")
                                            logger.info(f"Applied correction: {column_name}: '{old_value}' -> '{new_value}'")
                        except Exception as correction_error:
                            logger.warning(f"Failed to parse correction: {correction_line}. Error: {correction_error}")
                            continue
                
                # Apply basic cleaning operations
                # 1. Remove duplicates
                before_dup = len(df)
                df = df.drop_duplicates()
                after_dup = len(df)
                if before_dup != after_dup:
                    changes.append(f"Removed {before_dup - after_dup} duplicate rows")
                
                # 2. Trim whitespace from text columns
                text_cols_cleaned = 0
                for col in df.select_dtypes(include=['object']).columns:
                    original_values = df[col].astype(str)
                    df[col] = df[col].astype(str).str.strip()
                    if not original_values.equals(df[col]):
                        text_cols_cleaned += 1
                
                if text_cols_cleaned > 0:
                    changes.append(f"Trimmed whitespace in {text_cols_cleaned} text columns")
                
                # 3. Fill missing values intelligently
                missing_filled = 0
                for col in df.columns:
                    if df[col].isnull().any():
                        missing_count = df[col].isnull().sum()
                        if df[col].dtype in ['int64', 'float64']:
                            df[col] = df[col].fillna(df[col].median())
                            changes.append(f"Filled {missing_count} missing values in '{col}' with median")
                        else:
                            mode = df[col].mode()
                            if len(mode) > 0:
                                df[col] = df[col].fillna(mode[0])
                                changes.append(f"Filled {missing_count} missing values in '{col}' with most common value")
                        missing_filled += 1
                
                cleaned_csv = df.to_csv(index=False)
                
                # Create summary message
                if corrections_applied > 0:
                    ai_message = f"🧹 **Data Cleaned Successfully!**\n\n✅ Applied {corrections_applied} LLM-identified corrections\n✅ {'. '.join(changes[:3])}"
                else:
                    ai_message = f"🧹 **Data Cleaned!**\n\n✅ {'. '.join(changes[:3]) if changes else 'Data appears clean - no major issues found'}"
                
                return {
                    'csv_data': cleaned_csv,
                    'changes': changes,
                    'rows_before': original_shape[0],
                    'rows_after': len(df),
                    'ai_message': ai_message
                }
            else:
                # Fallback basic cleaning
                return await self._clean_data_basic(df, csv_data, original_shape)
                
        except Exception as e:
            logger.error(f"Error cleaning data: {str(e)}")
            raise
    
    async def describe_data(self, csv_data: str, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Provide intelligent data insights using LLM.
        """
        try:
            df = pd.read_csv(StringIO(csv_data))
            
            # Basic stats
            basic_info = {
                'shape': {'rows': len(df), 'columns': len(df.columns)},
                'columns': list(df.columns),
                'memory_usage': f"{df.memory_usage(deep=True).sum() / 1024:.2f} KB"
            }
            
            if self.llm:
                # Prepare contextual data summary for qualitative description
                column_names = list(df.columns)
                sample_rows = df.head(3).to_dict('records')
                experiment_context = context.get('experiment_id', 'Unknown experiment')
                
                data_context = {
                    "columns": column_names,
                    "sample_data": sample_rows,
                    "total_records": len(df),
                    "experiment_context": experiment_context
                }
                
                prompt = f"""Brief a new researcher about this dataset. Focus on what the experiment studies and what the data represents.

Data Context:
{json.dumps(data_context, indent=2)}

First, identify the research domain in this format:
"Research Domain: [domain]"

Examples:
- Research Domain: Biology/Botany
- Research Domain: Human Resources
- Research Domain: Medical/Clinical
- Research Domain: Psychology
- Research Domain: Marketing/Business

Then answer in 2-3 short sentences:
1. What is this study examining?
2. What variables are being tracked?  
3. What insights can we gain?

Be conversational, not technical. Keep description under 60 words."""

                response = await self.llm.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.4,
                    max_tokens=200
                )
                
                contextual_description = response.choices[0].message.content
                
                return {
                    'csv_data': csv_data,
                    'description': basic_info,
                    'ai_message': f"📋 **Experiment Overview** ({len(df)} records)\n\n{contextual_description}"
                }
            else:
                # Basic description without LLM - simple domain detection
                columns_str = " ".join(basic_info['columns']).lower()
                
                # Simple domain detection based on column names
                if any(word in columns_str for word in ['patient', 'treatment', 'medical', 'clinical', 'health']):
                    domain = "Medical/Clinical"
                elif any(word in columns_str for word in ['employee', 'salary', 'hr', 'department', 'performance']):
                    domain = "Human Resources"
                elif any(word in columns_str for word in ['sepal', 'petal', 'species', 'genus', 'biological']):
                    domain = "Biology/Botany"
                elif any(word in columns_str for word in ['marketing', 'sales', 'revenue', 'customer', 'business']):
                    domain = "Marketing/Business"
                else:
                    domain = "Research/General"
                
                column_summary = ", ".join(basic_info['columns'][:5])
                if len(basic_info['columns']) > 5:
                    column_summary += f" and {len(basic_info['columns']) - 5} more"
                
                return {
                    'csv_data': csv_data,
                    'description': basic_info,
                    'ai_message': f"📋 **Experiment Overview** ({len(df)} records)\n\nResearch Domain: {domain}\n\nThis dataset contains {len(basic_info['columns'])} variables: {column_summary}. The data appears to be tracking {basic_info['columns'][0].replace('_', ' ')} and related measurements."
                }
                
        except Exception as e:
            logger.error(f"Error describing data: {str(e)}")
            raise
    
    async def add_row(self, csv_data: str, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a new row using LLM to understand natural language instructions.
        """
        try:
            df = pd.read_csv(StringIO(csv_data))
            original_rows = len(df)
            
            if self.llm and 'user_message' in params:
                # Use LLM to extract row data from natural language
                columns_info = {col: str(dtype) for col, dtype in df.dtypes.items()}
                sample_row = df.iloc[0].to_dict() if len(df) > 0 else {}
                
                prompt = f"""Extract row data from this instruction:
"{params['user_message']}"

Columns: {json.dumps(columns_info, indent=2)}
Sample row: {json.dumps(sample_row, indent=2)}

Return ONLY a JSON object with column names as keys and values to add.
Use appropriate data types. For missing columns, use null."""

                response = await self.llm.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=200
                )
                
                try:
                    # Extract JSON from response
                    content = response.choices[0].message.content
                    # Find JSON in response
                    import re
                    json_match = re.search(r'\{[^}]+\}', content, re.DOTALL)
                    if json_match:
                        row_data = json.loads(json_match.group())
                    else:
                        row_data = json.loads(content)
                except:
                    row_data = params.get('row_data', {})
            else:
                row_data = params.get('row_data', {})
            
            if not row_data:
                raise ValueError("Could not extract row data")
            
            # Create new row with defaults
            new_row = {}
            for col in df.columns:
                if col in row_data and row_data[col] is not None:
                    new_row[col] = row_data[col]
                else:
                    # Smart defaults
                    if df[col].dtype in ['int64', 'float64']:
                        new_row[col] = 0
                    else:
                        new_row[col] = ''
            
            # Add the row
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            new_csv = df.to_csv(index=False)
            
            return {
                'csv_data': new_csv,
                'changes': [f"Added 1 new row"],
                'rows_before': original_rows,
                'rows_after': len(df),
                'ai_message': f"✅ Added new row successfully! Dataset now has {len(df)} rows."
            }
            
        except Exception as e:
            logger.error(f"Error adding row: {str(e)}")
            raise
    
    async def delete_row(self, csv_data: str, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Delete rows using LLM to understand natural language criteria.
        """
        try:
            df = pd.read_csv(StringIO(csv_data))
            original_rows = len(df)
            
            if self.llm and 'user_message' in params:
                # Use LLM to extract deletion criteria
                columns_info = list(df.columns)
                sample_data = df.head(3).to_dict('records')
                
                prompt = f"""Extract deletion criteria from this instruction:
"{params['user_message']}"

Columns: {columns_info}
Sample data: {json.dumps(sample_data, indent=2)}

Return ONLY a JSON object with:
{{"column": "column_name", "value": "value_to_match"}}

Be precise with column names and values."""

                response = await self.llm.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=100
                )
                
                try:
                    content = response.choices[0].message.content
                    import re
                    json_match = re.search(r'\{[^}]+\}', content, re.DOTALL)
                    if json_match:
                        criteria = json.loads(json_match.group())
                        condition = {criteria['column']: criteria['value']}
                    else:
                        condition = json.loads(content)
                except:
                    condition = params.get('condition', {})
            else:
                condition = params.get('condition', {})
            
            if not condition:
                raise ValueError("No deletion criteria provided")
            
            # Build mask for deletion
            mask = pd.Series([True] * len(df))
            for col, value in condition.items():
                if col in df.columns:
                    mask = mask & (df[col] == value)
                else:
                    raise ValueError(f"Column '{col}' not found")
            
            rows_to_delete = mask.sum()
            df = df[~mask]
            
            new_csv = df.to_csv(index=False)
            
            return {
                'csv_data': new_csv,
                'changes': [f"Deleted {rows_to_delete} rows"],
                'rows_before': original_rows,
                'rows_after': len(df),
                'ai_message': f"✅ Deleted {rows_to_delete} row(s). {len(df)} rows remaining."
            }
            
        except Exception as e:
            logger.error(f"Error deleting rows: {str(e)}")
            raise
    
    # Fallback methods for non-LLM operation
    async def _analyze_data_basic(self, df: pd.DataFrame, csv_data: str) -> Dict[str, Any]:
        """Basic analysis without LLM."""
        issues = []
        
        # Check for missing values
        missing = df.isnull().sum()
        for col, count in missing.items():
            if count > 0:
                percentage = (count / len(df)) * 100
                issues.append({
                    'type': 'missing_values',
                    'column': str(col),
                    'count': int(count),
                    'percentage': round(percentage, 2),
                    'severity': 'high' if percentage > 20 else 'medium',
                    'fix': f'Fill or remove missing values in column "{col}"'
                })
        
        # Check for duplicates
        dup_count = df.duplicated().sum()
        if dup_count > 0:
            issues.append({
                'type': 'duplicate_rows',
                'count': int(dup_count),
                'severity': 'medium',
                'fix': 'Remove duplicate rows'
            })
        
        quality_score = max(0, 100 - (len(issues) * 10))
        
        return {
            'csv_data': csv_data,
            'issues': issues,
            'total_issues': len(issues),
            'data_quality_score': quality_score,
            'ai_message': f"📊 Found {len(issues)} issues (Quality Score: {quality_score}/100)"
        }
    
    async def _clean_data_basic(self, df: pd.DataFrame, csv_data: str, original_shape: tuple) -> Dict[str, Any]:
        """Basic cleaning without LLM."""
        changes = []
        
        # Remove duplicates
        before = len(df)
        df = df.drop_duplicates()
        if before != len(df):
            changes.append(f"Removed {before - len(df)} duplicate rows")
        
        # Fill missing values
        for col in df.columns:
            if df[col].isnull().any():
                if df[col].dtype in ['int64', 'float64']:
                    df[col] = df[col].fillna(df[col].median())
                else:
                    df[col] = df[col].fillna('')
                changes.append(f"Filled missing values in '{col}'")
        
        cleaned_csv = df.to_csv(index=False)
        
        return {
            'csv_data': cleaned_csv,
            'changes': changes[:5],  # Limit changes shown
            'rows_before': original_shape[0],
            'rows_after': len(df),
            'ai_message': f"🧹 Data cleaned! {'. '.join(changes[:3])}"
        } 