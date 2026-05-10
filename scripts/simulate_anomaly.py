import asyncio
import httpx
import sys
import os

async def run_simulation():
    print("🚀 Simulating OBSTRUCTED_SENSOR Anomaly via dedicated endpoint...")
    print("-------------------------------------------------")
    
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post("http://localhost:8000/api/v1/simulate-anomaly")
            print(f"📡 API Response: {res.status_code}")
            if res.status_code == 200:
                print("✅ Successfully triggered anomaly!")
                print("\n👀 WHAT TO CHECK:")
                print("1. Look at the Admin Dashboard -> Fusion Analysis. You should see a YELLOW Anomaly Banner.")
                print("2. Look at the Water Level Card. It should show a warning icon.")
                print("3. Check the Responder App. A 'Maintenance' notification should have been pushed!")
            else:
                print(f"❌ Failed: {res.text}")
    except httpx.ConnectError:
        print("❌ Could not connect to backend. Is it running? (cd agos-backend && uvicorn app.main:app --reload)")

if __name__ == "__main__":
    asyncio.run(run_simulation())
