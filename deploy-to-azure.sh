#!/bin/bash

# Complete Azure Deployment Script for Discord Bot
# This script automates the entire deployment process

set -e

echo "🚀 Discord Bot Azure Deployment Script"
echo "======================================"

# Configuration
VM_NAME="discord-bot-vm"
RESOURCE_GROUP="discord-bot-rg"
LOCATION="eastus"
VM_SIZE="Standard_B1s"
ADMIN_USERNAME="azureuser"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    print_error "Azure CLI not found. Please install it first:"
    echo "curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash"
    exit 1
fi

# Check if logged in to Azure
if ! az account show &> /dev/null; then
    print_error "Not logged in to Azure. Please run: az login"
    exit 1
fi

print_status "Starting Azure VM deployment..."

# Create resource group
print_status "Creating resource group: $RESOURCE_GROUP"
az group create --name "$RESOURCE_GROUP" --location "$LOCATION" --output table

# Create VM
print_status "Creating VM: $VM_NAME"
az vm create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$VM_NAME" \
    --image Ubuntu2204 \
    --size "$VM_SIZE" \
    --admin-username "$ADMIN_USERNAME" \
    --generate-ssh-keys \
    --public-ip-sku Standard \
    --output table

# Get VM public IP
print_status "Getting VM public IP..."
VM_IP=$(az vm show -d --resource-group "$RESOURCE_GROUP" --name "$VM_NAME" --query publicIps -o tsv)
print_success "VM created with IP: $VM_IP"

# Wait for VM to be ready
print_status "Waiting for VM to be ready..."
sleep 30

# Create deployment package
print_status "Creating deployment package..."
DEPLOY_DIR="/tmp/discord-bot-deploy"
mkdir -p "$DEPLOY_DIR"

# Copy bot files
cp main.py "$DEPLOY_DIR/"
cp config.py "$DEPLOY_DIR/"
cp api_handler.py "$DEPLOY_DIR/"
cp music.py "$DEPLOY_DIR/"
cp requirements.txt "$DEPLOY_DIR/"

# Copy setup scripts
cp azure-setup.sh "$DEPLOY_DIR/"
cp security-setup.sh "$DEPLOY_DIR/"
cp backup-setup.sh "$DEPLOY_DIR/"

# Create deployment script
cat > "$DEPLOY_DIR/deploy-bot.sh" << 'EOF'
#!/bin/bash

# Bot deployment script to run on VM

set -e

echo "🤖 Deploying Discord Bot on Azure VM..."

# Run setup scripts
echo "📦 Running initial setup..."
chmod +x azure-setup.sh
sudo ./azure-setup.sh

echo "🔒 Configuring security..."
chmod +x security-setup.sh
sudo ./security-setup.sh

echo "💾 Setting up backups..."
chmod +x backup-setup.sh
sudo ./backup-setup.sh

# Copy bot files to proper location
echo "📁 Copying bot files..."
sudo cp *.py /opt/discord-bot/
sudo cp requirements.txt /opt/discord-bot/
sudo chown -R discordbot:discordbot /opt/discord-bot

# Install Python dependencies
echo "📦 Installing Python dependencies..."
sudo -u discordbot bash -c "cd /opt/discord-bot && source venv/bin/activate && pip install -r requirements.txt"

# Start the bot
echo "▶️  Starting Discord bot..."
sudo systemctl start discord-bot
sudo systemctl enable discord-bot

# Check status
sleep 5
if sudo systemctl is-active --quiet discord-bot; then
    echo "✅ Discord bot is running!"
    echo "📊 Status: $(sudo systemctl is-active discord-bot)"
else
    echo "❌ Bot failed to start. Check logs:"
    sudo journalctl -u discord-bot -n 20
fi

echo ""
echo "🎉 Deployment complete!"
echo ""
echo "🔧 Useful commands:"
echo "  Check status: sudo systemctl status discord-bot"
echo "  View logs: sudo journalctl -u discord-bot -f"
echo "  Restart: sudo systemctl restart discord-bot"
echo "  Monitor: /opt/discord-bot/monitor.sh"
echo "  Security check: /opt/discord-bot/security-monitor.sh"
echo "  Backup status: /opt/backups/backup-status.sh"
EOF

chmod +x "$DEPLOY_DIR/deploy-bot.sh"

# Create SSH config for easier access
print_status "Creating SSH config..."
cat > ~/.ssh/config << EOF
Host discord-bot-vm
    HostName $VM_IP
    User $ADMIN_USERNAME
    IdentityFile ~/.ssh/id_rsa
    StrictHostKeyChecking no
EOF

# Copy files to VM
print_status "Copying files to VM..."
scp -r "$DEPLOY_DIR"/* "$ADMIN_USERNAME@$VM_IP:/home/$ADMIN_USERNAME/"

# Run deployment on VM
print_status "Running deployment on VM..."
ssh "$ADMIN_USERNAME@$VM_IP" "cd /home/$ADMIN_USERNAME && chmod +x deploy-bot.sh && ./deploy-bot.sh"

# Cleanup
rm -rf "$DEPLOY_DIR"

print_success "Deployment completed!"
echo ""
echo "🎉 Your Discord bot is now running on Azure VM!"
echo ""
echo "📋 Connection details:"
echo "  VM IP: $VM_IP"
echo "  SSH: ssh discord-bot-vm"
echo "  Resource Group: $RESOURCE_GROUP"
echo ""
echo "🔧 Management commands:"
echo "  Check bot status: ssh discord-bot-vm 'sudo systemctl status discord-bot'"
echo "  View logs: ssh discord-bot-vm 'sudo journalctl -u discord-bot -f'"
echo "  Restart bot: ssh discord-bot-vm 'sudo systemctl restart discord-bot'"
echo "  Monitor: ssh discord-bot-vm '/opt/discord-bot/monitor.sh'"
echo ""
echo "💰 Cost optimization:"
echo "  - VM size: $VM_SIZE (~$5-10/month)"
echo "  - Enable auto-shutdown: az vm auto-shutdown -g $RESOURCE_GROUP -n $VM_NAME --time 2200"
echo "  - Consider Azure Spot VMs for 60-90% savings"
echo ""
echo "⚠️  Important:"
echo "  - Configure your Discord bot token in config.py"
echo "  - Set up your API keys (OpenAI, Gemini, Spotify)"
echo "  - Test the bot before going live"
echo "  - Monitor costs in Azure Portal"




















