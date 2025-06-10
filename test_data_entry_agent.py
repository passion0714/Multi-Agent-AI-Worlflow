import asyncio
import sys
import os
import traceback
from loguru import logger

# Configure logger to output to console
logger.remove()
logger.add(sys.stderr, level="DEBUG")

# Set up paths for imports
current_dir = os.getcwd()
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

backend_dir = os.path.join(current_dir, 'backend')
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

async def test_data_entry_agent():
    """Test only the data entry agent with detailed error reporting"""
    logger.info("Starting data entry agent test")
    
    try:
        # Import the agent class
        from agents.data_entry_agent import DataEntryAgent
        logger.info("Successfully imported DataEntryAgent class")
        
        # Check if all dependencies are properly imported
        try:
            from playwright.async_api import async_playwright
            logger.info("Playwright import successful")
        except ImportError as e:
            logger.error(f"Playwright import error: {e}")
            logger.error("Run: pip install playwright && python -m playwright install")
            return
        
        try:
            from database.database import get_db_session
            logger.info("Database import successful")
        except ImportError as e:
            logger.error(f"Database import error: {e}")
            return
            
        try:
            from database.models import Lead, LeadStatus, DataEntryLog
            logger.info("Models import successful")
        except ImportError as e:
            logger.error(f"Models import error: {e}")
            return
            
        try:
            from services.leadhoop_service import EnhancedLeadHoopService
            logger.info("LeadHoop service import successful")
        except ImportError as e:
            logger.error(f"LeadHoop service import error: {e}")
            return
        
        # Create the agent instance
        logger.info("Creating DataEntryAgent instance")
        data_entry_agent = DataEntryAgent()
        
        # Start the agent
        logger.info("Starting data entry agent")
        task = asyncio.create_task(data_entry_agent.start())
        
        # Wait for a short time to see if it starts successfully
        await asyncio.sleep(10)
        
        # Check if the agent is running
        is_running = data_entry_agent.running
        logger.info(f"Data entry agent running: {is_running}")
        
        # Stop the agent
        logger.info("Stopping data entry agent")
        data_entry_agent.stop()
        
        # Wait for cleanup
        await asyncio.sleep(5)
        
        # Check for any exceptions in the task
        if task.done():
            if task.exception():
                logger.error(f"Task exception: {task.exception()}")
                logger.error(traceback.format_exception(type(task.exception()), task.exception(), task.exception().__traceback__))
            else:
                logger.info("Task completed normally")
        
        return is_running
        
    except Exception as e:
        logger.error(f"Error during test: {e}")
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    asyncio.run(test_data_entry_agent()) 