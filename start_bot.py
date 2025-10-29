#!/usr/bin/env python3
"""
Startup script for AI Discord Bot with Multi-Model LLM System
Runs both the Discord bot and web dashboard server
"""

import asyncio
import subprocess
import sys
import os
import signal
import time
from threading import Thread
import webbrowser

def run_discord_bot():
    """Run the Discord bot"""
    print("🤖 Starting Discord Bot...")
    try:
        subprocess.run([sys.executable, "main.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Discord bot failed to start: {e}")
    except KeyboardInterrupt:
        print("🛑 Discord bot stopped by user")

def run_web_server():
    """Run the Flask web server"""
    print("🌐 Starting Web Dashboard Server...")
    try:
        subprocess.run([sys.executable, "web_server.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Web server failed to start: {e}")
    except KeyboardInterrupt:
        print("🛑 Web server stopped by user")

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print("\n🛑 Shutting down services...")
    sys.exit(0)

def main():
    """Main startup function"""
    print("=" * 60)
    print("🚀 AI Discord Bot - Multi-Model LLM System")
    print("=" * 60)
    print()
    
    # Check if required files exist
    required_files = ["main.py", "web_server.py", "model_manager.py", "config.py"]
    missing_files = [f for f in required_files if not os.path.exists(f)]
    
    if missing_files:
        print(f"❌ Missing required files: {', '.join(missing_files)}")
        print("Please ensure all files are present before starting.")
        return
    
    # Check if config is set up
    try:
        from config import DISCORD_TOKEN, OPENAI_API_KEY, GEMINI_API_KEY
        if DISCORD_TOKEN == "YOUR_DISCORD_BOT_TOKEN" or not DISCORD_TOKEN:
            print("⚠️  Warning: DISCORD_TOKEN not set in config.py")
        if not OPENAI_API_KEY and not GEMINI_API_KEY:
            print("⚠️  Warning: No API keys configured. Bot will use fallback responses.")
    except ImportError:
        print("❌ Could not import config.py. Please check your configuration.")
        return
    
    print("📋 System Information:")
    print(f"   • Python Version: {sys.version}")
    print(f"   • Working Directory: {os.getcwd()}")
    print(f"   • Discord Bot: main.py")
    print(f"   • Web Dashboard: web_server.py")
    print(f"   • Model Manager: model_manager.py")
    print()
    
    # Set up signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    # Start web server in a separate thread
    web_thread = Thread(target=run_web_server, daemon=True)
    web_thread.start()
    
    # Give web server time to start
    print("⏳ Waiting for web server to start...")
    time.sleep(3)
    
    # Open dashboard in browser (optional)
    try:
        webbrowser.open("http://localhost:5000")
        print("🌐 Dashboard opened in browser: http://localhost:5000")
    except Exception:
        print("🌐 Dashboard available at: http://localhost:5000")
    
    print()
    print("🎯 Services Starting:")
    print("   • Discord Bot: Starting...")
    print("   • Web Dashboard: http://localhost:5000")
    print("   • Demo Login: username='demo', password='demo'")
    print()
    print("💡 Available Commands:")
    print("   • !model - Show/set your preferred AI model")
    print("   • !models - List all available AI models")
    print("   • !modelinfo <model> - Get detailed model information")
    print("   • !modelstats - Show model statistics (admin only)")
    print("   • !modelhealth - Run model health check (admin only)")
    print()
    print("🛑 Press Ctrl+C to stop all services")
    print("=" * 60)
    
    # Start Discord bot in main thread
    try:
        run_discord_bot()
    except KeyboardInterrupt:
        print("\n🛑 Shutdown complete")

if __name__ == "__main__":
    main()

