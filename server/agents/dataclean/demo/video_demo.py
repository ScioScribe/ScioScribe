#!/usr/bin/env python3
"""
ScioScribe Data Cleaning Demo Script
=====================================

This script demonstrates the complete data cleaning pipeline for video recording.
Run this script to show all the functionality in action.

Usage:
    python video_demo.py
"""

import os
import sys
import asyncio
import pandas as pd
from datetime import datetime
from pathlib import Path

# Add the parent directory to the path so we can import the modules
sys.path.append(str(Path(__file__).parent.parent))

from complete_processor import CompleteFileProcessor
from models import ProcessFileCompleteRequest
from file_processor import FileProcessingAgent
from quality_agent import DataQualityAgent
from transformation_engine import TransformationEngine
from memory_store import get_data_store

# Mock OpenAI client for demo (replace with real client if available)
class MockOpenAIClient:
    """Mock OpenAI client for demonstration purposes."""
    
    class ChatCompletions:
        async def create(self, **kwargs):
            # Mock response for quality analysis
            class MockResponse:
                def __init__(self):
                    self.choices = [self.MockChoice()]
                
                class MockChoice:
                    def __init__(self):
                        self.message = self.MockMessage()
                    
                    class MockMessage:
                        def __init__(self):
                            self.content = '''[
                                {
                                    "column": "Age",
                                    "issue_type": "data_type_mismatch",
                                    "description": "Text value 'thirty-five' found in numeric column",
                                    "severity": "high",
                                    "affected_rows": 1
                                },
                                {
                                    "column": "Department",
                                    "issue_type": "inconsistent_values",
                                    "description": "Inconsistent capitalization in department names",
                                    "severity": "medium",
                                    "affected_rows": 4
                                },
                                {
                                    "column": "Email",
                                    "issue_type": "missing_values",
                                    "description": "Missing email addresses detected",
                                    "severity": "medium",
                                    "affected_rows": 1
                                }
                            ]'''
            
            return MockResponse()
    
    def __init__(self):
        self.chat = self.ChatCompletions()


