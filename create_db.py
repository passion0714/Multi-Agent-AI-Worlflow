import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
import getpass

# Load environment variables
load_dotenv()

def create_database():
    # Prompt for database credentials
    print("Please enter your PostgreSQL credentials:")
    username = input("Username (default: postgres): ") or "postgres"
    password = getpass.getpass("Password: ")
    host = input("Host (default: localhost): ") or "localhost"
    port = input("Port (default: 5432): ") or "5432"
    
    # Connect to the default postgres database
    DATABASE_URL = f"postgresql://{username}:{password}@{host}:{port}/postgres"
    TARGET_DB = "merge_ai_workflow"
    
    try:
        # Create a connection
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            # Commit any open transaction
            conn.execute(text("COMMIT"))
            
            # Check if the target database already exists
            result = conn.execute(text(f"SELECT 1 FROM pg_database WHERE datname = '{TARGET_DB}'"))
            if result.fetchone():
                print(f"Database '{TARGET_DB}' already exists.")
                return
            
            # Create the database
            conn.execute(text(f"CREATE DATABASE {TARGET_DB}"))
            print(f"Database '{TARGET_DB}' created successfully!")
            
            # Save connection string to .env.local
            conn_string = f"postgresql://{username}:{password}@{host}:{port}/{TARGET_DB}"
            with open(".env.local", "w") as f:
                f.write(f"DATABASE_URL={conn_string}\n")
                f.write("SECRET_KEY=develop_key_12345\n")
                f.write("DEBUG=True\n")
                f.write("LOG_LEVEL=INFO\n")
            print("Connection details saved to .env.local")
    
    except OperationalError as e:
        print(f"Database connection error: {e}")
        print("Please check your PostgreSQL credentials and ensure PostgreSQL is running.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    create_database() 