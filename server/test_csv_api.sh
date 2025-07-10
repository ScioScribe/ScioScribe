#!/bin/bash

# CSV API Testing Script
BASE_URL="http://localhost:8000"
SESSION_ID="test-$(date +%s)"

echo "🧪 Testing CSV Data Cleaning API"
echo "Session ID: $SESSION_ID"
echo "================================="

# Test 1: Health Check
echo "1. Health Check..."
curl -s -X GET "$BASE_URL/health" | jq '.'
echo

# Test 2: Basic CSV Processing
echo "2. Basic CSV Processing with Greeting..."
RESPONSE1=$(curl -s -X POST "$BASE_URL/api/dataclean/csv-conversation/process" \
  -H "Content-Type: application/json" \
  -d '{
    "csv_data": "name,age,city\nJohn,25,NYC\nJane,,LA\nBob,30,",
    "user_message": "Hi",
    "session_id": "'$SESSION_ID'",
    "user_id": "demo-user"
  }')

echo "$RESPONSE1" | jq '.'
echo

# Test 3: Data Cleaning Request
echo "3. Requesting Data Cleaning..."
RESPONSE2=$(curl -s -X POST "$BASE_URL/api/dataclean/csv-conversation/process" \
  -H "Content-Type: application/json" \
  -d '{
    "csv_data": "name,age,city\nJohn,25,NYC\nJane,,LA\nBob,30,",
    "user_message": "Please clean this data",
    "session_id": "'$SESSION_ID'",
    "user_id": "demo-user"
  }')

echo "$RESPONSE2" | jq '.'
echo

# Test 4: Complex Data with Issues
echo "4. Testing Complex Data with Multiple Issues..."
CSV_COMPLEX="name,age,city,salary\nJohn Doe,25,New York,50000\nJane Smith,,Los Angeles,60000\nJohn Doe,25,New York,50000\nBob Johnson,30,Chicago,\nAlice Brown,35,Boston,70000"

RESPONSE3=$(curl -s -X POST "$BASE_URL/api/dataclean/csv-conversation/process" \
  -H "Content-Type: application/json" \
  -d '{
    "csv_data": "'$CSV_COMPLEX'",
    "user_message": "Analyze this data",
    "session_id": "'$SESSION_ID'-complex",
    "user_id": "demo-user"
  }')

echo "$RESPONSE3" | jq '.'
echo

# Test 5: Missing Values Handling
echo "5. Testing Missing Values Handling..."
RESPONSE4=$(curl -s -X POST "$BASE_URL/api/dataclean/csv-conversation/process" \
  -H "Content-Type: application/json" \
  -d '{
    "csv_data": "name,age,city\nJohn,25,NYC\nJane,,LA\nBob,30,",
    "user_message": "Fill missing values",
    "session_id": "'$SESSION_ID'-missing",
    "user_id": "demo-user"
  }')

echo "$RESPONSE4" | jq '.'
echo

echo "✅ API Testing Complete!"
echo "Check responses above for results." 