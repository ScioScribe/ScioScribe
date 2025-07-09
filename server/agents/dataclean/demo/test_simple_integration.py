#!/usr/bin/env python3
"""
Simple test script to verify LangGraph conversation integration.

This script tests basic functionality to ensure the enhanced nodes
properly integrate with existing data cleaning components.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add paths for imports
current_dir = Path(__file__).parent
sys.path.append(str(current_dir.parent))
sys.path.append(str(current_dir.parent.parent))

async def test_basic_integration():
    """Test basic integration between LangGraph and existing components."""
    print("🔧 Testing LangGraph Backend Integration")
    print("=" * 50)
    
    try:
        # Import components from our local modules
        sys.path.insert(0, str(current_dir.parent))
        from conversation.conversation_graph import ConversationGraph
        from conversation.nodes import message_parser_node, context_loader_node, processing_router_node
        from conversation.state_schema import ConversationState, Intent
        from memory_store import get_data_store
        
        print("✅ Successfully imported LangGraph components")
        
        # Test 1: Initialize conversation graph
        conversation_graph = ConversationGraph()
        print("✅ ConversationGraph initialized")
        
        # Test 2: Test basic state processing
        test_state = ConversationState(
            session_id="test-session",
            user_id="test-user",
            artifact_id=None,
            user_message="show me data",
            intent=Intent.UNKNOWN,
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
        
        # Test message parser
        parsed_state = await message_parser_node(test_state)
        assert parsed_state["intent"] == Intent.SHOW_DATA
        print("✅ Message parser node working")
        
        # Test context loader
        context_state = await context_loader_node(parsed_state)
        print("✅ Context loader node working")
        
        # Test processing router
        router_state = await processing_router_node(context_state)
        assert "operation_result" in router_state
        print("✅ Processing router node working")
        
        # Test 3: Start conversation
        session_result = await conversation_graph.start_conversation(
            user_id="test-user"
        )
        assert session_result["status"] == "active"
        session_id = session_result["session_id"]
        print(f"✅ Started conversation session: {session_id}")
        
        # Test 4: Process message
        message_result = await conversation_graph.process_message(
            user_message="describe my data",
            session_id=session_id,
            user_id="test-user"
        )
        assert "response" in message_result
        assert "intent" in message_result
        print(f"✅ Processed message. Intent: {message_result['intent']}")
        print(f"   Response: {message_result['response'][:100]}...")
        
        # Test 5: Memory store integration
        data_store = get_data_store()
        stats = await data_store.get_storage_stats()
        assert "storage_type" in stats
        print("✅ Memory store integration working")
        
        print("\n🎉 ALL BASIC INTEGRATION TESTS PASSED!")
        print("✅ LangGraph conversation system is properly integrated with existing components")
        return True
        
    except ImportError as e:
        print(f"❌ Import Error: {str(e)}")
        print("   Check if all modules are properly set up")
        return False
        
    except Exception as e:
        print(f"❌ Integration Error: {str(e)}")
        print("   There's an issue with the integration")
        return False


async def test_with_sample_data():
    """Test integration with sample data."""
    print("\n🔧 Testing with Sample Data")
    print("=" * 50)
    
    try:
        import pandas as pd
        from conversation.conversation_graph import ConversationGraph
        from memory_store import get_data_store
        from models import DataArtifact, ProcessingStatus
        from datetime import datetime
        
        # Create sample data
        sample_data = pd.DataFrame({
            'name': ['Alice', 'Bob', 'Charlie'],
            'age': [25, 30, 35],
            'city': ['NYC', 'SF', 'LA']
        })
        
        # Create artifact
        artifact_id = "test-artifact-123"
        data_store = get_data_store()
        
        artifact = DataArtifact(
            artifact_id=artifact_id,
            experiment_id="test",
            owner_id="test-user",
            status=ProcessingStatus.READY_FOR_ANALYSIS,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        await data_store.save_data_artifact(artifact)
        await data_store.save_dataframe(artifact_id, sample_data)
        print("✅ Sample data and artifact created")
        
        # Test conversation with data
        conversation_graph = ConversationGraph()
        
        session_result = await conversation_graph.start_conversation(
            user_id="test-user",
            artifact_id=artifact_id
        )
        
        session_id = session_result["session_id"]
        print(f"✅ Started conversation with data artifact: {session_id}")
        
        # Test data operations
        test_messages = [
            "show me the first 5 rows",
            "describe my dataset", 
            "analyze the data quality"
        ]
        
        for message in test_messages:
            result = await conversation_graph.process_message(
                user_message=message,
                session_id=session_id,
                user_id="test-user",
                artifact_id=artifact_id
            )
            print(f"✅ '{message}' → {result['intent']} → {result['response_type']}")
        
        print("\n🎉 SAMPLE DATA TESTS PASSED!")
        print("✅ LangGraph works correctly with existing data processing components")
        return True
        
    except Exception as e:
        print(f"❌ Sample Data Test Error: {str(e)}")
        return False


async def main():
    """Run the simple integration tests."""
    print("ScioScribe LangGraph Integration Test (Simple)")
    print("Testing enhanced backend integration...\n")
    
    # Test basic integration
    basic_success = await test_basic_integration()
    
    # Test with sample data
    data_success = await test_with_sample_data()
    
    if basic_success and data_success:
        print("\n" + "=" * 60)
        print("🎉 INTEGRATION TEST SUCCESSFUL!")
        print("✅ Backend integration is working correctly")
        print("✅ LangGraph conversation system properly integrates with:")
        print("   - Memory store (data_store)")
        print("   - Data artifacts")
        print("   - Intent classification")
        print("   - Processing router")
        print("   - Existing data cleaning components")
        print("\n🚀 Ready to proceed with Phase 2.5: Prompt Engineering!")
        return 0
    else:
        print("\n" + "=" * 60)
        print("❌ INTEGRATION TEST FAILED!")
        print("⚠️  Fix the integration issues before proceeding")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        exit(exit_code)
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\n💥 Test failed with error: {str(e)}")
        exit(1) 