import sys
import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Add parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings

def run_migration():
    """Update all articles with 'No Image' as image value to NULL"""
    try:
        # Connect to database
        conn = psycopg2.connect(settings.DATABASE_URL)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        print("Running migration to fix 'No Image' values...")
        
        # Get count of records with 'No Image'
        cursor.execute("""
            SELECT COUNT(*) 
            FROM articles 
            WHERE image = 'No Image';
        """)
        count = cursor.fetchone()[0]
        print(f"Found {count} articles with 'No Image' value")
        
        # Update all records with 'No Image' to NULL
        cursor.execute("""
            UPDATE articles
            SET image = NULL
            WHERE image = 'No Image';
        """)
        
        print(f"Successfully updated {count} articles from 'No Image' to NULL")
            
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