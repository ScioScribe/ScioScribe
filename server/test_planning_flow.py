#!/usr/bin/env python3
"""
End-to-end testing script for the experiment planning agent system.

This script provides a command-line interface to test the complete LangGraph
orchestration, allowing manual testing of the planning agent conversations.
"""

import sys
import os
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import json

# Add server directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from agents.planning import (
        create_planning_graph,
        PlanningGraphExecutor,
        start_new_experiment_planning,
        ExperimentPlanState,
        PLANNING_STAGES,
        get_planning_graph_info,
        setup_logging,
        get_global_debugger,
        test_llm_connection
    )
    from agents.planning.tools import StatisticalCalculator, StatisticalTestType
    from config import get_settings, validate_required_settings, initialize_logging
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running this script from the server directory")
    sys.exit(1)


class PlanningFlowTester:
    """
    Interactive tester for the planning agent system.
    
    Provides a command-line interface to test the complete LangGraph
    orchestration and agent interactions.
    """
    
    def __init__(self):
        """Initialize the flow tester."""
        self.settings = get_settings()
        self.executor: Optional[PlanningGraphExecutor] = None
        self.current_state: Optional[ExperimentPlanState] = None
        self.debugger = get_global_debugger()
        
        # Set up logging
        setup_logging(log_level=self.settings.log_level)
        self.logger = logging.getLogger("planning_flow_tester")
        
        # Initialize statistical calculator
        self.stats_calculator = StatisticalCalculator()
        
    def display_header(self) -> None:
        """Display the application header."""
        print("\n" + "="*70)
        print("🧪 SCIOSCRIBE PLANNING AGENT - END-TO-END TESTING")
        print("="*70)
        print("Testing complete LangGraph orchestration and agent interactions")
        print("="*70)
        
    def display_system_info(self) -> None:
        """Display system configuration information."""
        print("\n📋 SYSTEM CONFIGURATION:")
        print("-" * 40)
        
        # Get system info
        from config import get_system_info
        info = get_system_info()
        
        print(f"🔧 OpenAI Model: {info['openai_model']}")
        print(f"🌡️  Temperature: {info['openai_temperature']}")
        print(f"📝 Max Tokens: {info['openai_max_tokens']}")
        print(f"🔍 Debug Mode: {info['debug']}")
        print(f"📊 Log Level: {info['log_level']}")
        print(f"🔑 Has OpenAI Key: {'✅' if info['has_openai_key'] else '❌'}")
        print(f"🌐 Has Tavily Key: {'✅' if info['has_tavily_key'] else '❌'}")
        
        # Graph info
        graph_info = get_planning_graph_info()
        print(f"\n🔄 Graph Type: {graph_info['graph_type']}")
        print(f"📊 State Type: {graph_info['state_type']}")
        print(f"🤖 Agent Count: {graph_info['agent_count']}")
        print(f"⚡ Entry Point: {graph_info['entry_point']}")
        
    def validate_setup(self) -> bool:
        """Validate that the system is properly configured."""
        print("\n🔍 VALIDATING SETUP:")
        print("-" * 40)
        
        # Check required settings
        missing_settings = validate_required_settings()
        if missing_settings:
            print(f"❌ Missing required settings: {', '.join(missing_settings)}")
            return False
        
        print("✅ All required settings configured")
        
        # Test LLM connection
        print("🔗 Testing LLM connection...")
        llm_test = test_llm_connection()
        
        if llm_test['success']:
            print("✅ LLM connection successful")
            print(f"   Model: {llm_test['model_info']['model']}")
            print(f"   Response Length: {llm_test['response_length']} chars")
        else:
            print(f"❌ LLM connection failed: {llm_test['error']}")
            return False
        
        # Test statistical calculator
        print("📊 Testing statistical calculator...")
        try:
            sample_size = self.stats_calculator.calculate_sample_size(
                StatisticalTestType.TWO_SAMPLE_TTEST,
                effect_size=0.5,
                power=0.8,
                alpha=0.05
            )
            print(f"✅ Statistical calculator working (sample size: {sample_size.required_sample_size})")
        except Exception as e:
            print(f"⚠️  Statistical calculator warning: {e}")
        
        return True
    
    def initialize_executor(self) -> bool:
        """Initialize the planning graph executor."""
        print("\n🚀 INITIALIZING PLANNING GRAPH:")
        print("-" * 40)
        
        try:
            self.executor = PlanningGraphExecutor(
                debugger=self.debugger,
                log_level=self.settings.log_level
            )
            self.executor.initialize_graph()
            print("✅ Planning graph initialized successfully")
            return True
        except Exception as e:
            print(f"❌ Failed to initialize planning graph: {e}")
            return False
    
    def display_planning_stages(self) -> None:
        """Display the planning stages and current progress."""
        print("\n📋 PLANNING STAGES:")
        print("-" * 40)
        
        for i, stage in enumerate(PLANNING_STAGES, 1):
            current_stage = self.current_state.get('current_stage') if self.current_state else None
            completed_stages = self.current_state.get('completed_stages', []) if self.current_state else []
            
            if stage == current_stage:
                status = "🔄 CURRENT"
            elif stage in completed_stages:
                status = "✅ COMPLETED"
            else:
                status = "⏳ PENDING"
            
            print(f"{i}. {stage.replace('_', ' ').title()} - {status}")
    
    def display_state_summary(self) -> None:
        """Display a summary of the current experiment state."""
        if not self.current_state:
            print("ℹ️  No current experiment state")
            return
        
        print("\n📊 CURRENT EXPERIMENT STATE:")
        print("-" * 40)
        
        print(f"🆔 Experiment ID: {self.current_state.get('experiment_id', 'N/A')}")
        print(f"❓ Research Query: {self.current_state.get('research_query', 'N/A')}")
        print(f"🎯 Objective: {self.current_state.get('experiment_objective', 'Not set')}")
        print(f"💡 Hypothesis: {self.current_state.get('hypothesis', 'Not set')}")
        
        # Variables
        iv_count = len(self.current_state.get('independent_variables', []))
        dv_count = len(self.current_state.get('dependent_variables', []))
        cv_count = len(self.current_state.get('control_variables', []))
        print(f"📈 Variables: {iv_count} independent, {dv_count} dependent, {cv_count} control")
        
        # Design
        exp_groups = len(self.current_state.get('experimental_groups', []))
        ctrl_groups = len(self.current_state.get('control_groups', []))
        print(f"🧪 Groups: {exp_groups} experimental, {ctrl_groups} control")
        
        # Sample size
        sample_size = self.current_state.get('sample_size', {})
        if sample_size:
            bio_reps = sample_size.get('biological_replicates', 'N/A')
            tech_reps = sample_size.get('technical_replicates', 'N/A')
            print(f"🔢 Sample Size: {bio_reps} biological, {tech_reps} technical replicates")
        
        # Methodology
        method_steps = len(self.current_state.get('methodology_steps', []))
        materials = len(self.current_state.get('materials_equipment', []))
        print(f"📝 Methodology: {method_steps} steps, {materials} materials")
        
        # Data planning
        pitfalls = len(self.current_state.get('potential_pitfalls', []))
        print(f"⚠️  Pitfalls identified: {pitfalls}")
        
        # Errors
        errors = len(self.current_state.get('errors', []))
        if errors > 0:
            print(f"❌ Errors: {errors}")
    
    def display_chat_history(self, limit: int = 5) -> None:
        """Display recent chat history."""
        if not self.current_state:
            return
        
        chat_history = self.current_state.get('chat_history', [])
        if not chat_history:
            print("💬 No chat history yet")
            return
        
        print(f"\n💬 RECENT CHAT HISTORY (last {limit}):")
        print("-" * 40)
        
        recent_messages = chat_history[-limit:]
        for msg in recent_messages:
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            timestamp = msg.get('timestamp', '')
            
            role_emoji = "👤" if role == "user" else "🤖"
            print(f"{role_emoji} {role.title()}: {content[:100]}{'...' if len(content) > 100 else ''}")
    
    def display_menu(self) -> None:
        """Display the main menu options."""
        print("\n📋 AVAILABLE ACTIONS:")
        print("-" * 40)
        print("1. 🆕 Start new experiment planning")
        print("2. 💬 Send message to current agent")
        print("3. 📊 View current state summary")
        print("4. 💭 View chat history")
        print("5. 🔄 View planning stages")
        print("6. 📁 Export current plan")
        print("7. 🔧 Test statistical calculator")
        print("8. 🔍 Debug current state")
        print("9. ❓ Help")
        print("0. 🚪 Exit")
    
    def start_new_experiment(self) -> None:
        """Start a new experiment planning session."""
        print("\n🆕 STARTING NEW EXPERIMENT:")
        print("-" * 40)
        
        research_query = input("🔬 Enter your research question: ").strip()
        if not research_query:
            print("❌ Research question cannot be empty")
            return
        
        try:
            self.executor, self.current_state = start_new_experiment_planning(
                research_query=research_query,
                debugger=self.debugger,
                log_level=self.settings.log_level
            )
            
            print(f"✅ Started new experiment: {self.current_state['experiment_id']}")
            print(f"🎯 Research Query: {research_query}")
            print("\n🤖 Agent Response:")
            print("-" * 40)
            
            # Execute the first step
            self.current_state = self.executor.execute_step(self.current_state)
            
            # Display the agent's response
            self.display_latest_agent_response()
            
        except Exception as e:
            print(f"❌ Failed to start new experiment: {e}")
            self.logger.error(f"Failed to start new experiment: {e}")
    
    def send_message(self) -> None:
        """Send a message to the current agent."""
        if not self.current_state or not self.executor:
            print("❌ No active experiment. Start a new experiment first.")
            return
        
        print("\n💬 SEND MESSAGE TO AGENT:")
        print("-" * 40)
        
        current_stage = self.current_state.get('current_stage', 'unknown')
        print(f"🔄 Current Stage: {current_stage.replace('_', ' ').title()}")
        
        user_message = input("💭 Your message: ").strip()
        if not user_message:
            print("❌ Message cannot be empty")
            return
        
        try:
            print("\n🤖 Processing...")
            self.current_state = self.executor.execute_step(self.current_state, user_message)
            
            print("\n🤖 Agent Response:")
            print("-" * 40)
            self.display_latest_agent_response()
            
        except Exception as e:
            print(f"❌ Failed to send message: {e}")
            self.logger.error(f"Failed to send message: {e}")
    
    def display_latest_agent_response(self) -> None:
        """Display the most recent agent response."""
        if not self.current_state:
            return
        
        chat_history = self.current_state.get('chat_history', [])
        if not chat_history:
            print("No response available")
            return
        
        # Find the most recent assistant message
        for msg in reversed(chat_history):
            if msg.get('role') == 'assistant':
                content = msg.get('content', '')
                print(content)
                break
    
    def export_plan(self) -> None:
        """Export the current experiment plan."""
        if not self.current_state:
            print("❌ No active experiment to export")
            return
        
        print("\n📁 EXPORTING EXPERIMENT PLAN:")
        print("-" * 40)
        
        try:
            # Create export filename
            experiment_id = self.current_state.get('experiment_id', 'unknown')
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"experiment_plan_{experiment_id}_{timestamp}.json"
            
            # Export to JSON
            export_data = {
                'experiment_id': experiment_id,
                'exported_at': datetime.now().isoformat(),
                'research_query': self.current_state.get('research_query'),
                'current_stage': self.current_state.get('current_stage'),
                'completed_stages': self.current_state.get('completed_stages', []),
                'experiment_objective': self.current_state.get('experiment_objective'),
                'hypothesis': self.current_state.get('hypothesis'),
                'independent_variables': self.current_state.get('independent_variables', []),
                'dependent_variables': self.current_state.get('dependent_variables', []),
                'control_variables': self.current_state.get('control_variables', []),
                'experimental_groups': self.current_state.get('experimental_groups', []),
                'control_groups': self.current_state.get('control_groups', []),
                'sample_size': self.current_state.get('sample_size', {}),
                'methodology_steps': self.current_state.get('methodology_steps', []),
                'materials_equipment': self.current_state.get('materials_equipment', []),
                'data_collection_plan': self.current_state.get('data_collection_plan', {}),
                'data_analysis_plan': self.current_state.get('data_analysis_plan', {}),
                'potential_pitfalls': self.current_state.get('potential_pitfalls', []),
                'expected_outcomes': self.current_state.get('expected_outcomes'),
                'errors': self.current_state.get('errors', [])
            }
            
            with open(filename, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            print(f"✅ Plan exported to: {filename}")
            print(f"📊 File size: {os.path.getsize(filename)} bytes")
            
        except Exception as e:
            print(f"❌ Failed to export plan: {e}")
    
    def test_statistical_calculator(self) -> None:
        """Test the statistical calculator functionality."""
        print("\n📊 TESTING STATISTICAL CALCULATOR:")
        print("-" * 40)
        
        try:
            # Test sample size calculation
            print("🔢 Testing sample size calculation...")
            sample_result = self.stats_calculator.calculate_sample_size(
                test_type=StatisticalTestType.TWO_SAMPLE_TTEST,
                effect_size=0.5,
                power=0.8,
                alpha=0.05
            )
            
            print(f"✅ Sample size calculation:")
            print(f"   Required per group: {sample_result.required_sample_size}")
            print(f"   Total sample size: {sample_result.total_sample_size}")
            print(f"   Power achieved: {sample_result.power_achieved:.1%}")
            
            # Test power analysis
            print("\n⚡ Testing power analysis...")
            power_result = self.stats_calculator.calculate_power_analysis(
                test_type=StatisticalTestType.TWO_SAMPLE_TTEST,
                effect_size=0.5,
                sample_size=20,
                alpha=0.05
            )
            
            print(f"✅ Power analysis:")
            print(f"   Statistical power: {power_result.power:.1%}")
            print(f"   Effect size category: {power_result.effect_size_category}")
            print(f"   Test assumptions: {', '.join(power_result.assumptions[:2])}")
            
            # Test statistical test recommendations
            print("\n🔍 Testing test recommendations...")
            mock_design = {
                'independent_variables': [{'name': 'treatment', 'type': 'categorical'}],
                'dependent_variables': [{'name': 'response', 'type': 'continuous'}],
                'experimental_groups': [{'name': 'control'}, {'name': 'treatment'}]
            }
            
            recommendations = self.stats_calculator.recommend_statistical_test(
                mock_design['independent_variables'],
                mock_design['dependent_variables'],
                mock_design['experimental_groups']
            )
            
            print(f"✅ Test recommendations ({len(recommendations)} tests):")
            for rec in recommendations[:3]:  # Show first 3
                print(f"   • {rec['test']}: {rec['description']}")
            
        except Exception as e:
            print(f"❌ Statistical calculator test failed: {e}")
    
    def debug_current_state(self) -> None:
        """Debug the current state with detailed information."""
        if not self.current_state:
            print("❌ No active experiment state to debug")
            return
        
        print("\n🔍 DEBUG STATE INFORMATION:")
        print("-" * 40)
        
        # Basic info
        print(f"🆔 Experiment ID: {self.current_state.get('experiment_id')}")
        print(f"🔄 Current Stage: {self.current_state.get('current_stage')}")
        print(f"✅ Completed Stages: {self.current_state.get('completed_stages', [])}")
        print(f"❌ Errors: {len(self.current_state.get('errors', []))}")
        
        # State validation
        try:
            from agents.planning import validate_experiment_plan_state
            validate_experiment_plan_state(self.current_state)
            print("✅ State validation: PASSED")
        except Exception as e:
            print(f"❌ State validation: FAILED - {e}")
        
        # Chat history
        chat_count = len(self.current_state.get('chat_history', []))
        print(f"💬 Chat Messages: {chat_count}")
        
        # Save debug snapshot
        try:
            debug_filename = f"debug_state_{self.current_state.get('experiment_id')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(debug_filename, 'w') as f:
                json.dump(self.current_state, f, indent=2, default=str)
            print(f"📁 Debug snapshot saved: {debug_filename}")
        except Exception as e:
            print(f"⚠️  Could not save debug snapshot: {e}")
    
    def display_help(self) -> None:
        """Display help information."""
        print("\n❓ HELP INFORMATION:")
        print("-" * 40)
        print("📋 This tool tests the complete LangGraph planning agent system")
        print("🔄 The system follows these stages:")
        for i, stage in enumerate(PLANNING_STAGES, 1):
            print(f"   {i}. {stage.replace('_', ' ').title()}")
        
        print("\n💡 Tips:")
        print("• Start with a clear research question")
        print("• Provide detailed responses to agent questions")
        print("• Use the state summary to track progress")
        print("• Export your plan when complete")
        print("• Check the debug info if issues arise")
        
        print("\n🔧 Configuration:")
        print("• Set OPENAI_API_KEY environment variable")
        print("• Optional: Set TAVILY_API_KEY for web search")
        print("• Adjust settings in config.py if needed")
    
    def run(self) -> None:
        """Run the interactive planning flow tester."""
        self.display_header()
        
        # Validate setup
        if not self.validate_setup():
            print("\n❌ Setup validation failed. Please fix configuration issues.")
            return
        
        # Initialize executor
        if not self.initialize_executor():
            print("\n❌ Failed to initialize planning graph. Cannot continue.")
            return
        
        # Display system info
        self.display_system_info()
        
        print("\n🚀 SYSTEM READY FOR TESTING!")
        print("Use the menu below to test different aspects of the planning system.")
        
        # Main interaction loop
        while True:
            try:
                self.display_menu()
                choice = input("\n🎯 Select an action (0-9): ").strip()
                
                if choice == '0':
                    print("\n👋 Goodbye! Thanks for testing the planning system.")
                    break
                elif choice == '1':
                    self.start_new_experiment()
                elif choice == '2':
                    self.send_message()
                elif choice == '3':
                    self.display_state_summary()
                elif choice == '4':
                    self.display_chat_history()
                elif choice == '5':
                    self.display_planning_stages()
                elif choice == '6':
                    self.export_plan()
                elif choice == '7':
                    self.test_statistical_calculator()
                elif choice == '8':
                    self.debug_current_state()
                elif choice == '9':
                    self.display_help()
                else:
                    print("❌ Invalid choice. Please select 0-9.")
                
                # Add a small pause for better UX
                input("\n⏸️  Press Enter to continue...")
                
            except KeyboardInterrupt:
                print("\n\n👋 Interrupted by user. Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Unexpected error: {e}")
                self.logger.error(f"Unexpected error in main loop: {e}")
                input("⏸️  Press Enter to continue...")


def main():
    """Main entry point for the planning flow tester."""
    print("🔧 Initializing Planning Flow Tester...")
    
    # Initialize configuration
    try:
        initialize_logging()
    except Exception as e:
        print(f"❌ Failed to initialize logging: {e}")
    
    # Create and run the tester
    tester = PlanningFlowTester()
    tester.run()


if __name__ == "__main__":
    main() 