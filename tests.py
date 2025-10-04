import asyncio
import os
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv()

async def test_connection():
    MONGO_URL = os.getenv("MONGO")
    print(f"Attempting to connect to: {MONGO_URL[:30]}...")
    
    try:
        client = AsyncIOMotorClient(MONGO_URL)
        db = client["budget_tracker"]
        
        # Test the connection
        result = await db.command("ping")
        print(f"✓ MongoDB connection successful: {result}")
        
        # Test a simple find_one
        collection = db["personnel"]
        doc = await collection.find_one({})
        print(f"✓ find_one works! Found doc: {doc}")
        
        client.close()
        print("✓ All tests passed!")
        
    except Exception as e:
        print(f"✗ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_connection())