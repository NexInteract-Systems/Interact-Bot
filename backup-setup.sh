#!/bin/bash

# Backup and Recovery Setup Script for Discord Bot
# Run this script to set up automated backups

set -e

echo "💾 Setting up backup and recovery for Discord Bot..."

# Install backup tools
echo "📦 Installing backup tools..."
sudo apt update
sudo apt install -y rsync tar gzip

# Create backup directory structure
echo "📁 Creating backup directories..."
sudo mkdir -p /opt/backups/discord-bot/{daily,weekly,monthly}
sudo mkdir -p /opt/backups/config
sudo chown -R discordbot:discordbot /opt/backups/discord-bot

# Create backup script
echo "📝 Creating backup script..."
sudo tee /opt/backups/backup-bot.sh > /dev/null << 'EOF'
#!/bin/bash

# Discord Bot Backup Script
# Creates timestamped backups of bot files and configuration

set -e

BACKUP_DIR="/opt/backups/discord-bot"
BOT_DIR="/opt/discord-bot"
CONFIG_DIR="/opt/backups/config"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_TYPE=${1:-daily}

# Create backup directory for this run
CURRENT_BACKUP="$BACKUP_DIR/$BACKUP_TYPE/bot_backup_$TIMESTAMP"
mkdir -p "$CURRENT_BACKUP"

echo "🔄 Starting backup: $BACKUP_TYPE ($TIMESTAMP)"

# Stop bot service for consistent backup
echo "⏹️  Stopping bot service..."
sudo systemctl stop discord-bot

# Backup bot files
echo "📦 Backing up bot files..."
if [ -d "$BOT_DIR" ]; then
    rsync -av --exclude='venv' --exclude='__pycache__' --exclude='*.log' \
          "$BOT_DIR/" "$CURRENT_BACKUP/"
    echo "✅ Bot files backed up"
else
    echo "⚠️  Bot directory not found: $BOT_DIR"
fi

# Backup system configuration
echo "📋 Backing up system configuration..."
sudo cp /etc/systemd/system/discord-bot.service "$CURRENT_BACKUP/"
sudo cp /etc/logrotate.d/discord-bot "$CURRENT_BACKUP/" 2>/dev/null || true

# Backup system logs
echo "📊 Backing up recent logs..."
sudo journalctl -u discord-bot --since "7 days ago" > "$CURRENT_BACKUP/bot_logs_7days.txt"

# Create backup manifest
echo "📝 Creating backup manifest..."
cat > "$CURRENT_BACKUP/backup_manifest.txt" << MANIFEST
Discord Bot Backup
==================
Backup Type: $BACKUP_TYPE
Timestamp: $TIMESTAMP
Date: $(date)
Bot Directory: $BOT_DIR
Backup Location: $CURRENT_BACKUP

Files Included:
- Bot source code (excluding venv and cache)
- Systemd service configuration
- Recent bot logs (7 days)
- This manifest

Recovery Instructions:
1. Stop bot service: sudo systemctl stop discord-bot
2. Restore files: sudo rsync -av $CURRENT_BACKUP/ $BOT_DIR/
3. Set permissions: sudo chown -R discordbot:discordbot $BOT_DIR
4. Restart service: sudo systemctl start discord-bot
MANIFEST

# Compress backup
echo "🗜️  Compressing backup..."
cd "$BACKUP_DIR/$BACKUP_TYPE"
tar -czf "bot_backup_$TIMESTAMP.tar.gz" "bot_backup_$TIMESTAMP"
rm -rf "bot_backup_$TIMESTAMP"

# Restart bot service
echo "▶️  Starting bot service..."
sudo systemctl start discord-bot

# Cleanup old backups based on type
echo "🧹 Cleaning up old backups..."
case $BACKUP_TYPE in
    daily)
        # Keep 7 daily backups
        find "$BACKUP_DIR/daily" -name "bot_backup_*.tar.gz" -mtime +7 -delete
        ;;
    weekly)
        # Keep 4 weekly backups
        find "$BACKUP_DIR/weekly" -name "bot_backup_*.tar.gz" -mtime +28 -delete
        ;;
    monthly)
        # Keep 12 monthly backups
        find "$BACKUP_DIR/monthly" -name "bot_backup_*.tar.gz" -mtime +365 -delete
        ;;
esac

echo "✅ Backup completed: bot_backup_$TIMESTAMP.tar.gz"
echo "📊 Backup size: $(du -h "$BACKUP_DIR/$BACKUP_TYPE/bot_backup_$TIMESTAMP.tar.gz" | cut -f1)"
EOF

sudo chmod +x /opt/backups/backup-bot.sh

