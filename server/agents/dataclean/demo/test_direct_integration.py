#!/usr/bin/env python3
"""
Direct integration test for LangGraph conversation system.

This test directly tests the core functionality to verify backend integration
without complex import dependencies.
"""

import asyncio
import sys
import os
import pandas as pd
from datetime import datetime
from pathlib import Path

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

async def test_basic_conversation_flow():
    """Test basic conversation workflow."""
    print("🧪 Testing Basic Conversation Flow")
    print("=" * 40)
    
    try:
        # Test 1: Import test
        print("📦 Testing imports...")
        from langgraph.graph import StateGraph, END
        print("✅ LangGraph imports successful")
        
        # Test 2: Memory store test
        print("💾 Testing memory store...")
        from memory_store import get_data_store
        data_store = get_data_store()
        stats = await data_store.get_storage_stats()
        print(f"✅ Memory store working: {stats['storage_type']}")
        
        # Test 3: Component imports
        print("🔧 Testing component imports...")
        from quality_agent import DataQualityAgent
        from complete_processor import CompleteFileProcessor
        from file_processor import FileProcessingAgent
        print("✅ All components imported successfully")
        
        # Test 4: Create sample data
        print("📊 Creating sample data...")
        sample_data = pd.DataFrame({
            'name': ['Alice', 'Bob', 'Charlie'],
            'age': [25, 30, 35],
            'email': ['alice@test.com', 'bob@test.com', 'charlie@test.com']
        })
        
        # Save to data store
        artifact_id = "test-artifact-direct"
        await data_store.save_dataframe(artifact_id, sample_data)
        
        # Verify data was saved
        retrieved_data = await data_store.get_dataframe(artifact_id)
        assert retrieved_data is not None
        assert retrieved_data.shape == sample_data.shape
        print("✅ Data storage and retrieval working")
        
        # Test 5: Test file processor
        print("📁 Testing file processor...")
        file_processor = FileProcessingAgent()
        # Just test that it initializes - we don't need to process actual files
        assert file_processor.supported_formats == ['.csv', '.xlsx', '.xls']
        print("✅ File processor initialized")
        
        print("\n🎉 BASIC INTEGRATION TEST PASSED!")
        print("✅ Core components are working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_conversation_components():
    """Test conversation-specific components."""
    print("\n🧪 Testing Conversation Components")
    print("=" * 40)
    
    try:
        # Test conversation state and intent
        print("🎯 Testing conversation state...")
        from conversation.state_schema import ConversationState, Intent
        
        # Test intent enum
        assert Intent.SHOW_DATA.value == "show_data"
        assert Intent.ANALYZE.value == "analyze"
        print("✅ Intent enum working")
        
        # Test basic conversation state
        state = ConversationState(
            session_id="test",
            user_id="test-user",
            user_message="test message",
            intent=Intent.SHOW_DATA,
            response="",
            conversation_history=[],
            extracted_parameters={},
            data_context=None,
            current_dataframe=None,
            pending_operation=None,
            confirmation_required=False,
            operation_result=None,
            error_message=None,
            error_type=None,
            response_type="info",
            artifact_id=None,
            file_format=None,
            file_path=None,
            sheet_name=None,
            delimiter=None,
            encoding=None,
            next_steps=None,
            suggestions=None,
            retry_count=0,
            dataframe_info=None,
            last_operation=None,
            csv_excel_context=None
        )
        
        assert state["session_id"] == "test"
        assert state["intent"] == Intent.SHOW_DATA
        print("✅ Conversation state working")
        
        # Test nodes directly
        print("🔄 Testing conversation nodes...")
        from conversation.nodes import message_parser_node, context_loader_node
        
        # Test message parser
        test_state = state.copy()
        test_state["user_message"] = "show me the data"
        parsed_state = await message_parser_node(test_state)
        assert parsed_state["intent"] == Intent.SHOW_DATA
        print("✅ Message parser working")
        
        # Test context loader  
        context_state = await context_loader_node(parsed_state)
        assert "data_context" in context_state
        print("✅ Context loader working")
        
        print("\n🎉 CONVERSATION COMPONENTS TEST PASSED!")
        print("✅ LangGraph integration is working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Conversation test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_end_to_end_flow():
    """Test a simplified end-to-end conversation flow."""
    print("\n🧪 Testing End-to-End Flow")
    print("=" * 40)
    
    try:
        # Test conversation graph
        print("🎯 Testing conversation graph...")
        from conversation.conversation_graph import ConversationGraph
        
        conversation_graph = ConversationGraph()
        print("✅ Conversation graph created")
        
        # Test session creation
        session_result = await conversation_graph.start_conversation(
            user_id="test-user"
        )
        assert session_result["status"] == "active"
        session_id = session_result["session_id"]
        print(f"✅ Session created: {session_id}")
        
        # Test message processing
        message_result = await conversation_graph.process_message(
            user_message="show me data",
            session_id=session_id,
            user_id="test-user"
        )
        
        assert "response" in message_result
        assert "intent" in message_result
        print(f"✅ Message processed - Intent: {message_result['intent']}")
        print(f"   Response: {message_result['response'][:50]}...")
        
        print("\n🎉 END-TO-END TEST PASSED!")
        print("✅ Full conversation flow is working!")
        return True
        
    except Exception as e:
        print(f"❌ End-to-end test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all direct integration tests."""
    print("ScioScribe Direct Integration Test")
    print("Testing LangGraph conversation backend integration...")
    print("=" * 60)
    
    # Run tests
    test1 = await test_basic_conversation_flow()
    test2 = await test_conversation_components() 
    test3 = await test_end_to_end_flow()
    
    # Results
    passed_tests = sum([test1, test2, test3])
    total_tests = 3
    
    print("\n" + "=" * 60)
    print("🏁 FINAL RESULTS")
    print("=" * 60)
    print(f"✅ Basic Integration: {'PASS' if test1 else 'FAIL'}")
    print(f"✅ Conversation Components: {'PASS' if test2 else 'FAIL'}")
    print(f"✅ End-to-End Flow: {'PASS' if test3 else 'FAIL'}")
    print("-" * 60)
    print(f"TOTAL: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ LangGraph conversation system is properly integrated!")
        print("✅ Backend integration is working correctly!")
        print("🚀 Ready to proceed with Phase 2.5: Prompt Engineering!")
        return 0
    else:
        print("\n❌ SOME TESTS FAILED!")
        print("⚠️  Check the integration implementation")
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        exit(exit_code)
    except Exception as e:
        print(f"💥 Test suite failed: {str(e)}")
        exit(1) 