import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

# Load environment variables
load_dotenv()
# Also load .env.local if it exists
if os.path.exists(".env.local"):
    load_dotenv(".env.local")

# Update this to point to the actual database
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/merge_ai_workflow")

def setup_database():
    try:
        # Import the database modules
        from backend.database.database import engine
        from backend.database.models import Base
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("Database tables created successfully!")
        
    except ImportError as e:
        print(f"Import error: {e}")
        print("Make sure you're running this script from the project root directory.")
    except OperationalError as e:
        print(f"Database connection error: {e}")
        print("Please check your PostgreSQL credentials and ensure PostgreSQL is running.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    setup_database() 