# Create recovery script
echo "🔄 Creating recovery script..."
sudo tee /opt/backups/recover-bot.sh > /dev/null << 'EOF'
#!/bin/bash

# Discord Bot Recovery Script
# Restores bot from backup

set -e

BACKUP_DIR="/opt/backups/discord-bot"
BOT_DIR="/opt/discord-bot"

if [ $# -eq 0 ]; then
    echo "Usage: $0 <backup_file.tar.gz>"
    echo ""
    echo "Available backups:"
    find "$BACKUP_DIR" -name "bot_backup_*.tar.gz" -type f | sort -r
    exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "🔄 Starting recovery from: $BACKUP_FILE"

# Confirm recovery
read -p "⚠️  This will overwrite current bot files. Continue? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Recovery cancelled"
    exit 1
fi

# Stop bot service
echo "⏹️  Stopping bot service..."
sudo systemctl stop discord-bot

# Create recovery backup
echo "💾 Creating recovery backup..."
RECOVERY_BACKUP="/opt/backups/recovery_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$RECOVERY_BACKUP"
if [ -d "$BOT_DIR" ]; then
    sudo cp -r "$BOT_DIR" "$RECOVERY_BACKUP/"
    echo "✅ Current state backed up to: $RECOVERY_BACKUP"
fi

# Extract backup
echo "📦 Extracting backup..."
TEMP_DIR="/tmp/bot_recovery_$$"
mkdir -p "$TEMP_DIR"
tar -xzf "$BACKUP_FILE" -C "$TEMP_DIR"

# Find the extracted directory
EXTRACTED_DIR=$(find "$TEMP_DIR" -maxdepth 1 -type d -name "bot_backup_*" | head -1)

if [ -z "$EXTRACTED_DIR" ]; then
    echo "❌ Could not find extracted backup directory"
    rm -rf "$TEMP_DIR"
    exit 1
fi

# Restore files
echo "🔄 Restoring bot files..."
sudo rsync -av --delete "$EXTRACTED_DIR/" "$BOT_DIR/"

# Set correct permissions
echo "🔐 Setting permissions..."
sudo chown -R discordbot:discordbot "$BOT_DIR"

# Restore systemd service if it exists
if [ -f "$EXTRACTED_DIR/discord-bot.service" ]; then
    echo "⚙️  Restoring systemd service..."
    sudo cp "$EXTRACTED_DIR/discord-bot.service" /etc/systemd/system/
    sudo systemctl daemon-reload
fi

# Cleanup
rm -rf "$TEMP_DIR"

# Start bot service
echo "▶️  Starting bot service..."
sudo systemctl start discord-bot

# Check status
sleep 3
if sudo systemctl is-active --quiet discord-bot; then
    echo "✅ Recovery completed successfully!"
    echo "📊 Bot status: $(sudo systemctl is-active discord-bot)"
else
    echo "❌ Bot failed to start. Check logs: sudo journalctl -u discord-bot -f"
    exit 1
fi

echo ""
echo "🔧 Useful commands:"
echo "  Check status: sudo systemctl status discord-bot"
echo "  View logs: sudo journalctl -u discord-bot -f"
echo "  Restart: sudo systemctl restart discord-bot"
EOF

sudo chmod +x /opt/backups/recover-bot.sh

# Set up automated backups with cron
echo "⏰ Setting up automated backups..."

# Create cron jobs
sudo tee /etc/cron.d/discord-bot-backups > /dev/null << 'EOF'
# Discord Bot Automated Backups
# Daily backup at 2 AM
0 2 * * * root /opt/backups/backup-bot.sh daily

# Weekly backup on Sunday at 3 AM
0 3 * * 0 root /opt/backups/backup-bot.sh weekly

# Monthly backup on 1st at 4 AM
0 4 1 * * root /opt/backups/backup-bot.sh monthly
EOF

# Create backup monitoring script
echo "📊 Creating backup monitoring script..."
sudo tee /opt/backups/backup-status.sh > /dev/null << 'EOF'
#!/bin/bash

# Backup Status Monitoring Script

echo "💾 Discord Bot Backup Status"
echo "============================"

BACKUP_DIR="/opt/backups/discord-bot"

echo "📊 Backup Summary:"
for type in daily weekly monthly; do
    count=$(find "$BACKUP_DIR/$type" -name "bot_backup_*.tar.gz" 2>/dev/null | wc -l)
    latest=$(find "$BACKUP_DIR/$type" -name "bot_backup_*.tar.gz" -type f -printf '%T@ %p\n' 2>/dev/null | sort -n | tail -1 | cut -d' ' -f2-)
    if [ -n "$latest" ]; then
        size=$(du -h "$latest" | cut -f1)
        date=$(stat -c %y "$latest" | cut -d' ' -f1)
        echo "  $type: $count backups (latest: $date, $size)"
    else
        echo "  $type: No backups found"
    fi
done

echo ""
echo "📋 Recent Backups:"
find "$BACKUP_DIR" -name "bot_backup_*.tar.gz" -type f -printf '%T@ %TY-%Tm-%Td %TH:%TM %p\n' | sort -n | tail -5 | while read timestamp date time file; do
    size=$(du -h "$file" | cut -f1)
    echo "  $date $time - $size - $(basename "$file")"
done

echo ""
echo "💾 Total Backup Storage:"
du -sh "$BACKUP_DIR" 2>/dev/null || echo "  No backups found"

echo ""
echo "🔧 Backup Commands:"
echo "  Manual backup: /opt/backups/backup-bot.sh [daily|weekly|monthly]"
echo "  List backups: find $BACKUP_DIR -name 'bot_backup_*.tar.gz' | sort -r"
echo "  Restore: /opt/backups/recover-bot.sh <backup_file>"
EOF

sudo chmod +x /opt/backups/backup-status.sh

# Create Azure Blob Storage backup script (optional)
echo "☁️  Creating Azure Blob Storage backup script..."
sudo tee /opt/backups/upload-to-azure.sh > /dev/null << 'EOF'
#!/bin/bash

# Upload backups to Azure Blob Storage
# Requires azure-cli to be installed and configured

set -e

BACKUP_DIR="/opt/backups/discord-bot"
CONTAINER_NAME="discord-bot-backups"
RESOURCE_GROUP="discord-bot-rg"
STORAGE_ACCOUNT="discordbotstorage"

# Check if azure-cli is installed
if ! command -v az &> /dev/null; then
    echo "❌ Azure CLI not installed. Install with: curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash"
    exit 1
fi

# Check if logged in
if ! az account show &> /dev/null; then
    echo "❌ Not logged in to Azure. Run: az login"
    exit 1
fi

echo "☁️  Uploading backups to Azure Blob Storage..."

# Create storage account if it doesn't exist
if ! az storage account show --name "$STORAGE_ACCOUNT" --resource-group "$RESOURCE_GROUP" &> /dev/null; then
    echo "📦 Creating storage account..."
    az storage account create \
        --name "$STORAGE_ACCOUNT" \
        --resource-group "$RESOURCE_GROUP" \
        --location eastus \
        --sku Standard_LRS
fi

# Create container if it doesn't exist
az storage container create --name "$CONTAINER_NAME" --account-name "$STORAGE_ACCOUNT" 2>/dev/null || true

# Upload latest backups
echo "📤 Uploading latest backups..."
for type in daily weekly monthly; do
    latest=$(find "$BACKUP_DIR/$type" -name "bot_backup_*.tar.gz" -type f -printf '%T@ %p\n' 2>/dev/null | sort -n | tail -1 | cut -d' ' -f2-)
    if [ -n "$latest" ]; then
        filename=$(basename "$latest")
        echo "  Uploading $filename..."
        az storage blob upload \
            --file "$latest" \
            --container-name "$CONTAINER_NAME" \
            --name "$type/$filename" \
            --account-name "$STORAGE_ACCOUNT"
    fi
done

echo "✅ Upload completed!"
echo "🔗 View backups in Azure Portal: https://portal.azure.com"
EOF

sudo chmod +x /opt/backups/upload-to-azure.sh

echo ""
echo "🎉 Backup and recovery setup complete!"
echo ""
echo "💾 Backup features:"
echo "  ✅ Automated daily, weekly, and monthly backups"
echo "  ✅ Manual backup script"
echo "  ✅ Recovery script"
echo "  ✅ Backup monitoring"
echo "  ✅ Optional Azure Blob Storage upload"
echo ""
echo "📋 Backup commands:"
echo "  Manual backup: /opt/backups/backup-bot.sh [daily|weekly|monthly]"
echo "  Check status: /opt/backups/backup-status.sh"
echo "  Restore: /opt/backups/recover-bot.sh <backup_file>"
echo "  Upload to Azure: /opt/backups/upload-to-azure.sh"
echo ""
echo "⏰ Automated schedule:"
echo "  Daily: 2:00 AM"
echo "  Weekly: Sunday 3:00 AM"
echo "  Monthly: 1st of month 4:00 AM"
echo ""
echo "📁 Backup location: /opt/backups/discord-bot/"
echo "  - daily/: Last 7 days"
echo "  - weekly/: Last 4 weeks"
echo "  - monthly/: Last 12 months"


