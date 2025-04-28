import sys
import os
from sqlalchemy import MetaData

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import Base, engine
from app.models.models import Article, User, user_article_interactions
from migrations.add_description_column import run_migration as add_description_column
from migrations.add_preference_embeddings_column import run_migration as add_preference_embeddings_column

def create_tables():
    """Create database tables"""
    try:
        Base.metadata.create_all(bind=engine)
        print("Database tables created successfully")
        return True
    except Exception as e:
        print(f"Error creating database tables: {e}")
        return False

def drop_tables():
    """Drop all database tables"""
    try:
        meta = MetaData()
        meta.reflect(bind=engine)
        meta.drop_all(bind=engine)
        print("Database tables dropped successfully")
        return True
    except Exception as e:
        print(f"Error dropping database tables: {e}")
        return False

# Simplified version without Alembic dependency
if __name__ == "__main__":
    print("Resetting database...")
    drop_success = drop_tables()

    if drop_success:
        print("Recreating database tables...")
        success = create_tables()

        if success:
            print("Running migrations to ensure all columns exist...")
            description_migration_success = add_description_column()
            preference_embeddings_migration_success = add_preference_embeddings_column()

            if description_migration_success and preference_embeddings_migration_success:
                print("Database reset, initialization, and migrations complete")
                sys.exit(0)
            else:
                print("Tables created but some migrations failed")
                sys.exit(1)
        else:
            print("Database initialization failed")
            sys.exit(1)
    else:
        print("Database reset failed")
        sys.exit(1)