#!/usr/bin/env python
import os
import sys
import uvicorn
import logging
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("app.log")
    ]
)

# Set up paths properly
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(current_dir, 'backend')

# Add paths to sys.path if not already there
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
    logging.info(f"Added {current_dir} to sys.path")

if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
    logging.info(f"Added {backend_dir} to sys.path")

logging.info(f"Python version: {sys.version}")
logging.info(f"Current directory: {os.getcwd()}")
logging.info(f"sys.path: {sys.path}")

if __name__ == "__main__":
    logging.info("Starting MERGE AI Multi-Agent Application")
    
    try:
        # Check for required dependencies
        import httpx
        logging.info("httpx module loaded successfully")
        
        # Print out the data entry agent class details
        try:
            from backend.agents.data_entry_agent import data_entry_agent
            logging.info(f"Data entry agent loaded successfully: {data_entry_agent.__class__.__name__}")
            logging.info(f"Data entry agent running: {data_entry_agent.running}")
        except Exception as agent_error:
            logging.error(f"Error loading data entry agent: {agent_error}")
            traceback.print_exc()
        
        # Start the FastAPI application with Uvicorn
        logging.info("Starting FastAPI application with Uvicorn")
        uvicorn.run(
            "backend.main:app", 
            host="0.0.0.0", 
            port=8000, 
            reload=True,
            log_level="debug"
        )
    except ImportError as e:
        logging.error(f"Missing required dependency: {e}")
        traceback.print_exc()
        print(f"Error: Missing required dependency: {e}")
        print("Please install all dependencies with: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Error starting application: {e}")
        traceback.print_exc()
        print(f"Error starting application: {e}")
        sys.exit(1) 