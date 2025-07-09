#!/usr/bin/env python3
"""
Test script for LangGraph conversation integration with existing data cleaning components.

This script tests the enhanced backend integration to ensure that conversation
nodes properly interact with existing components like memory_store, quality_agent, etc.
"""

import asyncio
import pandas as pd
import tempfile
import os
import sys
from datetime import datetime
from pathlib import Path

# Add parent directories to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from langgraph.conversation_graph import ConversationGraph
from langgraph.state_schema import ConversationState, Intent
from memory_store import get_data_store
from models import DataArtifact, ProcessingStatus, FileMetadata
from file_processor import FileProcessingAgent


class ConversationIntegrationTester:
    """
    Test suite for verifying LangGraph conversation integration with existing components.
    """
    
    def __init__(self):
        """Initialize the test suite."""
        self.conversation_graph = ConversationGraph()
        self.data_store = get_data_store()
        self.file_processor = FileProcessingAgent()
        self.test_results = []
        
    async def run_all_tests(self):
        """Run all integration tests."""
        print("🧪 Starting LangGraph Conversation Integration Tests")
        print("=" * 60)
        
        try:
            # Test 1: Basic conversation flow
            await self._test_basic_conversation_flow()
            
            # Test 2: Data artifact integration
            await self._test_data_artifact_integration()
            
            # Test 3: Intent classification
            await self._test_intent_classification()
            
            # Test 4: Component integration
            await self._test_component_integration()
            
            # Test 5: Session management
            await self._test_session_management()
            
            # Test 6: Error handling
            await self._test_error_handling()
            
            # Print results
            self._print_test_results()
            
        except Exception as e:
            print(f"❌ Test suite failed: {str(e)}")
            return False
        
        return all(result["passed"] for result in self.test_results)
    
    async def _test_basic_conversation_flow(self):
        """Test basic conversation workflow."""
        test_name = "Basic Conversation Flow"
        print(f"\n🔄 Testing: {test_name}")
        
        try:
            # Start conversation
            session_result = await self.conversation_graph.start_conversation(
                user_id="test-user",
                session_id="test-session-1"
            )
            
            # Check session creation
            assert session_result["status"] == "active"
            assert "session_id" in session_result
            
            # Process a simple message
            message_result = await self.conversation_graph.process_message(
                user_message="show me data",
                session_id=session_result["session_id"],
                user_id="test-user"
            )
            
            # Check response
            assert "response" in message_result
            assert "intent" in message_result
            assert message_result["intent"] == Intent.SHOW_DATA.value
            
            self._add_test_result(test_name, True, "✅ Basic conversation flow working")
            
        except Exception as e:
            self._add_test_result(test_name, False, f"❌ {str(e)}")
    
    async def _test_data_artifact_integration(self):
        """Test integration with existing data artifacts."""
        test_name = "Data Artifact Integration"
        print(f"\n🔄 Testing: {test_name}")
        
        try:
            # Create test data
            test_data = pd.DataFrame({
                'name': ['Alice', 'Bob', 'Charlie'],
                'age': [25, 30, 35],
                'email': ['alice@test.com', 'bob@test.com', 'charlie@test.com']
            })
            
            # Create artifact
            artifact_id = "test-artifact-123"
            artifact = DataArtifact(
                artifact_id=artifact_id,
                experiment_id="test-experiment",
                owner_id="test-user",
                status=ProcessingStatus.READY_FOR_ANALYSIS,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # Save to memory store
            await self.data_store.save_data_artifact(artifact)
            await self.data_store.save_dataframe(artifact_id, test_data)
            
            # Start conversation with artifact
            session_result = await self.conversation_graph.start_conversation(
                user_id="test-user",
                session_id="test-session-2",
                artifact_id=artifact_id
            )
            
            # Test data exploration
            message_result = await self.conversation_graph.process_message(
                user_message="show me the first 5 rows",
                session_id=session_result["session_id"],
                user_id="test-user",
                artifact_id=artifact_id
            )
            
            # Check if data was retrieved
            assert message_result["response_type"] == "result"
            assert "operation_result" in message_result
            assert message_result["operation_result"]["status"] == "success"
            
            self._add_test_result(test_name, True, "✅ Data artifact integration working")
            
        except Exception as e:
            self._add_test_result(test_name, False, f"❌ {str(e)}")
    
    async def _test_intent_classification(self):
        """Test intent classification accuracy."""
        test_name = "Intent Classification"
        print(f"\n🔄 Testing: {test_name}")
        
        test_cases = [
            ("show me data", Intent.SHOW_DATA),
            ("analyze the quality", Intent.ANALYZE),
            ("describe my dataset", Intent.DESCRIBE),
            ("clean the data", Intent.CLEAN),
            ("remove duplicates", Intent.REMOVE),
            ("which sheets are available", Intent.SELECT_SHEET),
            ("what's the delimiter", Intent.DETECT_DELIMITER)
        ]
        
        passed_cases = 0
        total_cases = len(test_cases)
        
        try:
            for message, expected_intent in test_cases:
                # Test intent classification through message processing
                session_result = await self.conversation_graph.start_conversation(
                    user_id="test-user",
                    session_id=f"test-intent-{passed_cases}"
                )
                
                message_result = await self.conversation_graph.process_message(
                    user_message=message,
                    session_id=session_result["session_id"],
                    user_id="test-user"
                )
                
                classified_intent = Intent(message_result["intent"])
                if classified_intent == expected_intent:
                    passed_cases += 1
                    print(f"  ✅ '{message}' → {classified_intent.value}")
                else:
                    print(f"  ❌ '{message}' → Expected: {expected_intent.value}, Got: {classified_intent.value}")
            
            accuracy = passed_cases / total_cases
            success = accuracy >= 0.8  # 80% accuracy threshold
            
            result_msg = f"✅ Intent classification: {passed_cases}/{total_cases} ({accuracy:.1%})" if success else f"❌ Intent classification below threshold: {accuracy:.1%}"
            self._add_test_result(test_name, success, result_msg)
            
        except Exception as e:
            self._add_test_result(test_name, False, f"❌ {str(e)}")
    
    async def _test_component_integration(self):
        """Test integration with existing components."""
        test_name = "Component Integration"
        print(f"\n🔄 Testing: {test_name}")
        
        try:
            # Create test CSV file
            test_csv_data = """name,age,email,city
Alice,25,alice@test.com,New York
Bob,30,bob@test.com,San Francisco
Charlie,35,charlie@test.com,Los Angeles"""
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
                f.write(test_csv_data)
                temp_file_path = f.name
            
            try:
                # Test file processing integration
                result = await self.file_processor.process_file(temp_file_path, "text/csv")
                assert result.success, "File processor should work"
                
                # Test conversation with file context
                session_result = await self.conversation_graph.start_conversation(
                    user_id="test-user",
                    session_id="test-components",
                    file_path=temp_file_path
                )
                
                # Test delimiter detection
                message_result = await self.conversation_graph.process_message(
                    user_message="what's the delimiter in this CSV?",
                    session_id=session_result["session_id"],
                    user_id="test-user"
                )
                
                assert message_result["intent"] == Intent.DETECT_DELIMITER.value
                assert message_result["operation_result"]["status"] == "success"
                
                self._add_test_result(test_name, True, "✅ Component integration working")
                
            finally:
                # Clean up
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
            
        except Exception as e:
            self._add_test_result(test_name, False, f"❌ {str(e)}")
    
    async def _test_session_management(self):
        """Test conversation session management."""
        test_name = "Session Management"
        print(f"\n🔄 Testing: {test_name}")
        
        try:
            # Start session
            session_result = await self.conversation_graph.start_conversation(
                user_id="test-user",
                session_id="test-session-mgmt"
            )
            
            session_id = session_result["session_id"]
            
            # Send multiple messages
            messages = [
                "show me data",
                "describe the dataset",
                "analyze quality"
            ]
            
            for message in messages:
                await self.conversation_graph.process_message(
                    user_message=message,
                    session_id=session_id,
                    user_id="test-user"
                )
            
            # Get session summary
            summary_result = await self.conversation_graph.get_session_summary(session_id)
            
            assert summary_result["status"] == "success"
            assert "session_summary" in summary_result
            assert summary_result["session_summary"]["conversation_turns"] >= len(messages) * 2  # user + assistant
            
            self._add_test_result(test_name, True, "✅ Session management working")
            
        except Exception as e:
            self._add_test_result(test_name, False, f"❌ {str(e)}")
    
    async def _test_error_handling(self):
        """Test error handling and graceful failures."""
        test_name = "Error Handling"
        print(f"\n🔄 Testing: {test_name}")
        
        try:
            # Test with invalid session
            message_result = await self.conversation_graph.process_message(
                user_message="test message",
                session_id="invalid-session-id",
                user_id="test-user"
            )
            
            # Should handle gracefully and create new session
            assert "response" in message_result
            assert message_result["response_type"] in ["error", "result"]
            
            # Test with invalid artifact
            session_result = await self.conversation_graph.start_conversation(
                user_id="test-user",
                session_id="test-error-handling",
                artifact_id="invalid-artifact-id"
            )
            
            message_result = await self.conversation_graph.process_message(
                user_message="show me data",
                session_id=session_result["session_id"],
                user_id="test-user",
                artifact_id="invalid-artifact-id"
            )
            
            # Should handle missing data gracefully
            assert "response" in message_result
            
            self._add_test_result(test_name, True, "✅ Error handling working")
            
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
        print("\n" + "=" * 60)
        print("🏁 TEST RESULTS SUMMARY")
        print("=" * 60)
        
        passed_tests = sum(1 for result in self.test_results if result["passed"])
        total_tests = len(self.test_results)
        
        for result in self.test_results:
            status = "✅ PASS" if result["passed"] else "❌ FAIL"
            print(f"{status} | {result['test']}")
            if not result["passed"]:
                print(f"      {result['message']}")
        
        print("-" * 60)
        print(f"TOTAL: {passed_tests}/{total_tests} tests passed ({passed_tests/total_tests:.1%})")
        
        if passed_tests == total_tests:
            print("🎉 ALL TESTS PASSED! Backend integration is working correctly.")
        else:
            print("⚠️  Some tests failed. Check the integration implementation.")
        
        return passed_tests == total_tests


async def main():
    """Run the conversation integration tests."""
    print("ScioScribe LangGraph Conversation Integration Test")
    print("Testing backend integration between LangGraph and existing components...")
    
    tester = ConversationIntegrationTester()
    success = await tester.run_all_tests()
    
    if success:
        print("\n✅ Integration test completed successfully!")
        print("The LangGraph conversation system is properly integrated with existing components.")
        return 0
    else:
        print("\n❌ Integration test failed!")
        print("There are issues with the LangGraph conversation integration.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code) 