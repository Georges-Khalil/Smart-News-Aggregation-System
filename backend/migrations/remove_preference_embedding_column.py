"""Migration script to remove the preference_embedding column which is now redundant."""

import sys
import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import traceback

# Add the parent directory to the Python path to allow importing from backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.core.config import settings

def run_migration():
    """Migrate database to remove the preference_embedding column"""
    try:
        # Connect to database
        conn = psycopg2.connect(settings.DATABASE_URL)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        print("Running remove_preference_embedding_column migration...")
        
        # Check if preference_embedding column exists in users table
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = 'preference_embedding';
        """)
        
        has_preference_embedding = cursor.fetchone() is not None
        
        # Remove preference_embedding column if it exists
        if has_preference_embedding:
            print("Removing preference_embedding column from users table...")
            
            # Since we don't care about preserving the data, we'll simply drop the column
            cursor.execute("""
                ALTER TABLE users
                DROP COLUMN preference_embedding;
            """)
            print("preference_embedding column removed successfully.")
        else:
            print("preference_embedding column doesn't exist, skipping...")
            
        # Close connections
        cursor.close()
        conn.close()
        
        return True
    except Exception as e:
        print(f"Error during migration: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    run_migration()