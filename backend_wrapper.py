"""
Backend Wrapper Module

This module sets up the Python path correctly so that imports from both
'database' and 'backend.database' styles will work.
"""

import os
import sys
import asyncio
from loguru import logger

# Set up paths properly
current_dir = os.getcwd()
backend_dir = os.path.join(current_dir, 'backend')

# Add paths to sys.path if not already there
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

async def run_agents():
    """Run both agents with proper path setup"""
    logger.info("Starting agents through wrapper")
    
    try:
        # Now we can import from either style
        from backend.agents.voice_agent import voice_agent
        from backend.agents.data_entry_agent import DataEntryAgent
        
        # Create data entry agent
        data_entry_agent = DataEntryAgent()
        
        # Start both agents
        logger.info("Starting voice agent")
        voice_task = asyncio.create_task(voice_agent.start())
        
        logger.info("Starting data entry agent")
        data_entry_task = asyncio.create_task(data_entry_agent.start())
        
        # Wait for both to initialize
        await asyncio.sleep(10)
        
        # Log status
        logger.info(f"Voice agent running: {voice_agent.running}")
        logger.info(f"Data entry agent running: {data_entry_agent.running}")
        
        # Keep running until interrupted
        try:
            while True:
                await asyncio.sleep(10)
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt detected")
        finally:
            # Stop both agents
            logger.info("Stopping agents")
            voice_agent.stop()
            data_entry_agent.stop()
            
            # Wait for cleanup
            await asyncio.sleep(5)
    
    except Exception as e:
        logger.error(f"Error in run_agents: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    # Configure logger
    logger.remove()
    logger.add(sys.stderr, level="DEBUG")
    
    # Run the agents
    try:
        asyncio.run(run_agents())
    except KeyboardInterrupt:
        logger.info("Program terminated by user") 