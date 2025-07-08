"""
Barebones Text Interface for Testing Analysis Agent

This module provides a simple command-line interface for testing
the LangGraph-based visualization agent interactively.
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional

from dotenv import load_dotenv

# Add the parent directory to the path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from agents.analysis import (
    AnalysisAgent,
    create_analysis_agent,
    validate_environment,
    get_default_experiment_plan,
    get_default_dataset
)

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '..', '.env'))

class SimpleAnalysisTest:
    """Simple text-based interface for testing the analysis agent"""
    
    def __init__(self):
        """Initialize the test interface"""
        self.agent: Optional[AnalysisAgent] = None
        self.memory: Dict[str, Any] = {}
        self.experiment_plan_path: Optional[str] = None
        self.dataset_path: Optional[str] = None
        
    def initialize_agent(self) -> bool:
        """Initialize the analysis agent with environment validation"""
        try:
            print("🔧 Initializing Analysis Agent...")
            
            # Validate environment
            validation_result = validate_environment()
            if not validation_result["valid"]:
                print(f"❌ Environment validation failed:")
                for error in validation_result["errors"]:
                    print(f"  - {error}")
                return False
            
            # Show warnings if any
            if validation_result["warnings"]:
                for warning in validation_result["warnings"]:
                    print(f"⚠️  {warning}")
            
            print("✅ Environment validated successfully")
            
            # Create agent
            self.agent = create_analysis_agent()
            print("✅ Agent created successfully")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to initialize agent: {e}")
            return False
    
    def load_default_data(self) -> bool:
        """Load default experiment plan and dataset"""
        try:
            print("\n📁 Loading default data...")
            
            # Get default paths
            self.experiment_plan_path = get_default_experiment_plan()
            self.dataset_path = get_default_dataset()
            
            if not self.experiment_plan_path or not self.dataset_path:
                print("❌ Failed to get default data paths")
                return False
            
            # Check if files exist
            if not os.path.exists(self.experiment_plan_path):
                print(f"❌ Experiment plan not found: {self.experiment_plan_path}")
                return False
            
            if not os.path.exists(self.dataset_path):
                print(f"❌ Dataset not found: {self.dataset_path}")
                return False
            
            print(f"✅ Experiment plan: {os.path.basename(self.experiment_plan_path)}")
            print(f"✅ Dataset: {os.path.basename(self.dataset_path)}")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to load default data: {e}")
            return False
    
    def generate_visualization(self, user_query: str) -> Dict[str, Any]:
        """Generate visualization based on user query"""
        try:
            print(f"\n🤖 Processing query: {user_query}")
            print("⏳ Generating visualization...")
            
            # Call agent
            result = self.agent.generate_visualization(
                user_prompt=user_query,
                experiment_plan_path=self.experiment_plan_path,
                csv_file_path=self.dataset_path,
                memory=self.memory
            )
            
            # Update memory with result
            if "memory" in result:
                self.memory.update(result["memory"])
            
            return result
            
        except Exception as e:
            print(f"❌ Error generating visualization: {e}")
            return {"error": str(e)}
    
    def display_result(self, result: Dict[str, Any]):
        """Display the result of visualization generation"""
        if "error" in result:
            print(f"❌ Error: {result['error']}")
            return
        
        print("\n" + "="*60)
        print("📊 VISUALIZATION RESULT")
        print("="*60)
        
        # Show explanation
        if "explanation" in result and result["explanation"]:
            print("📝 Explanation:")
            print(result["explanation"])
            print()
        
        # Show chart info
        if "chart_specification" in result and result["chart_specification"]:
            chart_spec = result["chart_specification"]
            print("📈 Chart Details:")
            print(f"  Type: {chart_spec.get('chart_type', 'Unknown')}")
            print(f"  Title: {chart_spec.get('title', 'No title')}")
            print(f"  X-axis: {chart_spec.get('x_column', 'Unknown')} ({chart_spec.get('x_label', 'No label')})")
            print(f"  Y-axis: {chart_spec.get('y_column', 'Unknown')} ({chart_spec.get('y_label', 'No label')})")
            if chart_spec.get('hue_column'):
                print(f"  Color by: {chart_spec.get('hue_column')}")
            print()
        
        # Show plot path
        if "plot_image_path" in result and result["plot_image_path"]:
            print(f"💾 Plot saved to: {result['plot_image_path']}")
            print()
        
        # Show memory status
        if "memory" in result and result["memory"]:
            memory_items = len(result["memory"])
            print(f"🧠 Memory updated ({memory_items} items)")
        
        print("="*60)
    
    def run_conversation(self):
        """Run the interactive conversation loop"""
        print("\n🎯 ANALYSIS AGENT - TEXT INTERFACE")
        print("="*50)
        print("Type your analysis questions or 'quit' to exit.")
        print("Example queries:")
        print("  - 'Show me the distribution of sepal length'")
        print("  - 'Compare petal width across species'")
        print("  - 'Create a scatter plot of sepal length vs petal length'")
        print("="*50)
        
        while True:
            try:
                # Get user input
                user_input = input("\n💬 Your query: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("👋 Goodbye!")
                    break
                
                # Generate visualization
                result = self.generate_visualization(user_input)
                
                # Display result
                self.display_result(result)
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Unexpected error: {e}")
    
    def run(self):
        """Run the complete test interface"""
        print("🧬 IRIS ANALYSIS AGENT - BAREBONES TEST")
        print("="*60)
        
        # Initialize agent
        if not self.initialize_agent():
            return
        
        # Load default data
        if not self.load_default_data():
            return
        
        # Run conversation
        self.run_conversation()


def main():
    """Main function to run the test interface"""
    test = SimpleAnalysisTest()
    test.run()


if __name__ == "__main__":
    main() 