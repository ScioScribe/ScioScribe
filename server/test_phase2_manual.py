"""
Manual Test for Phase 2: AI-Powered Data Cleaning Agent

This script manually tests the complete AI workflow including:
- File processing (Phase 1)
- AI quality analysis (Phase 2)
- Suggestion generation (Phase 2)
- Quality scoring (Phase 2)
"""

import asyncio
import pandas as pd
import os
import tempfile
from pathlib import Path
import json

from agents.dataclean.file_processor import FileProcessingAgent
from agents.dataclean.quality_agent import DataQualityAgent
from config import get_openai_client, validate_openai_config


async def test_file_processing():
    """Test basic file processing (Phase 1 functionality)."""
    print("=" * 60)
    print("📁 PHASE 1 TEST: File Processing")
    print("=" * 60)
    
    # Create sample CSV data with quality issues
    sample_data = {
        'Name': ['John Doe', 'Jane Smith', 'Bob Johnson', None, 'Alice Brown'],
        'Age': ['25', '30', 'thirty-five', '28', '22'],  # Mixed types - data quality issue
        'Email': ['john@email.com', 'jane.smith@company.co', 'bob@email', 'alice@email.com', ''],
        'Salary': [50000, 60000, 70000, 55000, 999999],  # Contains outlier
        'Department': ['Engineering', 'marketing', 'Sales', 'HR', 'ENGINEERING'],  # Inconsistent case
        'Status': ['Active', 'active', 'INACTIVE', 'Active', 'pending']  # Inconsistent values
    }
    
    df = pd.DataFrame(sample_data)
    
    # Create temporary CSV file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        df.to_csv(f.name, index=False)
        temp_file_path = f.name
    
    try:
        # Initialize processor
        processor = FileProcessingAgent()
        
        # Process the file
        result = await processor.process_file(temp_file_path, 'text/csv')
        
        print(f"✅ File Processing Result: {result.success}")
        if result.success and result.data_preview:
            print(f"📊 Data Shape: {result.data_preview['shape']}")
            print(f"📋 Columns: {result.data_preview['columns']}")
            print(f"🔍 Column Types: {result.data_preview['column_types']}")
            print(f"❓ Null Counts: {result.data_preview['null_counts']}")
            print("\n📄 Sample Data:")
            for i, row in enumerate(result.data_preview['sample_rows'][:3], 1):
                print(f"   Row {i}: {row}")
            return df, result
        else:
            print(f"❌ Error: {result.error_message}")
            return None, None
            
    finally:
        # Clean up
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)


