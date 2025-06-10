import asyncio
import sys
import os
from loguru import logger

# Configure logger to output to console
logger.remove()
logger.add(sys.stderr, level="DEBUG")

# Use the path to make imports work
current_dir = os.getcwd()
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# This is needed to make the imports work from both locations
backend_dir = os.path.join(current_dir, 'backend')
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

async def test_voice_agent():
    """Test only voice agent"""
    logger.info("Testing voice agent")
    
    # Import here after setting up paths
    from agents.voice_agent import voice_agent
    
    # Start voice agent
    voice_running = False
    voice_error = None
    
    try:
        voice_task = asyncio.create_task(voice_agent.start())
        await asyncio.sleep(5)
        voice_running = voice_agent.running
        logger.info(f"Voice agent running: {voice_running}")
        voice_agent.stop()
        await asyncio.sleep(2)
    except Exception as e:
        voice_error = str(e)
        logger.error(f"Voice agent error: {e}")
    
    return {
        "voice_agent_running": voice_running,
        "voice_agent_error": voice_error
    }

async def test_data_entry_agent():
    """Test only data entry agent"""
    logger.info("Testing data entry agent")
    
    # Import here after setting up paths
    from agents.data_entry_agent import DataEntryAgent
    
    # Start data entry agent
    data_entry_running = False
    data_entry_error = None
    
    try:
        data_entry_agent = DataEntryAgent()
        data_entry_task = asyncio.create_task(data_entry_agent.start())
        await asyncio.sleep(5)
        data_entry_running = data_entry_agent.running
        logger.info(f"Data entry agent running: {data_entry_running}")
        data_entry_agent.stop()
        await asyncio.sleep(2)
    except Exception as e:
        data_entry_error = str(e)
        logger.error(f"Data entry agent error: {e}")
    
    return {
        "data_entry_agent_running": data_entry_running,
        "data_entry_agent_error": data_entry_error
    }

async def main():
    """Run tests for both agents separately"""
    logger.info("Starting debug script")
    
    voice_results = await test_voice_agent()
    data_entry_results = await test_data_entry_agent()
    
    logger.info("Test results:")
    logger.info(f"Voice agent: {'Running' if voice_results['voice_agent_running'] else 'Not running'}")
    if voice_results['voice_agent_error']:
        logger.info(f"Voice agent error: {voice_results['voice_agent_error']}")
    
    logger.info(f"Data entry agent: {'Running' if data_entry_results['data_entry_agent_running'] else 'Not running'}")
    if data_entry_results['data_entry_agent_error']:
        logger.info(f"Data entry agent error: {data_entry_results['data_entry_agent_error']}")

if __name__ == "__main__":
    asyncio.run(main()) 