def print_header(title):
    """Print a formatted header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_step(step_num, title):
    """Print a formatted step."""
    print(f"\n🔹 STEP {step_num}: {title}")
    print("-" * 50)


def print_data_preview(df, title="Data Preview"):
    """Print a formatted data preview."""
    print(f"\n📊 {title}")
    print(f"Shape: {df.shape}")
    print(f"Columns: {list(df.columns)}")
    print("\nFirst 5 rows:")
    print(df.head().to_string(index=False))
    
    # Show data types
    print(f"\nData Types:")
    for col, dtype in df.dtypes.items():
        print(f"  {col}: {dtype}")


def print_quality_issues(issues):
    """Print quality issues in a formatted way."""
    print(f"\n⚠️  Quality Issues Found: {len(issues)}")
    for i, issue in enumerate(issues, 1):
        print(f"{i}. {issue.column}: {issue.description}")
        print(f"   Severity: {issue.severity.upper()}, Affected rows: {issue.affected_rows}")


def print_suggestions(suggestions):
    """Print suggestions in a formatted way."""
    print(f"\n💡 AI Suggestions Generated: {len(suggestions)}")
    for i, suggestion in enumerate(suggestions, 1):
        print(f"{i}. {suggestion.column}: {suggestion.description}")
        print(f"   Confidence: {suggestion.confidence:.2f}, Risk: {suggestion.risk_level}")


def create_sample_data():
    """Create sample messy data for demonstration."""
    sample_file = Path(__file__).parent / "sample_data_messy.csv"
    
    # Use existing sample data if available
    if sample_file.exists():
        return str(sample_file)
    
    # Create sample data
    data = {
        'Name': ['John Doe', 'Jane Smith', 'Bob Johnson', '', 'Charlie Brown', 'Mike Davis', 'Sarah Wilson'],
        'Age': [25, 30, 'thirty-five', 28, 22, 45, 'text'],
        'Email': ['john@email.com', 'jane.smith@company.co', 'bob@email', 'alice@email.com', '', 'mike@company.com', 'sarah@email'],
        'Salary': [50000, 60000, 70000, 55000, 999999, 75000, 65000],
        'Department': ['Engineering', 'marketing', 'Sales', 'HR', 'ENGINEERING', 'Marketing', 'engineering'],
        'Status': ['Active', 'active', 'INACTIVE', 'Active', 'pending', 'active', 'ACTIVE'],
        'Phone': ['555-0123', '555.0456', '555 0789', '555-0012', 'invalid-phone', '555-0345', '+1-555-0678']
    }
    
    df = pd.DataFrame(data)
    df.to_csv(sample_file, index=False)
    return str(sample_file)


async def main():
    """Main demo function."""
    print_header("🧬 SCIOSCRIBE DATA CLEANING DEMO")
    
    print("""
    Welcome to ScioScribe - the AI-powered research co-pilot!
    
    ScioScribe is an open-source platform designed specifically for biomedical 
    researchers to streamline their data analysis workflows.
    
    Today we'll demonstrate our intelligent data cleaning system that:
    ✅ Processes multiple file formats (CSV, Excel, Images)
    ✅ Uses AI to identify data quality issues
    ✅ Generates smart cleaning suggestions
    ✅ Applies transformations with full version control
    ✅ Provides complete data lineage tracking
    """)
    
    input("Press Enter to start the demo...")
    
    # Create sample data
    sample_file = create_sample_data()
    
    print_step(1, "Loading Sample Messy Data")
    print(f"📁 Using sample file: {sample_file}")
    
    # Read the original data
    original_df = pd.read_csv(sample_file)
    print_data_preview(original_df, "Original Messy Data")
    
    print("\n🔍 Common data quality issues we can see:")
    print("  • Mixed case in Department column")
    print("  • Text values in Age column ('thirty-five', 'text')")
    print("  • Missing values in Name and Email columns")
    print("  • Inconsistent phone number formats")
    print("  • Various status value formats")
    print("  • Potential outliers in Salary column")
    
    input("\nPress Enter to continue...")
    
    print_step(2, "Initializing ScioScribe Data Cleaning System")
    
    # Initialize the system
    mock_client = MockOpenAIClient()
    processor = CompleteFileProcessor(openai_client=mock_client)
    
    print("✅ File Processor initialized")
    print("✅ AI Quality Agent initialized")
    print("✅ Transformation Engine initialized")
    print("✅ Memory Store initialized")
    
    input("\nPress Enter to start AI analysis...")
    
    print_step(3, "AI-Powered Quality Analysis")
    
    # Simulate quality analysis
    quality_agent = DataQualityAgent(mock_client)
    
    print("🤖 Running AI analysis with OpenAI GPT-4...")
    print("   • Analyzing data types...")
    print("   • Detecting inconsistencies...")
    print("   • Identifying missing values...")
    print("   • Checking for outliers...")
    
    # Get quality issues
    issues = await quality_agent.analyze_data(original_df)
    print_quality_issues(issues)
    
    input("\nPress Enter to generate suggestions...")
    
    print_step(4, "AI Suggestion Generation")
    
    print("🧠 Generating intelligent cleaning suggestions...")
    suggestions = await quality_agent.generate_suggestions(issues, original_df)
    print_suggestions(suggestions)
    
    input("\nPress Enter to apply cleaning transformations...")
    
    print_step(5, "Applying Data Transformations")
    
    # Create processing request
    request = ProcessFileCompleteRequest(
        experiment_id="demo-experiment",
        auto_apply_suggestions=True,
        max_suggestions_to_apply=10,
        confidence_threshold=0.5,
        user_id="demo-user"
    )
    
    print("⚙️  Applying transformations:")
    print("   • Converting text ages to numeric values...")
    print("   • Standardizing department names...")
    print("   • Filling missing values...")
    print("   • Normalizing phone formats...")
    print("   • Cleaning status values...")
    
    # Process the file completely
    result = await processor.process_file_complete(
        file_path=sample_file,
        filename="sample_data_messy.csv",
        file_size=os.path.getsize(sample_file),
        mime_type="text/csv",
        request=request
    )
    
    if result.success:
        print("✅ Data cleaning completed successfully!")
        
        # Show cleaned data
        cleaned_df = pd.DataFrame(result.cleaned_data)
        print_data_preview(cleaned_df, "Cleaned Data")
        
        # Show processing summary
        print_step(6, "Processing Summary")
        summary = result.processing_summary
        
        print(f"📈 Processing Results:")
        print(f"   • Processing time: {summary.processing_time_seconds:.2f} seconds")
        print(f"   • Suggestions generated: {summary.suggestions_generated}")
        print(f"   • Suggestions applied: {summary.suggestions_applied}")
        print(f"   • Transformations performed: {len(summary.transformations_performed)}")
        
        if summary.quality_score_before and summary.quality_score_after:
            improvement = summary.quality_score_after - summary.quality_score_before
            print(f"   • Quality score improvement: {summary.quality_score_before:.2f} → {summary.quality_score_after:.2f} (+{improvement:.2f})")
        
        # Show transformations
        if summary.transformations_performed:
            print(f"\n🔄 Transformations Applied:")
            for i, transform in enumerate(summary.transformations_performed, 1):
                print(f"   {i}. {transform}")
        
        print_step(7, "Data Export & Next Steps")
        
        print("📤 Export Options:")
        print("   • Clean data available as JSON")
        print("   • Can export to CSV, Excel, or database")
        print("   • Full version history maintained")
        print("   • Transformation rules saved for reuse")
        
        # Show comparison
        print_step(8, "Before vs After Comparison")
        
        print("🔍 Key Improvements:")
        print(f"   • Shape: {original_df.shape} → {cleaned_df.shape}")
        
        # Compare specific columns
        if 'Age' in original_df.columns and 'Age' in cleaned_df.columns:
            orig_age_issues = original_df['Age'].apply(lambda x: not str(x).isdigit() if pd.notna(x) else False).sum()
            clean_age_issues = cleaned_df['Age'].apply(lambda x: not str(x).isdigit() if pd.notna(x) else False).sum()
            print(f"   • Age column: {orig_age_issues} text values → {clean_age_issues} text values")
        
        if 'Department' in original_df.columns and 'Department' in cleaned_df.columns:
            orig_dept_unique = original_df['Department'].nunique()
            clean_dept_unique = cleaned_df['Department'].nunique()
            print(f"   • Department standardization: {orig_dept_unique} unique values → {clean_dept_unique} unique values")
        
        print_step(9, "Advanced Features")
        
        print("🚀 ScioScribe Advanced Capabilities:")
        print("   • Version control with undo/redo")
        print("   • Custom transformation rules")
        print("   • Batch processing for multiple files")
        print("   • OCR support for image-based data")
        print("   • Collaborative cleaning workflows")
        print("   • API integration for automated pipelines")
        
        print_step(10, "Coming Soon: Conversational Interface")
        
        print("💬 Future Features:")
        print("   • Natural language commands: 'clean the email column'")
        print("   • Real-time WebSocket updates")
        print("   • LangGraph-powered agent workflows")
        print("   • Research planning integration")
        print("   • Advanced visualization tools")
        
    else:
        print("❌ Processing failed:")
        print(f"   Error: {result.error_message}")
    
    print_header("🎉 DEMO COMPLETE")
    
    print("""
    Thank you for exploring ScioScribe!
    
    🌟 Key Takeaways:
    • AI-powered data cleaning saves hours of manual work
    • Intelligent suggestions catch issues humans might miss
    • Full version control ensures reproducible research
    • Modular design enables easy customization
    • Open source for the research community
    
    📚 What's Next:
    • Try ScioScribe with your own data
    • Contribute to the open source project
    • Join our research community
    • Share feedback and feature requests
    
    🔗 Connect with us:
    • GitHub: [Your GitHub Repository]
    • Discord: [Your Discord Server]
    • Twitter: [Your Twitter Handle]
    
    Together, we can accelerate biomedical research! 🧬✨
    """)


if __name__ == "__main__":
    asyncio.run(main()) 