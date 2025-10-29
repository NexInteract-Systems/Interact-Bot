#!/usr/bin/env python3
"""
Setup Script for AI Discord Bot Multi-Model System
Automates the setup process and validates configuration
"""

import os
import sys
import subprocess
import json
from pathlib import Path

def print_header():
    """Print setup header"""
    print("=" * 70)
    print("🚀 AI Discord Bot - Multi-Model LLM System Setup")
    print("=" * 70)
    print()

def check_python_version():
    """Check if Python version is compatible"""
    print("🐍 Checking Python version...")
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8 or higher is required")
        print(f"   Current version: {version.major}.{version.minor}.{version.micro}")
        return False
    else:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} is compatible")
        return True

def install_dependencies():
    """Install required dependencies"""
    print("\n📦 Installing dependencies...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                      check=True, capture_output=True, text=True)
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        print("   Please run: pip install -r requirements.txt")
        return False

def check_config_file():
    """Check if config.py exists and is properly configured"""
    print("\n⚙️  Checking configuration...")
    
    if not os.path.exists("config.py"):
        print("❌ config.py not found")
        return False
    
    try:
        # Import config to check for syntax errors
        import config
        print("✅ config.py found and valid")
        
        # Check for API keys
        api_keys = {
            "OpenAI": getattr(config, 'OPENAI_API_KEY', ''),
            "Gemini": getattr(config, 'GEMINI_API_KEY', ''),
            "Anthropic": getattr(config, 'ANTHROPIC_API_KEY', ''),
            "OpenRouter": getattr(config, 'OPENROUTER_API_KEY', '')
        }
        
        configured_keys = []
        for name, key in api_keys.items():
            if key and key.strip():
                configured_keys.append(name)
                print(f"✅ {name} API key configured")
            else:
                print(f"⚠️  {name} API key not configured")
        
        if not configured_keys:
            print("\n⚠️  No API keys configured!")
            print("   Please add at least one API key to config.py")
            print("   See API-Connection-Guide.md for setup instructions")
            return False
        
        print(f"\n✅ {len(configured_keys)} API key(s) configured")
        return True
        
    except Exception as e:
        print(f"❌ Error reading config.py: {e}")
        return False

def create_directories():
    """Create necessary directories"""
    print("\n📁 Creating directories...")
    
    directories = ["templates", "logs", "data"]
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✅ Created directory: {directory}")

def check_discord_token():
    """Check if Discord token is configured"""
    print("\n🤖 Checking Discord bot token...")
    
    try:
        import config
        token = getattr(config, 'DISCORD_TOKEN', '')
        
        if not token or token == "YOUR_DISCORD_BOT_TOKEN":
            print("❌ Discord bot token not configured")
            print("   Please set DISCORD_TOKEN in config.py")
            return False
        else:
            print("✅ Discord bot token configured")
            return True
    except Exception as e:
        print(f"❌ Error checking Discord token: {e}")
        return False

def run_api_test():
    """Run API connection test"""
    print("\n🧪 Testing API connections...")
    
    if not os.path.exists("test_apis.py"):
        print("⚠️  test_apis.py not found, skipping API test")
        return True
    
    try:
        result = subprocess.run([sys.executable, "test_apis.py"], 
                               capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print("✅ API tests completed successfully")
            return True
        else:
            print("⚠️  Some API tests failed")
            print("   This is normal if API keys are not configured yet")
            return True
    except subprocess.TimeoutExpired:
        print("⚠️  API test timed out")
        return True
    except Exception as e:
        print(f"⚠️  API test error: {e}")
        return True

def create_startup_scripts():
    """Create convenient startup scripts"""
    print("\n📝 Creating startup scripts...")
    
    # Windows batch file
    windows_script = """@echo off
echo Starting AI Discord Bot Multi-Model System...
python start_bot.py
pause
"""
    
    with open("start_bot.bat", "w") as f:
        f.write(windows_script)
    print("✅ Created start_bot.bat")
    
    # Linux/Mac shell script
    unix_script = """#!/bin/bash
echo "Starting AI Discord Bot Multi-Model System..."
python3 start_bot.py
"""
    
    with open("start_bot.sh", "w") as f:
        f.write(unix_script)
    
    # Make executable
    try:
        os.chmod("start_bot.sh", 0o755)
        print("✅ Created start_bot.sh")
    except:
        print("⚠️  Could not make start_bot.sh executable")

def show_next_steps():
    """Show next steps to the user"""
    print("\n" + "=" * 70)
    print("🎉 Setup Complete!")
    print("=" * 70)
    print()
    print("📋 Next Steps:")
    print()
    print("1. 🔑 Configure API Keys (if not done already):")
    print("   • Edit config.py")
    print("   • Add your API keys for OpenAI, Gemini, Anthropic, or OpenRouter")
    print("   • See API-Connection-Guide.md for detailed instructions")
    print()
    print("2. 🧪 Test API Connections:")
    print("   • Run: python test_apis.py")
    print("   • This will verify all your API keys work")
    print()
    print("3. 🚀 Start the Bot:")
    print("   • Run: python start_bot.py")
    print("   • Or use: start_bot.bat (Windows) / start_bot.sh (Linux/Mac)")
    print()
    print("4. 🌐 Access Web Dashboard:")
    print("   • URL: http://localhost:5000")
    print("   • Login: username='demo', password='demo'")
    print()
    print("5. 💬 Test Discord Commands:")
    print("   • !model - Show your current model")
    print("   • !models - List all available models")
    print("   • !model gpt-4o-mini - Switch to GPT-4o Mini")
    print("   • !chat Hello - Test chat with AI")
    print()
    print("📚 Documentation:")
    print("   • README-Multi-Model.md - Complete guide")
    print("   • API-Connection-Guide.md - API setup instructions")
    print()
    print("🆘 Need Help?")
    print("   • Check the documentation files")
    print("   • Run python test_apis.py to diagnose issues")
    print("   • Ensure all API keys are valid and have credits")

def main():
    """Main setup function"""
    print_header()
    
    # Check Python version
    if not check_python_version():
        return
    
    # Install dependencies
    if not install_dependencies():
        return
    
    # Check configuration
    config_ok = check_config_file()
    
    # Check Discord token
    discord_ok = check_discord_token()
    
    # Create directories
    create_directories()
    
    # Run API test
    run_api_test()
    
    # Create startup scripts
    create_startup_scripts()
    
    # Show next steps
    show_next_steps()
    
    # Final status
    print("\n" + "=" * 70)
    if config_ok and discord_ok:
        print("✅ Setup completed successfully!")
        print("   Your bot is ready to start.")
    else:
        print("⚠️  Setup completed with warnings.")
        print("   Please configure missing settings before starting the bot.")
    print("=" * 70)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Setup interrupted by user")
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        print("Please check the error and try again.")

