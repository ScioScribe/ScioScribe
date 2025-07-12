#!/usr/bin/env python3

"""
Test suite for row operations functionality.

This test suite validates the newly implemented row addition and deletion
capabilities in the data cleaning system.
"""

import asyncio
import logging
import os
import sys
from typing import Dict, Any
import pandas as pd

# Add the parent directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.dataclean.quality_agent import DataQualityAgent
from agents.dataclean.csv_processor import CSVDirectProcessor
from agents.dataclean.conversation.csv_conversation_graph import CSVConversationGraph
from agents.dataclean.models import CSVMessageRequest

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sample test data
SAMPLE_CSV_DATA = """Name,Age,Department,Salary
John Doe,30,Engineering,75000
Jane Smith,25,Marketing,65000
Bob Johnson,35,Engineering,80000
Alice Brown,28,HR,55000
Charlie Davis,32,Sales,70000"""

class RowOperationsTestSuite:
    """Test suite for row operations functionality."""
    
    def __init__(self):
        """Initialize the test suite."""
        self.quality_agent = None
        self.csv_processor = None
        self.conversation_graph = None
        self.setup_agents()
    
    def setup_agents(self):
        """Set up the necessary agents for testing."""
        try:
            from config import get_openai_client
            openai_client = get_openai_client()
            
            if openai_client:
                self.quality_agent = DataQualityAgent(openai_client)
                self.csv_processor = CSVDirectProcessor(openai_client)
                self.conversation_graph = CSVConversationGraph(openai_client)
                logger.info("✅ Agents initialized successfully")
            else:
                logger.warning("⚠️  OpenAI client not available - tests will be limited")
                
        except Exception as e:
            logger.error(f"❌ Error setting up agents: {str(e)}")
            
    async def test_add_row_detection(self):
        """Test detection of add row operations."""
        logger.info("\n🧪 Testing add row detection...")
        
        if not self.quality_agent:
            logger.warning("⚠️  Quality agent not available - skipping test")
            return
        
        # Create test DataFrame
        df = pd.read_csv(pd.io.common.StringIO(SAMPLE_CSV_DATA))
        
        # Test cases for add row detection
        test_cases = [
            {
                "message": "Add a new row with Name=Sarah Lee, Age=29, Department=IT, Salary=72000",
                "expected_detected": True,
                "expected_type": "add_row"
            },
            {
                "message": "Insert a new entry for Mike Wilson",
                "expected_detected": True,
                "expected_type": "add_row"
            },
            {
                "message": "Create a row with default values",
                "expected_detected": True,
                "expected_type": "add_row"
            },
            {
                "message": "Clean the data and remove duplicates",
                "expected_detected": False,
                "expected_type": "none"
            }
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            try:
                result = await self.quality_agent.detect_row_operations(test_case["message"], df)
                
                detected = result.get("operation_detected", False)
                operation_type = result.get("operation_type", "none")
                
                if detected == test_case["expected_detected"] and operation_type == test_case["expected_type"]:
                    logger.info(f"✅ Test {i}: Detection correctly identified - {operation_type}")
                else:
                    logger.error(f"❌ Test {i}: Expected {test_case['expected_detected']}/{test_case['expected_type']}, got {detected}/{operation_type}")
                    
            except Exception as e:
                logger.error(f"❌ Test {i}: Error during detection - {str(e)}")
    
    async def test_delete_row_detection(self):
        """Test detection of delete row operations."""
        logger.info("\n🧪 Testing delete row detection...")
        
        if not self.quality_agent:
            logger.warning("⚠️  Quality agent not available - skipping test")
            return
        
        # Create test DataFrame
        df = pd.read_csv(pd.io.common.StringIO(SAMPLE_CSV_DATA))
        
        # Test cases for delete row detection
        test_cases = [
            {
                "message": "Delete the row where Name is 'John Doe'",
                "expected_detected": True,
                "expected_type": "delete_row"
            },
            {
                "message": "Remove all rows where Department is 'HR'",
                "expected_detected": True,
                "expected_type": "delete_row"
            },
            {
                "message": "Delete row at index 2",
                "expected_detected": True,
                "expected_type": "delete_row"
            },
            {
                "message": "Analyze the data quality",
                "expected_detected": False,
                "expected_type": "none"
            }
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            try:
                result = await self.quality_agent.detect_row_operations(test_case["message"], df)
                
                detected = result.get("operation_detected", False)
                operation_type = result.get("operation_type", "none")
                
                if detected == test_case["expected_detected"] and operation_type == test_case["expected_type"]:
                    logger.info(f"✅ Test {i}: Detection correctly identified - {operation_type}")
                else:
                    logger.error(f"❌ Test {i}: Expected {test_case['expected_detected']}/{test_case['expected_type']}, got {detected}/{operation_type}")
                    
            except Exception as e:
                logger.error(f"❌ Test {i}: Error during detection - {str(e)}")
    
    async def test_add_row_execution(self):
        """Test execution of add row operations."""
        logger.info("\n🧪 Testing add row execution...")
        
        if not self.quality_agent:
            logger.warning("⚠️  Quality agent not available - skipping test")
            return
        
        # Create test DataFrame
        df = pd.read_csv(pd.io.common.StringIO(SAMPLE_CSV_DATA))
        original_length = len(df)
        
        # Test add row with specific values
        message = "Add a new row with Name=Sarah Lee, Age=29, Department=IT, Salary=72000"
        
        try:
            # Step 1: Detect operation
            detection_result = await self.quality_agent.detect_row_operations(message, df)
            
            if not detection_result.get("operation_detected", False):
                logger.error("❌ Add row operation not detected")
                return
            
            # Step 2: Parse details
            operation_details = await self.quality_agent.parse_row_operation_details(
                message, "add_row", df
            )
            
            if not operation_details.get("success", False):
                logger.error("❌ Failed to parse add row details")
                return
            
            # Step 3: Validate operation
            validation_result = await self.quality_agent.validate_row_operation(
                "add_row", operation_details, df
            )
            
            if not validation_result.get("valid", False):
                logger.error(f"❌ Add row validation failed: {validation_result.get('error')}")
                return
            
            # Step 4: Execute operation
            execution_result = await self.quality_agent.execute_row_operation(
                "add_row", validation_result, df
            )
            
            if not execution_result.get("success", False):
                logger.error(f"❌ Add row execution failed: {execution_result.get('error')}")
                return
            
            modified_df = execution_result.get("modified_df")
            new_length = len(modified_df)
            
            if new_length == original_length + 1:
                logger.info(f"✅ Add row successful: {original_length} -> {new_length} rows")
                
                # Check if the new row was added correctly
                new_row = modified_df.iloc[-1]  # Last row should be the new one
                logger.info(f"✅ New row added: {new_row.to_dict()}")
            else:
                logger.error(f"❌ Expected {original_length + 1} rows, got {new_length}")
                
        except Exception as e:
            logger.error(f"❌ Error during add row execution: {str(e)}")
    
    async def test_delete_row_execution(self):
        """Test execution of delete row operations."""
        logger.info("\n🧪 Testing delete row execution...")
        
        if not self.quality_agent:
            logger.warning("⚠️  Quality agent not available - skipping test")
            return
        
        # Create test DataFrame
        df = pd.read_csv(pd.io.common.StringIO(SAMPLE_CSV_DATA))
        original_length = len(df)
        
        # Test delete row by criteria
        message = "Delete the row where Name is 'John Doe'"
        
        try:
            # Step 1: Detect operation
            detection_result = await self.quality_agent.detect_row_operations(message, df)
            
            if not detection_result.get("operation_detected", False):
                logger.error("❌ Delete row operation not detected")
                return
            
            # Step 2: Parse details
            operation_details = await self.quality_agent.parse_row_operation_details(
                message, "delete_row", df
            )
            
            if not operation_details.get("success", False):
                logger.error("❌ Failed to parse delete row details")
                return
            
            # Step 3: Validate operation
            validation_result = await self.quality_agent.validate_row_operation(
                "delete_row", operation_details, df
            )
            
            if not validation_result.get("valid", False):
                logger.error(f"❌ Delete row validation failed: {validation_result.get('error')}")
                return
            
            # Step 4: Execute operation
            execution_result = await self.quality_agent.execute_row_operation(
                "delete_row", validation_result, df
            )
            
            if not execution_result.get("success", False):
                logger.error(f"❌ Delete row execution failed: {execution_result.get('error')}")
                return
            
            modified_df = execution_result.get("modified_df")
            new_length = len(modified_df)
            
            if new_length == original_length - 1:
                logger.info(f"✅ Delete row successful: {original_length} -> {new_length} rows")
                
                # Check if the correct row was deleted
                john_doe_rows = modified_df[modified_df['Name'] == 'John Doe']
                if len(john_doe_rows) == 0:
                    logger.info("✅ John Doe row successfully deleted")
                else:
                    logger.error("❌ John Doe row was not deleted")
                    
            else:
                logger.error(f"❌ Expected {original_length - 1} rows, got {new_length}")
                
        except Exception as e:
            logger.error(f"❌ Error during delete row execution: {str(e)}")
    
    async def test_conversation_integration(self):
        """Test row operations integration with conversation graph."""
        logger.info("\n🧪 Testing conversation integration...")
        
        if not self.conversation_graph:
            logger.warning("⚠️  Conversation graph not available - skipping test")
            return
        
        session_id = "test_row_operations_session"
        
        # Test add row through conversation
        try:
            add_request = CSVMessageRequest(
                csv_data=SAMPLE_CSV_DATA,
                user_message="Add a new row with Name=Test User, Age=30, Department=QA, Salary=60000",
                session_id=session_id,
                user_id="test_user"
            )
            
            add_response = await self.conversation_graph.process_csv_conversation(add_request)
            
            if add_response.success:
                logger.info("✅ Add row conversation successful")
                logger.info(f"Response: {add_response.response_message}")
                
                # Test delete row through conversation
                delete_request = CSVMessageRequest(
                    csv_data=add_response.cleaned_csv or add_response.original_csv,
                    user_message="Delete the row where Name is 'Test User'",
                    session_id=session_id,
                    user_id="test_user"
                )
                
                delete_response = await self.conversation_graph.process_csv_conversation(delete_request)
                
                if delete_response.success:
                    logger.info("✅ Delete row conversation successful")
                    logger.info(f"Response: {delete_response.response_message}")
                else:
                    logger.error(f"❌ Delete row conversation failed: {delete_response.error_message}")
                    
            else:
                logger.error(f"❌ Add row conversation failed: {add_response.error_message}")
                
        except Exception as e:
            logger.error(f"❌ Error during conversation integration test: {str(e)}")
    
    async def test_edge_cases(self):
        """Test edge cases and error handling."""
        logger.info("\n🧪 Testing edge cases...")
        
        if not self.quality_agent:
            logger.warning("⚠️  Quality agent not available - skipping test")
            return
        
        # Create test DataFrame
        df = pd.read_csv(pd.io.common.StringIO(SAMPLE_CSV_DATA))
        
        # Test cases for edge cases
        test_cases = [
            {
                "name": "Add row with missing columns",
                "message": "Add a row with Name=Incomplete User",
                "operation": "add_row",
                "should_succeed": True
            },
            {
                "name": "Delete non-existent row",
                "message": "Delete the row where Name is 'Non-existent User'",
                "operation": "delete_row",
                "should_succeed": True  # Should succeed with 0 rows affected
            },
            {
                "name": "Delete with invalid criteria",
                "message": "Delete the row where NonExistentColumn is 'value'",
                "operation": "delete_row",
                "should_succeed": True  # Should succeed with warnings
            },
            {
                "name": "Add row with invalid column",
                "message": "Add a row with InvalidColumn=value",
                "operation": "add_row",
                "should_succeed": True  # Should succeed with warnings
            }
        ]
        
        for test_case in test_cases:
            try:
                logger.info(f"Testing: {test_case['name']}")
                
                # Detect operation
                detection_result = await self.quality_agent.detect_row_operations(test_case["message"], df)
                
                if not detection_result.get("operation_detected", False):
                    logger.warning(f"⚠️  {test_case['name']}: Operation not detected")
                    continue
                
                # Parse details
                operation_details = await self.quality_agent.parse_row_operation_details(
                    test_case["message"], test_case["operation"], df
                )
                
                # Validate operation
                validation_result = await self.quality_agent.validate_row_operation(
                    test_case["operation"], operation_details, df
                )
                
                if validation_result.get("valid", False):
                    # Execute operation
                    execution_result = await self.quality_agent.execute_row_operation(
                        test_case["operation"], validation_result, df
                    )
                    
                    if execution_result.get("success", False):
                        logger.info(f"✅ {test_case['name']}: Handled successfully")
                    else:
                        logger.error(f"❌ {test_case['name']}: Execution failed")
                else:
                    logger.info(f"✅ {test_case['name']}: Validation correctly failed")
                    
            except Exception as e:
                logger.error(f"❌ {test_case['name']}: Error - {str(e)}")
    
    async def run_all_tests(self):
        """Run all tests in the suite."""
        logger.info("🚀 Starting Row Operations Test Suite")
        logger.info("=" * 50)
        
        # Run all tests
        await self.test_add_row_detection()
        await self.test_delete_row_detection()
        await self.test_add_row_execution()
        await self.test_delete_row_execution()
        await self.test_conversation_integration()
        await self.test_edge_cases()
        
        logger.info("=" * 50)
        logger.info("✅ Row Operations Test Suite completed")


async def main():
    """Main test function."""
    test_suite = RowOperationsTestSuite()
    await test_suite.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main()) 