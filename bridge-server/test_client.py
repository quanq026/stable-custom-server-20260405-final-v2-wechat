import asyncio
import websockets
import json
import sys

async def test_client():
    uri = "ws://localhost:8000"
    print(f"Connecting to {uri}...")
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected!")
            
            # Send Hello
            hello_msg = {
                "type": "hello",
                "version": 3,
                "transport": "websocket",
                "audio_params": {
                    "format": "opus",
                    "sample_rate": 16000,
                    "channels": 1,
                    "frame_duration": 60
                }
            }
            await websocket.send(json.dumps(hello_msg))
            print("Sent Hello")

            # Receive Response
            response = await websocket.recv()
            print(f"Received: {response}")
            
            data = json.loads(response)
            if data['type'] == 'hello':
                print("Handshake successful!")
            else:
                print("Handshake failed!")

    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_client())
