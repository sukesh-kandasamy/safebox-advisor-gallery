
import asyncio
import os
import aiosqlite
from db.database import init_db, create_default_admin, DATABASE_PATH

async def reset_database():
    print("⚠️  RESETTING DATABASE...")
    
    if os.path.exists(DATABASE_PATH):
        try:
            os.remove(DATABASE_PATH)
            print(f"✓ Removed existing database: {DATABASE_PATH}")
        except Exception as e:
            print(f"❌ Failed to remove database: {e}")
            return

    print("init DB...")
    await init_db()
    print("✓ Tables created")
    
    print("Creating admin...")
    await create_default_admin()
    
    print("✅ Database reset complete!")

if __name__ == "__main__":
    asyncio.run(reset_database())
