#!/usr/bin/env python3
"""
Simple WebSocket test for CSV conversation endpoint.
"""

import asyncio
import websockets
import json

async def test_csv_websocket():
    uri = "ws://localhost:8000/api/dataclean/csv-conversation/ws/websocket-test-session"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("🔌 Connected to CSV WebSocket!")
            
            # Send a CSV message
            message = {
                "type": "csv_message",
                "data": {
                    "csv_data": "name,age,city\\nJohn,25,NYC\\nJane,,LA\\nBob,30,",
                    "user_message": "Hi, please analyze my data",
                    "user_id": "demo-user"
                }
            }
            
            await websocket.send(json.dumps(message))
            print("📤 Sent CSV message")
            
            # Receive response
            response = await websocket.recv()
            data = json.loads(response)
            print("📥 Received response:")
            print(json.dumps(data, indent=2))
            
    except Exception as e:
        print(f"❌ WebSocket test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_csv_websocket()) 