import asyncio, websockets

async def test_ws():
    url = "wss://api.hyperliquid.xyz/ws"
    try:
        async with websockets.connect(url) as ws:
            print("Connected!")
            await ws.send("ping")
            print("Ping sent!")
            msg = await ws.recv()
            print("Received:", msg)
    except Exception as e:
        print("WS error:", e)

asyncio.run(test_ws())
