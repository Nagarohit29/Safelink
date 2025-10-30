#!/usr/bin/env python3
"""Test WebSocket connection to SafeLink backend"""
import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://localhost:8000/ws/updates"
    
    try:
        print(f"🔌 Connecting to {uri}...")
        
        # Increase timeout to 30 seconds
        async with websockets.connect(uri, ping_timeout=30, close_timeout=30) as websocket:
            print("✅ Connected successfully!")
            print(f"📊 Connection state: {websocket.state}")
            
            # Send a ping
            print("� Sending ping...")
            await websocket.send("ping")
            
            # Wait for response
            print("📡 Waiting for response...")
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"📨 Received: {message}")
            except asyncio.TimeoutError:
                print("⏱️  No response received (timeout)")
            
            print("✅ WebSocket test completed successfully!")
            
    except websockets.exceptions.InvalidStatusCode as e:
        print(f"❌ Invalid status code: {e}")
    except ConnectionRefusedError:
        print("❌ Connection refused! Is the backend running on port 8000?")
    except asyncio.TimeoutError:
        print("❌ Connection timeout! Backend is not responding to WebSocket handshake.")
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket())
