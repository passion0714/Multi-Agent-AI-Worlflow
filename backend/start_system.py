#!/usr/bin/env python3
"""
System Startup Script
This script starts the complete system with proper initialization and health checks
"""
import asyncio
import os
import sys
import signal
import subprocess
import time
from datetime import datetime

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from debug_system import run_full_system_test
from agents.voice_agent import VoiceAgent

class SystemManager:
    """Manages the complete system startup and operation"""
    
    def __init__(self):
        self.voice_agent = None
        self.running = False
        self.processes = []
        
    async def startup_sequence(self):
        """Execute complete system startup sequence"""
        print("🚀 Starting MERGE AI System")
        print("=" * 50)
        print(f"🕒 Startup time: {datetime.utcnow().isoformat()}")
        
        # Step 1: Run system health tests
        print("\n📋 Step 1: Running system health tests...")
        health_passed = await run_full_system_test()
        
        if not health_passed:
            print("\n❌ System health tests failed!")
            print("Please fix the issues above before starting the system.")
            return False
        
        print("\n✅ System health tests passed!")
        
        # Step 2: Initialize Voice Agent
        print("\n📋 Step 2: Initializing Voice Agent...")
        try:
            self.voice_agent = VoiceAgent()
            print("✅ Voice Agent initialized successfully")
        except Exception as e:
            print(f"❌ Failed to initialize Voice Agent: {e}")
            return False
        
        # Step 3: Start Voice Agent
        print("\n📋 Step 3: Starting Voice Agent...")
        try:
            # Start voice agent in background task
            asyncio.create_task(self.voice_agent.start())
            print("✅ Voice Agent started successfully")
            print("🤖 Voice Agent is now processing leads...")
        except Exception as e:
            print(f"❌ Failed to start Voice Agent: {e}")
            return False
        
        # Step 4: System ready
        print("\n🎉 System startup completed successfully!")
        print("\n📊 System Status:")
        print("   ✅ Database: Connected")
        print("   ✅ VAPI Service: Connected")
        print("   ✅ Voice Agent: Running")
        print("   ✅ Call Processing: Active")
        
        self.running = True
        return True
    
    async def monitor_system(self):
        """Monitor system health and components"""
        print("\n🔍 Starting system monitoring...")
        
        while self.running:
            try:
                # Check voice agent status
                if self.voice_agent and not self.voice_agent.running:
                    print("⚠️  Voice Agent stopped - attempting restart...")
                    try:
                        await self.voice_agent.start()
                        print("✅ Voice Agent restarted")
                    except Exception as e:
                        print(f"❌ Failed to restart Voice Agent: {e}")
                
                # Wait before next check
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                print(f"❌ Error in system monitoring: {e}")
                await asyncio.sleep(120)  # Wait longer on error
    
    async def shutdown_sequence(self):
        """Execute graceful system shutdown"""
        print("\n🛑 Starting system shutdown...")
        
        self.running = False
        
        # Stop voice agent
        if self.voice_agent:
            print("🤖 Stopping Voice Agent...")
            self.voice_agent.stop()
            
            # Show final statistics
            stats = self.voice_agent.get_statistics()
            print(f"📊 Final Voice Agent Statistics:")
            print(f"   Total attempts: {stats.get('total_attempts', 0)}")
            print(f"   Successful calls: {stats.get('successful_vapi_calls', 0)}")
            print(f"   Success rate: {stats.get('success_rate', 0):.1f}%")
        
        # Stop any other processes
        for process in self.processes:
            try:
                process.terminate()
                process.wait(timeout=5)
                print("✅ Process terminated")
            except Exception as e:
                print(f"⚠️  Error terminating process: {e}")
        
        print("✅ System shutdown completed")
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            print(f"\n🛑 Received signal {signum}, initiating shutdown...")
            asyncio.create_task(self.shutdown_sequence())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

async def start_backend_server():
    """Start the FastAPI backend server"""
    print("🌐 Starting FastAPI backend server...")
    
    try:
        # Start FastAPI server using uvicorn
        process = subprocess.Popen([
            sys.executable, "-m", "uvicorn",
            "app:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload"
        ], cwd=os.path.dirname(os.path.abspath(__file__)))
        
        # Give server time to start
        await asyncio.sleep(3)
        
        # Check if process is still running
        if process.poll() is None:
            print("✅ FastAPI backend server started on http://0.0.0.0:8000")
            return process
        else:
            print("❌ FastAPI backend server failed to start")
            return None
            
    except Exception as e:
        print(f"❌ Error starting backend server: {e}")
        return None

async def main():
    """Main startup function"""
    system_manager = SystemManager()
    system_manager.setup_signal_handlers()
    
    try:
        # Option to run with or without web server
        run_server = input("Start FastAPI backend server? (y/n): ").lower().strip()
        
        backend_process = None
        if run_server in ['y', 'yes']:
            backend_process = await start_backend_server()
            if backend_process:
                system_manager.processes.append(backend_process)
        
        # Execute startup sequence
        startup_success = await system_manager.startup_sequence()
        
        if not startup_success:
            print("\n❌ System startup failed!")
            return
        
        # Show system URLs
        print("\n🌐 System URLs:")
        if backend_process:
            print("   📊 Health Dashboard: http://localhost:8000/health/system")
            print("   📞 Call Health: http://localhost:8000/health/calls")
            print("   🔧 VAPI Health: http://localhost:8000/health/vapi")
            print("   📋 API Docs: http://localhost:8000/docs")
        
        print("\n🎮 System Controls:")
        print("   Ctrl+C: Graceful shutdown")
        print("   View logs for real-time system activity")
        
        # Start monitoring
        await system_manager.monitor_system()
        
    except KeyboardInterrupt:
        print("\n🛑 Received keyboard interrupt")
    except Exception as e:
        print(f"\n❌ System error: {e}")
    finally:
        await system_manager.shutdown_sequence()

if __name__ == "__main__":
    print("🔧 MERGE AI System Manager")
    print("=" * 30)
    print("This script will start the complete system including:")
    print("   - System health checks")
    print("   - Voice agent for call processing")
    print("   - Optional FastAPI backend server")
    print("   - System monitoring")
    
    print(f"\n⚙️  Environment: {os.getenv('ENVIRONMENT', 'development')}")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"\n💥 Fatal error: {e}")
        sys.exit(1) 