async def test_ai_quality_analysis(df):
    """Test AI-powered quality analysis (Phase 2 functionality)."""
    print("\n" + "=" * 60)
    print("🤖 PHASE 2 TEST: AI Quality Analysis")
    print("=" * 60)
    
    # Check OpenAI configuration
    if not validate_openai_config():
        print("⚠️  OpenAI not configured - skipping AI tests")
        print("   To enable AI features:")
        print("   1. Get API key from: https://platform.openai.com/api-keys")
        print("   2. Set in .env file: OPENAI_API_KEY=sk-your-key-here")
        return None, None
    
    print("✅ OpenAI configured and ready")
    
    # Get OpenAI client and create quality agent
    client = get_openai_client()
    quality_agent = DataQualityAgent(client)
    
    try:
        print("🔍 Starting AI data quality analysis...")
        
        # Step 1: Analyze data quality issues
        quality_issues = await quality_agent.analyze_data(df)
        
        print(f"\n📋 Quality Issues Found: {len(quality_issues)}")
        for i, issue in enumerate(quality_issues, 1):
            print(f"   {i}. Column '{issue.column}' ({issue.severity}): {issue.description}")
            print(f"      → Affects {issue.affected_rows} rows")
        
        # Step 2: Generate AI suggestions
        if quality_issues:
            print(f"\n💡 Generating AI suggestions...")
            suggestions = await quality_agent.generate_suggestions(quality_issues, df)
            
            print(f"\n🎯 AI Suggestions Generated: {len(suggestions)}")
            for i, suggestion in enumerate(suggestions, 1):
                print(f"\n   Suggestion {i} - Column '{suggestion.column}':")
                print(f"   Action: {suggestion.description}")
                print(f"   Confidence: {suggestion.confidence:.2f} | Risk: {suggestion.risk_level}")
                print(f"   Explanation: {suggestion.explanation}")
        
        # Step 3: Calculate quality score
        total_rows = df.shape[0]
        total_issues = sum(issue.affected_rows for issue in quality_issues)
        quality_score = max(0.0, 1.0 - (total_issues / max(total_rows, 1)))
        
        print(f"\n📈 Overall Quality Score: {quality_score:.2f}/1.0")
        
        return quality_issues, suggestions
        
    except Exception as e:
        print(f"❌ AI Analysis Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None, None


async def test_complete_workflow():
    """Test the complete AI-powered data cleaning workflow."""
    print("\n" + "=" * 60)
    print("🔄 COMPLETE WORKFLOW TEST")
    print("=" * 60)
    
    print("This simulates the complete background processing workflow that happens")
    print("when a user uploads a file through the API...")
    
    # Step 1: File Processing
    df, file_result = await test_file_processing()
    if not df is not None:
        return
    
    # Step 2: AI Analysis (if OpenAI configured)
    issues, suggestions = await test_ai_quality_analysis(df)
    
    # Step 3: Summary
    print("\n" + "=" * 60)
    print("📊 WORKFLOW SUMMARY")
    print("=" * 60)
    
    print(f"✅ File Processing: SUCCESS")
    print(f"📊 Data Shape: {df.shape}")
    print(f"📋 Columns: {list(df.columns)}")
    
    if issues is not None:
        print(f"🤖 AI Analysis: SUCCESS")
        print(f"📋 Issues Found: {len(issues)}")
        print(f"💡 Suggestions Generated: {len(suggestions) if suggestions else 0}")
        
        # Calculate final score
        total_rows = df.shape[0]
        total_issues = sum(issue.affected_rows for issue in issues)
        quality_score = max(0.0, 1.0 - (total_issues / max(total_rows, 1)))
        print(f"📈 Quality Score: {quality_score:.2f}/1.0")
        
        # Show top 3 suggestions
        if suggestions and len(suggestions) > 0:
            print(f"\n🎯 Top 3 AI Recommendations:")
            for i, suggestion in enumerate(suggestions[:3], 1):
                print(f"   {i}. {suggestion.column}: {suggestion.description}")
                print(f"      Confidence: {suggestion.confidence:.2f}")
    else:
        print(f"⚠️  AI Analysis: SKIPPED (OpenAI not configured)")
        print(f"📈 Quality Score: Not calculated (requires AI)")


async def test_api_simulation():
    """Simulate what happens in the API background processing."""
    print("\n" + "=" * 60)
    print("🌐 API SIMULATION TEST")
    print("=" * 60)
    
    print("This simulates the exact process that happens in the FastAPI")
    print("background task when processing uploaded files...")
    
    # Simulate the process_file_background function
    artifact_id = "test-artifact-123"
    
    print(f"\n🔄 Processing artifact: {artifact_id}")
    
    # This mirrors the actual API workflow
    try:
        # Create sample data (like uploaded file)
        sample_data = {
            'Product': ['Widget A', 'Widget B', 'Widget C'],
            'Price': ['19.99', '29.99', 'invalid'],  # Price as string with invalid value
            'Stock': ['100', '150', '200'],  # Numbers as strings
            'Category': ['electronics', 'Home & Garden', 'ELECTRONICS']  # Inconsistent case
        }
        df = pd.DataFrame(sample_data)
        
        print("✅ File processing completed")
        print(f"📊 Data shape: {df.shape}")
        
        # AI analysis (if available)
        if validate_openai_config():
            client = get_openai_client()
            quality_agent = DataQualityAgent(client)
            
            print("🤖 Starting AI quality analysis...")
            quality_issues = await quality_agent.analyze_data(df)
            suggestions = await quality_agent.generate_suggestions(quality_issues, df)
            
            # Calculate quality score
            total_rows = df.shape[0]
            total_issues = sum(issue.affected_rows for issue in quality_issues)
            quality_score = max(0.0, 1.0 - (total_issues / max(total_rows, 1)))
            
            print(f"✅ AI analysis completed")
            print(f"📋 Issues found: {len(quality_issues)}")
            print(f"💡 Suggestions generated: {len(suggestions)}")
            print(f"📈 Quality score: {quality_score:.2f}")
            
            # This would be saved to the DataArtifact in real API
            print(f"💾 Status: PENDING_REVIEW (ready for user)")
            
        else:
            print("⚠️  OpenAI not configured - basic processing only")
            print(f"💾 Status: PENDING_REVIEW (no AI suggestions)")
            
    except Exception as e:
        print(f"❌ Processing failed: {str(e)}")


async def main():
    """Run all manual tests."""
    print("🧪 ScioScribe Phase 2 Manual Testing")
    print("Testing AI-Powered Data Cleaning Agent")
    
    # Test individual components
    await test_complete_workflow()
    
    # Test API simulation
    await test_api_simulation()
    
    print("\n" + "=" * 60)
    print("✅ ALL MANUAL TESTS COMPLETED")
    print("=" * 60)
    
    print("\n🎯 Next Steps:")
    print("1. Start the FastAPI server: uvicorn main:app --reload")
    print("2. Visit API docs: http://localhost:8000/docs")
    print("3. Test file upload through the web interface")
    print("4. Check the AI suggestions in the response")


if __name__ == "__main__":
    asyncio.run(main()) 