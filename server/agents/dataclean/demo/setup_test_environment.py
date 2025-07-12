#!/usr/bin/env python3
"""
Setup script to prepare the test environment for data cleaning flow.
"""

import os
import sys
import subprocess
import json

def check_python_version():
    """Check if Python version is compatible."""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8 or higher is required")
        return False
    print(f"✅ Python {version.major}.{version.minor} detected")
    return True

def install_requirements():
    """Install required packages."""
    print("📦 Installing required packages...")
    
    try:
        # Install from requirements.txt
        if os.path.exists("requirements.txt"):
            subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                         check=True, capture_output=True)
        
        # Install additional packages that might be missing
        additional_packages = [
            "pandas>=1.5.0",
            "openai>=1.0.0", 
            "fastapi>=0.104.0",
            "pydantic>=2.0.0",
            "aiofiles>=23.0.0"
        ]
        
        for package in additional_packages:
            try:
                subprocess.run([sys.executable, "-m", "pip", "install", package], 
                             check=True, capture_output=True)
            except:
                print(f"⚠️  Could not install {package}")
        
        print("✅ Packages installed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Failed to install packages: {str(e)}")
        return False

def check_test_data():
    """Check and create test data if needed."""
    test_file = "sample_data_messy.csv"
    
    if os.path.exists(test_file):
        print(f"✅ Test file found: {test_file}")
        return True
    
    print(f"⚠️  Test file not found: {test_file}")
    print("📝 Creating sample test data...")
    
    # Create sample messy data
    import pandas as pd
    
    sample_data = {
        'Name': ['John Doe', 'Jane Smith', 'Bob Johnson', '', 'Charlie Brown', 'Mike Davis', 'Sarah Wilson'],
        'Age': [25, 30, 'thirty-five', 28, 22, 45, 'text'],
        'Email': ['john@email.com', 'jane.smith@company.co', 'bob@email', 'alice@email.com', '', 'mike@company.com', 'sarah@email'],
        'Salary': [50000, 60000, 70000, 55000, 999999, 75000, 65000],
        'Department': ['Engineering', 'marketing', 'Sales', 'HR', 'ENGINEERING', 'Marketing', 'engineering'],
        'Status': ['Active', 'active', 'INACTIVE', 'Active', 'pending', 'active', 'ACTIVE'],
        'Phone': ['555-0123', '555.0456', '555 0789', '555-0012', 'invalid-phone', '555-0345', '+1-555-0678']
    }
    
    df = pd.DataFrame(sample_data)
    df.to_csv(test_file, index=False)
    print(f"✅ Created test file: {test_file}")
    return True

def check_openai_key():
    """Check OpenAI API key."""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY not set")
        print("💡 Please set your OpenAI API key:")
        print("   For Unix/Linux/macOS:")
        print("     export OPENAI_API_KEY='your-api-key-here'")
        print("   For Windows:")
        print("     set OPENAI_API_KEY=your-api-key-here")
        print("")
        print("   Or create a .env file with:")
        print("     OPENAI_API_KEY=your-api-key-here")
        return False
    else:
        print("✅ OpenAI API key configured")
        return True

def create_env_file():
    """Create a sample .env file if it doesn't exist."""
    if not os.path.exists('.env'):
        env_content = """# ScioScribe Configuration
OPENAI_API_KEY=your-api-key-here
OPENAI_MODEL=gpt-4.1
DEBUG=true
"""
        with open('.env', 'w') as f:
            f.write(env_content)
        print("✅ Created .env file template")

def main():
    """Main setup function."""
    print("🔧 Setting up Data Cleaning Test Environment")
    print("=" * 50)
    
    success = True
    
    # Check Python version
    if not check_python_version():
        success = False
    
    # Install requirements
    if not install_requirements():
        success = False
    
    # Check test data
    if not check_test_data():
        success = False
    
    # Create env file template
    create_env_file()
    
    # Check OpenAI key
    if not check_openai_key():
        success = False
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 Setup completed successfully!")
        print("💡 Now you can run: python test_data_cleaning_flow.py")
    else:
        print("❌ Setup incomplete - please fix the issues above")
        sys.exit(1)

if __name__ == "__main__":
    main() 