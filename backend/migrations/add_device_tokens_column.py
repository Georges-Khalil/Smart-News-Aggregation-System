import sys
import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Add parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings

def run_migration():
    """Migrate database to add device_tokens column for future push notifications"""
    try:
        # Connect to database
        conn = psycopg2.connect(settings.DATABASE_URL)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        print("Running device_tokens column migration...")
        
        # Check if device_tokens column exists in users table
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = 'device_tokens';
        """)
        
        has_device_tokens = cursor.fetchone() is not None
        
        # Add device_tokens column if it doesn't exist
        if not has_device_tokens:
            print("Adding device_tokens column to users table...")
            cursor.execute("""
                ALTER TABLE users
                ADD COLUMN device_tokens JSONB DEFAULT '[]'::jsonb;
            """)
            print("device_tokens column added successfully.")
        else:
            print("device_tokens column already exists, skipping...")
            
        # Close connections
        cursor.close()
        conn.close()
        
        return True
    except Exception as e:
        print(f"Error during migration: {e}")
        return False

if __name__ == "__main__":
    success = run_migration()
    
    if success:
        print("Migration completed successfully")
        sys.exit(0)
    else:
        print("Migration failed")
        sys.exit(1)