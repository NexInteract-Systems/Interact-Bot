#!/bin/bash

# Azure VM Setup Script for Discord Bot
# Run this script on your Ubuntu VM to set up the Discord bot environment

set -e

echo "🤖 Setting up Discord Bot environment on Azure VM..."

# Update system packages
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install Python 3.11 and development tools
echo "🐍 Installing Python 3.11 and development tools..."
sudo apt install -y python3.11 python3.11-pip python3.11-venv python3.11-dev

# Install FFmpeg for music features
echo "🎵 Installing FFmpeg for music features..."
sudo apt install -y ffmpeg

# Install system dependencies
echo "🔧 Installing system dependencies..."
sudo apt install -y git curl wget build-essential

# Create bot user (optional but recommended for security)
echo "👤 Creating bot user..."
if ! id "discordbot" &>/dev/null; then
    sudo useradd -m -s /bin/bash discordbot
    echo "✅ Created discordbot user"
else
    echo "ℹ️  discordbot user already exists"
fi

# Create bot directory
echo "📁 Setting up bot directory..."
sudo mkdir -p /opt/discord-bot
sudo chown discordbot:discordbot /opt/discord-bot

# Switch to bot user and set up Python environment
echo "🔧 Setting up Python virtual environment..."
sudo -u discordbot bash << 'EOF'
cd /opt/discord-bot

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

echo "✅ Python environment ready"
EOF

# Install systemd service
echo "⚙️  Installing systemd service..."
sudo tee /etc/systemd/system/discord-bot.service > /dev/null << 'EOF'
[Unit]
Description=Discord Bot Service
After=network.target

[Service]
Type=simple
User=discordbot
Group=discordbot
WorkingDirectory=/opt/discord-bot
Environment=PATH=/opt/discord-bot/venv/bin
ExecStart=/opt/discord-bot/venv/bin/python main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and enable service
sudo systemctl daemon-reload
sudo systemctl enable discord-bot.service

echo "✅ Systemd service installed and enabled"

# Create deployment script
echo "📝 Creating deployment script..."
sudo tee /opt/discord-bot/deploy.sh > /dev/null << 'EOF'
#!/bin/bash

# Discord Bot Deployment Script
# Run this script to update and restart the bot

set -e

echo "🚀 Deploying Discord Bot..."

# Stop the service
sudo systemctl stop discord-bot

# Update code (assuming git repository)
if [ -d ".git" ]; then
    echo "📥 Pulling latest changes..."
    git pull origin main
else
    echo "⚠️  Not a git repository. Please upload your bot files manually."
fi

# Install/update dependencies
echo "📦 Installing dependencies..."
source venv/bin/activate
pip install -r requirements.txt

# Start the service
echo "🔄 Starting bot service..."
sudo systemctl start discord-bot

# Check status
sleep 3
sudo systemctl status discord-bot --no-pager

echo "✅ Deployment complete!"
echo "📊 Bot status: $(sudo systemctl is-active discord-bot)"
echo "📋 View logs: sudo journalctl -u discord-bot -f"
EOF

sudo chmod +x /opt/discord-bot/deploy.sh
sudo chown discordbot:discordbot /opt/discord-bot/deploy.sh

# Create monitoring script
echo "📊 Creating monitoring script..."
sudo tee /opt/discord-bot/monitor.sh > /dev/null << 'EOF'
#!/bin/bash

# Discord Bot Monitoring Script

echo "🤖 Discord Bot Status Monitor"
echo "=============================="

# Check service status
echo "📊 Service Status:"
sudo systemctl status discord-bot --no-pager -l

echo ""
echo "📋 Recent Logs (last 20 lines):"
sudo journalctl -u discord-bot -n 20 --no-pager

echo ""
echo "💾 System Resources:"
echo "CPU Usage: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)%"
echo "Memory Usage: $(free | grep Mem | awk '{printf("%.1f%%", $3/$2 * 100.0)}')"
echo "Disk Usage: $(df -h / | awk 'NR==2{printf "%s", $5}')"

echo ""
echo "🔧 Useful Commands:"
echo "  View live logs: sudo journalctl -u discord-bot -f"
echo "  Restart bot: sudo systemctl restart discord-bot"
echo "  Stop bot: sudo systemctl stop discord-bot"
echo "  Start bot: sudo systemctl start discord-bot"
EOF

sudo chmod +x /opt/discord-bot/monitor.sh
sudo chown discordbot:discordbot /opt/discord-bot/monitor.sh

# Set up log rotation
echo "📝 Setting up log rotation..."
sudo tee /etc/logrotate.d/discord-bot > /dev/null << 'EOF'
/var/log/discord-bot/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 644 discordbot discordbot
    postrotate
        systemctl reload discord-bot
    endscript
}
EOF

echo ""
echo "🎉 Setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Upload your bot files to /opt/discord-bot/"
echo "2. Configure your config.py with API keys"
echo "3. Run: sudo systemctl start discord-bot"
echo "4. Check status: sudo systemctl status discord-bot"
echo ""
echo "🔧 Useful commands:"
echo "  Monitor: /opt/discord-bot/monitor.sh"
echo "  Deploy updates: /opt/discord-bot/deploy.sh"
echo "  View logs: sudo journalctl -u discord-bot -f"
echo ""
echo "⚠️  Remember to:"
echo "  - Configure your Discord bot token in config.py"
echo "  - Set up your API keys (OpenAI, Gemini, Spotify)"
echo "  - Test the bot before going live"

