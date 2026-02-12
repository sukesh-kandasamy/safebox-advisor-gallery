"""
Safebox Blog Database Setup
"""
import aiosqlite
import os
from config import get_settings

settings = get_settings()

DATABASE_PATH = "gallery.db"


async def get_db():
    """Get database connection."""
    db = await aiosqlite.connect(DATABASE_PATH)
    db.row_factory = aiosqlite.Row
    try:
        yield db
    finally:
        await db.close()


async def init_db():
    """Initialize database tables."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Create admins table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                name TEXT NOT NULL,
                profile_image_url TEXT,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create videos table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS videos (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                video_link TEXT NOT NULL,
                youtube_id TEXT,
                next_video_id TEXT,
                order_index INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (next_video_id) REFERENCES videos (id) ON DELETE SET NULL
            )
        """)
        
        # Create notifications table (keeping for potential system alerts, though maybe unused)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                message TEXT NOT NULL,
                link TEXT,
                is_read BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.commit()
        
        # Run migrations for existing databases
        await run_migrations(db)


async def run_migrations(db):
    """Run database migrations for existing tables."""
    # Check if next_video_id column exists in videos table
    cursor = await db.execute("PRAGMA table_info(videos)")
    columns = await cursor.fetchall()
    column_names = [col[1] for col in columns]
    
    # Migration: Add next_video_id column
    if 'next_video_id' not in column_names:
        print("  → Adding 'next_video_id' column to videos table...")
        await db.execute("ALTER TABLE videos ADD COLUMN next_video_id TEXT")
        await db.commit()
        print("  ✓ Migration complete: next_video_id added")
    
    # Migration: Add order_index column
    if 'order_index' not in column_names:
        print("  → Adding 'order_index' column to videos table...")
        await db.execute("ALTER TABLE videos ADD COLUMN order_index INTEGER DEFAULT 0")
        await db.commit()
        print("  ✓ Migration complete: order_index added")
    
    # Migration: Initialize order_index for videos that all have 0
    cursor = await db.execute("SELECT COUNT(*) as cnt FROM videos WHERE order_index = 0")
    zero_count = (await cursor.fetchone())[0]
    cursor = await db.execute("SELECT COUNT(*) as cnt FROM videos")
    total_count = (await cursor.fetchone())[0]
    
    # If all videos have order_index = 0, initialize them sequentially
    if total_count > 0 and zero_count == total_count:
        print("  → Initializing order_index for existing videos...")
        cursor = await db.execute("SELECT id FROM videos ORDER BY created_at ASC")
        videos = await cursor.fetchall()
        for idx, (video_id,) in enumerate(videos):
            await db.execute("UPDATE videos SET order_index = ? WHERE id = ?", (idx, video_id))
        await db.commit()
        print(f"  ✓ Initialized order_index for {len(videos)} videos")


async def create_default_admin():
    """Create default admin user if not exists."""
    from utils.security import get_password_hash
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Check if admin exists
        cursor = await db.execute(
            "SELECT id FROM admins WHERE email = ?",
            (settings.DEFAULT_ADMIN_EMAIL,)
        )
        existing = await cursor.fetchone()
        
        if not existing:
            password_hash = get_password_hash(settings.DEFAULT_ADMIN_PASSWORD)
            await db.execute(
                "INSERT INTO admins (email, password_hash, name) VALUES (?, ?, ?)",
                (settings.DEFAULT_ADMIN_EMAIL, password_hash, settings.DEFAULT_ADMIN_NAME)
            )
            await db.commit()
            print(f"✓ Default admin created: {settings.DEFAULT_ADMIN_EMAIL}")
        else:
            print(f"✓ Admin already exists: {settings.DEFAULT_ADMIN_EMAIL}")
