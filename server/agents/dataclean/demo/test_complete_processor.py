#!/usr/bin/env python3
"""
Test script for the complete file processing endpoint.

This script demonstrates how to use the new process-file-complete endpoint
that handles the entire workflow in a single API call.
"""

import asyncio
import sys
import os
import requests
import json
from pathlib import Path

# Add the server directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from agents.dataclean.complete_processor import CompleteFileProcessor
from agents.dataclean.models import ProcessFileCompleteRequest
from config import get_openai_client


async def test_complete_processor_direct():
    """
    Test the CompleteFileProcessor directly (without API endpoint).
    """
    print("🧪 Testing Complete File Processor (Direct)")
    print("=" * 50)
    
    # Check if OpenAI is configured
    openai_client = get_openai_client()
    if not openai_client:
        print("❌ OpenAI API key not configured. Please set OPENAI_API_KEY environment variable.")
        return False
    
    # Get test file
    test_file = "sample_data_messy.csv"
    if not os.path.exists(test_file):
        print(f"❌ Test file not found: {test_file}")
        return False
    
    try:
        # Initialize processor
        processor = CompleteFileProcessor(openai_client)
        
        # Create request
        request = ProcessFileCompleteRequest(
            experiment_id="test-experiment",
            auto_apply_suggestions=True,
            max_suggestions_to_apply=5,
            confidence_threshold=0.6,
            include_processing_details=True,
            user_id="test-user"
        )
        
        # Get file info
        file_path = os.path.abspath(test_file)
        file_size = os.path.getsize(file_path)
        
        print(f"📁 Processing file: {test_file}")
        print(f"📊 File size: {file_size} bytes")
        print(f"⚙️  Auto-apply suggestions: {request.auto_apply_suggestions}")
        print(f"🎯 Confidence threshold: {request.confidence_threshold}")
        print(f"📈 Max suggestions: {request.max_suggestions_to_apply}")
        print()
        
        # Process file completely
        response = await processor.process_file_complete(
            file_path=file_path,
            filename=test_file,
            file_size=file_size,
            mime_type="text/csv",
            request=request
        )
        
        # Display results
        print("📊 PROCESSING RESULTS:")
        print("-" * 30)
        print(f"✅ Success: {response.success}")
        print(f"🆔 Artifact ID: {response.artifact_id}")
        print(f"📏 Data shape: {response.data_shape[0]} rows x {response.data_shape[1]} columns")
        print(f"🏷️  Columns: {', '.join(response.column_names)}")
        print()
        
        # Processing summary
        summary = response.processing_summary
        print("📋 PROCESSING SUMMARY:")
        print("-" * 30)
        print(f"⏱️  Processing time: {summary.processing_time_seconds:.2f} seconds")
        print(f"💡 Suggestions generated: {summary.suggestions_generated}")
        print(f"✅ Suggestions applied: {summary.suggestions_applied}")
        print(f"⏭️  Suggestions skipped: {summary.suggestions_skipped}")
        print(f"🔄 Transformations: {len(summary.transformations_performed)}")
        print()
        
        if summary.transformations_performed:
            print("🔄 TRANSFORMATIONS APPLIED:")
            for i, transformation in enumerate(summary.transformations_performed, 1):
                print(f"  {i}. {transformation}")
            print()
        
        # Quality scores
        if summary.quality_score_before is not None:
            print("📊 QUALITY SCORES:")
            print(f"  Before: {summary.quality_score_before:.2f}")
            if summary.quality_score_after is not None:
                print(f"  After:  {summary.quality_score_after:.2f}")
                improvement = summary.quality_score_after - summary.quality_score_before
                print(f"  Change: {improvement:+.2f}")
            print()
        
        # Unapplied suggestions
        if response.unapplied_suggestions:
            print("💡 UNAPPLIED SUGGESTIONS:")
            for suggestion in response.unapplied_suggestions:
                print(f"  • {suggestion.description} (confidence: {suggestion.confidence:.2f})")
            print()
        
        # Warnings
        if response.warnings:
            print("⚠️  WARNINGS:")
            for warning in response.warnings:
                print(f"  • {warning}")
            print()
        
        # Sample of cleaned data
        if response.cleaned_data:
            print("📄 CLEANED DATA SAMPLE (first 3 rows):")
            print("-" * 40)
            for i, row in enumerate(response.cleaned_data[:3]):
                print(f"Row {i + 1}: {row}")
            print()
        
        # Export cleaned data to JSON file
        output_file = "cleaned_data_complete.json"
        with open(output_file, 'w') as f:
            json.dump(response.cleaned_data, f, indent=2, default=str)
        print(f"💾 Cleaned data exported to: {output_file}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_api_endpoint():
    """
    Test the API endpoint (requires server to be running).
    """
    print("\n🌐 Testing API Endpoint")
    print("=" * 50)
    
    api_url = "http://localhost:8000/api/dataclean/process-file-complete"
    test_file = "sample_data_messy.csv"
    
    if not os.path.exists(test_file):
        print(f"❌ Test file not found: {test_file}")
        return False
    
    try:
        # Prepare request
        files = {
            'file': open(test_file, 'rb')
        }
        
        params = {
            'auto_apply_suggestions': True,
            'confidence_threshold': 0.6,
            'max_suggestions_to_apply': 5,
            'experiment_id': 'test-experiment',
            'user_id': 'test-user',
            'include_processing_details': True
        }
        
        print(f"📡 Making API request to: {api_url}")
        print(f"📁 File: {test_file}")
        print(f"⚙️  Parameters: {params}")
        print()
        
        # Make request
        response = requests.post(api_url, files=files, params=params, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ API request successful!")
            print(f"📊 Data shape: {result['data_shape']}")
            print(f"⏱️  Processing time: {result['processing_summary']['processing_time_seconds']:.2f}s")
            print(f"💡 Suggestions applied: {result['processing_summary']['suggestions_applied']}")
            
            # Save result
            with open("api_result.json", 'w') as f:
                json.dump(result, f, indent=2, default=str)
            print("💾 API result saved to: api_result.json")
            
            return True
        else:
            print(f"❌ API request failed: {response.status_code}")
            print(f"Error: {response.text}")
            return False
        
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed. Make sure the server is running:")
        print("   cd server && python main.py")
        return False
    except Exception as e:
        print(f"❌ API test failed: {str(e)}")
        return False
    finally:
        # Clean up
        if 'files' in locals():
            files['file'].close()


def print_usage_examples():
    """Print usage examples for the new endpoint."""
    print("\n📖 USAGE EXAMPLES:")
    print("=" * 50)
    
    print("1. CURL Example:")
    print("   curl -X POST http://localhost:8000/api/dataclean/process-file-complete \\")
    print("        -F 'file=@sample_data_messy.csv' \\")
    print("        -F 'auto_apply_suggestions=true' \\")
    print("        -F 'confidence_threshold=0.7' \\")
    print("        -F 'max_suggestions_to_apply=10'")
    print()
    
    print("2. Python requests example:")
    print("   import requests")
    print("   files = {'file': open('data.csv', 'rb')}")
    print("   params = {")
    print("       'auto_apply_suggestions': True,")
    print("       'confidence_threshold': 0.7,")
    print("       'max_suggestions_to_apply': 10")
    print("   }")
    print("   response = requests.post(url, files=files, params=params)")
    print("   cleaned_data = response.json()['cleaned_data']")
    print()
    
    print("3. JavaScript fetch example:")
    print("   const formData = new FormData();")
    print("   formData.append('file', fileInput.files[0]);")
    print("   formData.append('auto_apply_suggestions', 'true');")
    print("   formData.append('confidence_threshold', '0.7');")
    print("   ")
    print("   fetch('/api/dataclean/process-file-complete', {")
    print("       method: 'POST',")
    print("       body: formData")
    print("   }).then(response => response.json());")


def check_environment():
    """Check if environment is properly configured."""
    print("🔧 Environment Check:")
    print("-" * 30)
    
    # Check OpenAI API key
    api_key = os.getenv('OPENAI_API_KEY')
    if api_key:
        print("✅ OpenAI API key configured")
    else:
        print("❌ OpenAI API key not set")
        print("💡 Set it with: export OPENAI_API_KEY='your-key-here'")
        return False
    
    # Check test file
    test_file = "sample_data_messy.csv"
    if os.path.exists(test_file):
        print(f"✅ Test file found: {test_file}")
    else:
        print(f"❌ Test file not found: {test_file}")
        return False
    
    return True


async def main():
    """Main test function."""
    print("🧪 Complete File Processing Test")
    print("=" * 50)
    
    # Check environment
    if not check_environment():
        return
    
    print()
    
    # Test direct processor
    success = await test_complete_processor_direct()
    
    if success:
        print("\n✅ Direct processor test completed successfully!")
        
        # Test API endpoint
        print("\n" + "=" * 50)
        api_success = test_api_endpoint()
        
        if api_success:
            print("\n✅ API endpoint test completed successfully!")
        else:
            print("\n⚠️  API endpoint test failed (server might not be running)")
    
    # Print usage examples
    print_usage_examples()
    
    print("\n🎉 Testing completed!")


if __name__ == "__main__":
    asyncio.run(main()) 