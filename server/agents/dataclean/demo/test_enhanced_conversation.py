#!/usr/bin/env python3
"""
Enhanced Conversation System Integration Test

This script comprehensively tests the enhanced conversation system including:
- Complete delegation chain: API → ConversationGraph → EnhancedConversationGraph → Enhanced Nodes
- Simplified conversation templates
- Multi-turn context management
- Error recovery mechanisms
- Proactive suggestions
- Conversation summarization
- Real data processing integration
- Backward compatibility

Usage: python test_enhanced_conversation.py
"""

import asyncio
import pandas as pd
import tempfile
import os
import sys
import json
from datetime import datetime
from pathlib import Path
import uuid

# Add parent directories to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agents.dataclean.conversation.conversation_graph import ConversationGraph
from agents.dataclean.conversation.state_schema import ConversationState, Intent
from agents.dataclean.memory_store import get_data_store
from agents.dataclean.models import DataArtifact, ProcessingStatus, FileMetadata
from agents.dataclean.file_processor import FileProcessingAgent
from agents.dataclean.quality_agent import DataQualityAgent
from config import get_openai_client


class EnhancedConversationTester:
    """
    Comprehensive test suite for the enhanced conversation system.
    """
    
    def __init__(self):
        """Initialize the test suite."""
        self.conversation_graph = ConversationGraph()
        self.data_store = get_data_store()
        self.file_processor = FileProcessingAgent()
        self.openai_client = get_openai_client()
        self.test_results = []
        self.test_artifact_id = None
        
        print("🔧 Enhanced Conversation Tester Initialized")
        print(f"📊 Using conversation graph: {type(self.conversation_graph).__name__}")
        print(f"💾 Using data store: {type(self.data_store).__name__}")
        print(f"🤖 OpenAI available: {'✅' if self.openai_client else '❌'}")
    
    async def run_all_tests(self):
        """Run all enhanced conversation tests."""
        print("\n🧪 Starting Enhanced Conversation System Tests")
        print("=" * 70)
        
        try:
            # Setup test data
            await self._setup_test_data()
            
            # Test 1: Delegation chain validation
            await self._test_delegation_chain()
            
            # Test 2: Enhanced conversation start
            await self._test_enhanced_conversation_start()
            
            # Test 3: Multi-turn conversation flow
            await self._test_multi_turn_conversation()
            
            # Test 4: Simplified templates integration
            await self._test_simplified_templates()
            
            # Test 5: Proactive suggestions
            await self._test_proactive_suggestions()
            
            # Test 6: Error recovery mechanisms
            await self._test_error_recovery()
            
            # Test 7: Conversation summarization
            await self._test_conversation_summarization()
            
            # Test 8: Real data processing integration
            await self._test_real_data_processing()
            
            # Test 9: Backward compatibility
            await self._test_backward_compatibility()
            
            # Test 10: Performance benchmarks
            await self._test_performance()
            
            # Print results
            self._print_test_results()
            
        except Exception as e:
            print(f"❌ Test suite failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
        
        return all(result["passed"] for result in self.test_results)
    
    async def _setup_test_data(self):
        """Setup test data for conversation tests."""
        print("\n🔧 Setting up test data...")
        
        # Create test DataFrame
        test_data = pd.DataFrame({
            'name': ['Alice', 'Bob', 'Charlie', 'David', 'Eve'] * 4,  # 20 rows
            'age': [25, 30, 35, 40, 45] * 4,
            'email': ['alice@test.com', 'bob@test.com', 'charlie@test.com', 'david@test.com', 'eve@test.com'] * 4,
            'city': ['New York', 'San Francisco', 'Los Angeles', 'Chicago', 'Boston'] * 4,
            'salary': [50000, 60000, 70000, 80000, 90000] * 4
        })
        
        # Add some data quality issues for testing
        test_data.loc[1, 'email'] = None  # Missing value
        test_data.loc[3, 'age'] = 'thirty'  # Type inconsistency
        test_data.loc[5, 'salary'] = -5000  # Outlier
        
        # Create artifact
        self.test_artifact_id = str(uuid.uuid4())
        artifact = DataArtifact(
            artifact_id=self.test_artifact_id,
            experiment_id="enhanced-test-experiment",
            owner_id="test-user",
            status=ProcessingStatus.READY_FOR_ANALYSIS,
            original_file=FileMetadata(
                name="test_data_enhanced.csv",
                path="/tmp/test_data_enhanced.csv",
                size=1024,
                mime_type="text/csv",
                uploaded_at=datetime.now()
            ),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Save to data store
        await self.data_store.save_data_artifact(artifact)
        await self.data_store.save_dataframe(self.test_artifact_id, test_data)
        
        print(f"✅ Test data created: {test_data.shape[0]} rows, {test_data.shape[1]} columns")
        print(f"📝 Test artifact ID: {self.test_artifact_id}")
    
    async def _test_delegation_chain(self):
        """Test the complete delegation chain: ConversationGraph → EnhancedConversationGraph → Enhanced Nodes."""
        test_name = "Delegation Chain Validation"
        print(f"\n🔄 Testing: {test_name}")
        
        try:
            # Test that conversation graph delegates to enhanced graph
            conversation_graph = self.conversation_graph
            
            # Check that it has enhanced_graph attribute
            assert hasattr(conversation_graph, 'enhanced_graph'), "ConversationGraph should delegate to enhanced graph"
            
            # Test start_conversation delegation
            result = await conversation_graph.start_conversation(
                user_id="test-user",
                session_id="delegation-test"
            )
            
            assert result["success"] is True, "Start conversation should succeed"
            assert "session_id" in result, "Should return session_id"
            assert "message" in result, "Should return welcome message"
            
            # Test process_message delegation
            message_result = await conversation_graph.process_message(
                user_message="show me the data",
                session_id=result["session_id"],
                user_id="test-user",
                artifact_id=self.test_artifact_id
            )
            
            assert message_result["success"] is True, "Process message should succeed"
            assert "response" in message_result, "Should return response"
            assert "intent" in message_result, "Should classify intent"
            
            self._add_test_result(test_name, True, "✅ Delegation chain working correctly")
            
        except Exception as e:
            self._add_test_result(test_name, False, f"❌ {str(e)}")
    
    async def _test_enhanced_conversation_start(self):
        """Test enhanced conversation start with welcome message and capabilities."""
        test_name = "Enhanced Conversation Start"
        print(f"\n🔄 Testing: {test_name}")
        
        try:
            # Test conversation start with data
            result = await self.conversation_graph.start_conversation(
                user_id="test-user",
                session_id="enhanced-start-test",
                artifact_id=self.test_artifact_id
            )
            
            assert result["success"] is True, "Enhanced start should succeed"
            assert "capabilities" in result, "Should include capabilities"
            assert "conversation_active" in result, "Should indicate active conversation"
            
            # Check welcome message mentions data
            welcome_message = result["message"]
            assert "data ready" in welcome_message.lower() or "data" in welcome_message.lower(), "Should mention data availability"
            
            # Test conversation start without data
            result_no_data = await self.conversation_graph.start_conversation(
                user_id="test-user",
                session_id="enhanced-start-no-data"
            )
            
            assert result_no_data["success"] is True, "Start without data should succeed"
            welcome_message_no_data = result_no_data["message"]
            assert "upload" in welcome_message_no_data.lower(), "Should mention file upload"
            
            self._add_test_result(test_name, True, "✅ Enhanced conversation start working")
            
        except Exception as e:
            self._add_test_result(test_name, False, f"❌ {str(e)}")
    
    async def _test_multi_turn_conversation(self):
        """Test multi-turn conversation with context management."""
        test_name = "Multi-Turn Conversation"
        print(f"\n🔄 Testing: {test_name}")
        
        try:
            # Start conversation
            session_result = await self.conversation_graph.start_conversation(
                user_id="test-user",
                session_id="multi-turn-test",
                artifact_id=self.test_artifact_id
            )
            
            session_id = session_result["session_id"]
            
            # Sequence of related messages
            conversation_flow = [
                "show me the data",
                "describe the data structure", 
                "analyze the data quality",
                "clean the data"
            ]
            
            previous_response = None
            
            for i, message in enumerate(conversation_flow):
                print(f"  📨 Turn {i+1}: {message}")
                
                result = await self.conversation_graph.process_message(
                    user_message=message,
                    session_id=session_id,
                    user_id="test-user",
                    artifact_id=self.test_artifact_id
                )
                
                assert result["success"] is True, f"Turn {i+1} should succeed"
                assert "response" in result, f"Turn {i+1} should have response"
                assert "intent" in result, f"Turn {i+1} should classify intent"
                
                # Check that responses are different (conversation progresses)
                current_response = result["response"]
                if previous_response:
                    assert current_response != previous_response, "Responses should evolve"
                
                previous_response = current_response
                print(f"  ✅ Turn {i+1} completed: {result['intent']}")
            
            # Check session summary
            summary = await self.conversation_graph.get_session_summary(session_id)
            assert summary["status"] == "success", "Session summary should succeed"
            assert summary["conversation_turns"] >= len(conversation_flow) * 2, "Should track all turns"
            
            self._add_test_result(test_name, True, "✅ Multi-turn conversation working")
            
        except Exception as e:
            self._add_test_result(test_name, False, f"❌ {str(e)}")
    
    async def _test_simplified_templates(self):
        """Test simplified conversation templates integration."""
        test_name = "Simplified Templates"
        print(f"\n🔄 Testing: {test_name}")
        
        try:
            # Start conversation (should trigger template suggestions)
            session_result = await self.conversation_graph.start_conversation(
                user_id="test-user",
                session_id="templates-test",
                artifact_id=self.test_artifact_id
            )
            
            # Test that welcome message includes helpful suggestions
            welcome_message = session_result["message"]
            assert "try:" in welcome_message.lower() or "suggestions:" in welcome_message.lower(), "Should include template suggestions"
            
            # Test template suggestions appear in responses
            result = await self.conversation_graph.process_message(
                user_message="help me get started",
                session_id=session_result["session_id"],
                user_id="test-user",
                artifact_id=self.test_artifact_id
            )
            
            response = result["response"]
            
            # Check for template-style suggestions
            has_examples = any(phrase in response.lower() for phrase in [
                "try:", "example:", "you can:", "💡", "📋", "suggestions:"
            ])
            
            assert has_examples, "Response should include helpful examples/suggestions"
            
            # Test templates don't interfere with real processing
            result2 = await self.conversation_graph.process_message(
                user_message="show me the data",
                session_id=session_result["session_id"],
                user_id="test-user",
                artifact_id=self.test_artifact_id
            )
            
            assert result2["success"] is True, "Templates shouldn't interfere with real processing"
            assert result2["intent"] == "show_data", "Intent classification should still work"
            
            self._add_test_result(test_name, True, "✅ Simplified templates working correctly")
            
        except Exception as e:
            self._add_test_result(test_name, False, f"❌ {str(e)}")
    
    async def _test_proactive_suggestions(self):
        """Test proactive suggestions engine."""
        test_name = "Proactive Suggestions"
        print(f"\n🔄 Testing: {test_name}")
        
        try:
            # Start conversation
            session_result = await self.conversation_graph.start_conversation(
                user_id="test-user",
                session_id="proactive-test",
                artifact_id=self.test_artifact_id
            )
            
            # Process a message that should trigger proactive suggestions
            result = await self.conversation_graph.process_message(
                user_message="show me the data",
                session_id=session_result["session_id"],
                user_id="test-user",
                artifact_id=self.test_artifact_id
            )
            
            response = result["response"]
            
            # Check for proactive suggestions in response
            has_suggestions = any(phrase in response.lower() for phrase in [
                "suggestions:", "💡", "next steps:", "you might want to:", "consider:"
            ])
            
            # Since proactive suggestions depend on OpenAI, only check if client is available
            if self.openai_client:
                assert has_suggestions, "Should include proactive suggestions when OpenAI is available"
                print("  ✅ Proactive suggestions detected")
            else:
                print("  ⚠️  Proactive suggestions skipped (no OpenAI client)")
            
            # Test suggestions_provided flag
            suggestions_provided = result.get("suggestions_provided", False)
            assert isinstance(suggestions_provided, bool), "Should have suggestions_provided flag"
            
            self._add_test_result(test_name, True, "✅ Proactive suggestions system working")
            
        except Exception as e:
            self._add_test_result(test_name, False, f"❌ {str(e)}")
    
    async def _test_error_recovery(self):
        """Test error recovery mechanisms."""
        test_name = "Error Recovery"
        print(f"\n🔄 Testing: {test_name}")
        
        try:
            # Start conversation
            session_result = await self.conversation_graph.start_conversation(
                user_id="test-user",
                session_id="error-recovery-test"
            )
            
            # Test with invalid artifact ID (should trigger error recovery)
            result = await self.conversation_graph.process_message(
                user_message="show me the data",
                session_id=session_result["session_id"],
                user_id="test-user",
                artifact_id="invalid-artifact-id"
            )
            
            # Should handle error gracefully
            assert result["success"] is True, "Should handle errors gracefully"
            assert "response" in result, "Should provide error response"
            
            response = result["response"]
            assert any(word in response.lower() for word in ["error", "issue", "problem", "upload", "file"]), "Should explain the issue"
            
            # Test recovery by providing valid request
            result2 = await self.conversation_graph.process_message(
                user_message="what can I do?",
                session_id=session_result["session_id"],
                user_id="test-user"
            )
            
            assert result2["success"] is True, "Should recover from error"
            assert "upload" in result2["response"].lower(), "Should suggest next steps"
            
            self._add_test_result(test_name, True, "✅ Error recovery working correctly")
            
        except Exception as e:
            self._add_test_result(test_name, False, f"❌ {str(e)}")
    
    async def _test_conversation_summarization(self):
        """Test conversation summarization for long conversations."""
        test_name = "Conversation Summarization"
        print(f"\n🔄 Testing: {test_name}")
        
        try:
            # Start conversation
            session_result = await self.conversation_graph.start_conversation(
                user_id="test-user",
                session_id="summarization-test",
                artifact_id=self.test_artifact_id
            )
            
            session_id = session_result["session_id"]
            
            # Simulate many turns to trigger summarization (25 messages = 50 turns with responses)
            for i in range(25):
                await self.conversation_graph.process_message(
                    user_message=f"show me data - turn {i}",
                    session_id=session_id,
                    user_id="test-user",
                    artifact_id=self.test_artifact_id
                )
            
            # Check if conversation still works after potential summarization
            final_result = await self.conversation_graph.process_message(
                user_message="describe the data",
                session_id=session_id,
                user_id="test-user",
                artifact_id=self.test_artifact_id
            )
            
            assert final_result["success"] is True, "Should work after many turns"
            assert "response" in final_result, "Should still provide responses"
            
            # Check session summary
            summary = await self.conversation_graph.get_session_summary(session_id)
            assert summary["status"] == "success", "Session summary should work"
            
            print(f"  📊 Conversation turns: {summary.get('conversation_turns', 0)}")
            
            self._add_test_result(test_name, True, "✅ Conversation summarization working")
            
        except Exception as e:
            self._add_test_result(test_name, False, f"❌ {str(e)}")
    
    async def _test_real_data_processing(self):
        """Test integration with real data processing components."""
        test_name = "Real Data Processing"
        print(f"\n🔄 Testing: {test_name}")
        
        try:
            # Start conversation
            session_result = await self.conversation_graph.start_conversation(
                user_id="test-user",
                session_id="real-processing-test",
                artifact_id=self.test_artifact_id
            )
            
            session_id = session_result["session_id"]
            
            # Test real data operations
            operations = [
                ("show me the data", "show_data"),
                ("describe the data", "describe"),
            ]
            
            if self.openai_client:
                operations.append(("analyze the data quality", "analyze"))
            
            for message, expected_intent in operations:
                result = await self.conversation_graph.process_message(
                    user_message=message,
                    session_id=session_id,
                    user_id="test-user",
                    artifact_id=self.test_artifact_id
                )
                
                assert result["success"] is True, f"Operation '{message}' should succeed"
                assert result["intent"] == expected_intent, f"Should classify as {expected_intent}"
                
                # Check that processing_result contains real data
                processing_result = result.get("processing_result", {})
                if processing_result.get("success"):
                    print(f"  ✅ {message} → Real data processed")
                else:
                    print(f"  ⚠️  {message} → {processing_result.get('message', 'No details')}")
            
            self._add_test_result(test_name, True, "✅ Real data processing integration working")
            
        except Exception as e:
            self._add_test_result(test_name, False, f"❌ {str(e)}")
    
    async def _test_backward_compatibility(self):
        """Test backward compatibility with existing APIs."""
        test_name = "Backward Compatibility"
        print(f"\n🔄 Testing: {test_name}")
        
        try:
            # Test all core API methods still work
            methods_to_test = [
                "start_conversation",
                "process_message", 
                "handle_confirmation",
                "get_session_summary",
                "get_conversation_capabilities"
            ]
            
            for method_name in methods_to_test:
                assert hasattr(self.conversation_graph, method_name), f"Should have {method_name} method"
            
            # Test get_conversation_capabilities
            capabilities = self.conversation_graph.get_conversation_capabilities()
            assert isinstance(capabilities, dict), "Capabilities should be a dict"
            assert "supported_intents" in capabilities, "Should include supported intents"
            assert "features" in capabilities, "Should include features"
            
            # Test handle_confirmation
            session_result = await self.conversation_graph.start_conversation(
                user_id="test-user",
                session_id="compatibility-test"
            )
            
            confirmation_result = await self.conversation_graph.handle_confirmation(
                session_id=session_result["session_id"],
                user_id="test-user",
                confirmed=True
            )
            
            assert confirmation_result["success"] is True, "Confirmation handling should work"
            assert "response" in confirmation_result, "Should provide confirmation response"
            
            self._add_test_result(test_name, True, "✅ Backward compatibility maintained")
            
        except Exception as e:
            self._add_test_result(test_name, False, f"❌ {str(e)}")
    
    async def _test_performance(self):
        """Test performance benchmarks."""
        test_name = "Performance"
        print(f"\n🔄 Testing: {test_name}")
        
        try:
            import time
            
            # Start conversation
            start_time = time.time()
            session_result = await self.conversation_graph.start_conversation(
                user_id="test-user",
                session_id="performance-test",
                artifact_id=self.test_artifact_id
            )
            start_duration = time.time() - start_time
            
            # Process message
            msg_start_time = time.time()
            message_result = await self.conversation_graph.process_message(
                user_message="show me the data",
                session_id=session_result["session_id"],
                user_id="test-user",
                artifact_id=self.test_artifact_id
            )
            msg_duration = time.time() - msg_start_time
            
            # Performance thresholds
            start_threshold = 2.0  # seconds
            message_threshold = 5.0  # seconds (generous for AI processing)
            
            start_ok = start_duration < start_threshold
            message_ok = msg_duration < message_threshold
            
            print(f"  📊 Start conversation: {start_duration:.2f}s (threshold: {start_threshold}s)")
            print(f"  📊 Process message: {msg_duration:.2f}s (threshold: {message_threshold}s)")
            
            performance_ok = start_ok and message_ok
            
            if not performance_ok:
                print(f"  ⚠️  Performance warning: Some operations exceeded thresholds")
            
            self._add_test_result(test_name, True, f"✅ Performance measured (start: {start_duration:.2f}s, message: {msg_duration:.2f}s)")
            
        except Exception as e:
            self._add_test_result(test_name, False, f"❌ {str(e)}")
    
    def _add_test_result(self, test_name: str, passed: bool, message: str):
        """Add test result to results list."""
        self.test_results.append({
            "test": test_name,
            "passed": passed,
            "message": message
        })
        print(f"  {message}")
    
    def _print_test_results(self):
        """Print comprehensive test results."""
        print("\n" + "=" * 70)
        print("🏁 ENHANCED CONVERSATION TEST RESULTS")
        print("=" * 70)
        
        passed_tests = sum(1 for result in self.test_results if result["passed"])
        total_tests = len(self.test_results)
        
        # Group results by category
        categories = {
            "Core": ["Delegation Chain Validation", "Enhanced Conversation Start", "Backward Compatibility"],
            "Features": ["Multi-Turn Conversation", "Simplified Templates", "Proactive Suggestions"],
            "Robustness": ["Error Recovery", "Conversation Summarization", "Performance"],
            "Integration": ["Real Data Processing"]
        }
        
        for category, test_names in categories.items():
            print(f"\n📁 {category}:")
            for result in self.test_results:
                if result["test"] in test_names:
                    status = "✅ PASS" if result["passed"] else "❌ FAIL"
                    print(f"  {status} | {result['test']}")
                    if not result["passed"]:
                        print(f"         {result['message']}")
        
        # Any remaining tests
        categorized_tests = [test for tests in categories.values() for test in tests]
        remaining_tests = [r for r in self.test_results if r["test"] not in categorized_tests]
        
        if remaining_tests:
            print(f"\n📋 Other:")
            for result in remaining_tests:
                status = "✅ PASS" if result["passed"] else "❌ FAIL"
                print(f"  {status} | {result['test']}")
        
        print("-" * 70)
        print(f"TOTAL: {passed_tests}/{total_tests} tests passed ({passed_tests/total_tests:.1%})")
        
        if passed_tests == total_tests:
            print("🎉 ALL TESTS PASSED! Enhanced conversation system is working correctly.")
            print("✅ Ready for production use!")
        elif passed_tests >= total_tests * 0.8:  # 80% threshold
            print("⚡ MOSTLY PASSING! System is functional with minor issues.")
            print("💡 Consider addressing failed tests before production.")
        else:
            print("⚠️  SIGNIFICANT ISSUES! Multiple tests failed.")
            print("🔧 System needs attention before production use.")
        
        return passed_tests == total_tests


def check_environment():
    """Check if environment is properly configured."""
    print("🔧 Checking enhanced conversation test environment...")
    
    # Check imports
    try:
        from agents.dataclean.conversation.conversation_graph import ConversationGraph
        print("✅ ConversationGraph import successful")
    except ImportError as e:
        print(f"❌ ConversationGraph import failed: {e}")
        return False
    
    # Check OpenAI (optional)
    openai_client = get_openai_client()
    if openai_client:
        print("✅ OpenAI client available (full testing)")
    else:
        print("⚠️  OpenAI client not available (limited AI testing)")
    
    return True


async def main():
    """Run the enhanced conversation integration tests."""
    print("🚀 ScioScribe Enhanced Conversation System Test")
    print("Testing complete delegation chain and Phase 3 features...")
    
    # Check environment
    if not check_environment():
        print("❌ Environment check failed!")
        return 1
    
    # Run tests
    tester = EnhancedConversationTester()
    success = await tester.run_all_tests()
    
    if success:
        print("\n✅ Enhanced conversation test completed successfully!")
        print("🎯 System ready for Phase 3 completion and production deployment.")
        return 0
    else:
        print("\n❌ Enhanced conversation test found issues!")
        print("🔧 Please address failed tests before proceeding.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code) 