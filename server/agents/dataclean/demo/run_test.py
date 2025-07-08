#!/usr/bin/env python3
"""
Simple script to run the data cleaning flow test.
This script will handle setup and run the test in one command.
"""

import os
import sys
import subprocess
import asyncio

def main():
    print("🧪 ScioScribe Data Cleaning Flow Test")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not os.path.exists("agents"):
        print("❌ Please run this script from the server directory")
        print("   cd server && python run_test.py")
        sys.exit(1)
    
    # Check OpenAI API key
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ OpenAI API key not set")
        print("💡 Please set your OpenAI API key first:")
        print("   export OPENAI_API_KEY='your-api-key-here'")
        print("   Then run: python run_test.py")
        sys.exit(1)
    
    # Run the test
    print("🚀 Running data cleaning flow test...")
    print("-" * 50)
    
    try:
        # Import and run the test
        from test_data_cleaning_flow import main as test_main
        asyncio.run(test_main())
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Try running: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 