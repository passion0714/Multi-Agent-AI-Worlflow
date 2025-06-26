#!/usr/bin/env python3
"""
Test Voice Agent Script
Quick test to verify voice agent functionality
"""
import asyncio
import sys
import os

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.voice_agent import VoiceAgent
from database.database import get_db_session
from database.models import Lead, LeadStatus

async def test_voice_agent():
    """Test voice agent functionality"""
    print("🤖 Testing Voice Agent...")
    
    # Initialize voice agent
    voice_agent = VoiceAgent()
    print("✅ Voice Agent initialized successfully")
    print(f"📊 Initial statistics: {voice_agent.get_statistics()}")
    
    # Check for pending leads
    db = get_db_session()
    try:
        pending_leads = db.query(Lead).filter(Lead.status == LeadStatus.PENDING).count()
        print(f"📋 Pending leads: {pending_leads}")
        
        if pending_leads == 0:
            print("⚠️  No pending leads found - nothing to test")
            return
            
    finally:
        db.close()
    
    print("🚀 Starting voice agent for 30 seconds...")
    
    # Start the voice agent in background
    task = asyncio.create_task(voice_agent.start())
    
    # Wait 30 seconds
    await asyncio.sleep(30)
    
    # Stop the voice agent
    voice_agent.stop()
    await asyncio.sleep(2)  # Give it time to stop
    
    print("🛑 Voice agent stopped")
    print(f"📊 Final statistics: {voice_agent.get_statistics()}")
    
    # Check lead status changes
    db = get_db_session()
    try:
        status_counts = {}
        for status in LeadStatus:
            count = db.query(Lead).filter(Lead.status == status).count()
            if count > 0:
                status_counts[status.value] = count
        
        print("📊 Final lead status distribution:")
        for status, count in status_counts.items():
            print(f"   {status}: {count}")
            
    finally:
        db.close()

if __name__ == "__main__":
    print("🧪 Voice Agent Test")
    print("=" * 30)
    
    try:
        asyncio.run(test_voice_agent())
        print("\n✅ Test completed successfully!")
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed: {e}") 