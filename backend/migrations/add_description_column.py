import sys
import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Add parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings

def run_migration():
    """Migrate database to add missing columns"""
    try:
        # Connect to database
        conn = psycopg2.connect(settings.DATABASE_URL)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        print("Running database migrations...")
        
        # Check if description column exists in articles table
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'articles' AND column_name = 'description';
        """)
        
        has_description = cursor.fetchone() is not None
        
        # Add description column if it doesn't exist
        if not has_description:
            print("Adding description column to articles table...")
            cursor.execute("""
                ALTER TABLE articles
                ADD COLUMN description TEXT;
            """)
            print("Description column added successfully.")
        else:
            print("Description column already exists, skipping...")
            
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