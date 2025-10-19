# Azure VM Setup Guide for Discord Bot

## Prerequisites
- Azure account with active subscription
- Discord bot token and API keys configured
- Basic knowledge of Linux command line

## Step 1: Create Azure VM

### Option A: Using Azure Portal
1. Go to [Azure Portal](https://portal.azure.com)
2. Click "Create a resource" → "Virtual Machine"
3. Configure:
   - **Resource Group**: Create new or use existing
   - **VM Name**: `discord-bot-vm`
   - **Region**: Choose closest to your users
   - **Image**: Ubuntu Server 22.04 LTS
   - **Size**: B1s (1 vCPU, 1GB RAM) - sufficient for Discord bot
   - **Authentication**: SSH public key (recommended) or password
   - **Public inbound ports**: Allow SSH (22)

### Option B: Using Azure CLI
```bash
# Create resource group
az group create --name discord-bot-rg --location eastus

# Create VM
az vm create \
  --resource-group discord-bot-rg \
  --name discord-bot-vm \
  --image Ubuntu2204 \
  --size Standard_B1s \
  --admin-username azureuser \
  --generate-ssh-keys \
  --public-ip-sku Standard
```

## Step 2: Connect to VM
```bash
ssh azureuser@<your-vm-public-ip>
```

## Step 3: Install Dependencies
Run the setup script on your VM:
```bash
curl -sSL https://raw.githubusercontent.com/your-repo/azure-setup.sh | bash
```

Or manually install:
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11 and pip
sudo apt install python3.11 python3.11-pip python3.11-venv -y

# Install FFmpeg for music features
sudo apt install ffmpeg -y

# Install system dependencies
sudo apt install git curl wget -y
```

## Step 4: Deploy Bot
1. Clone your bot repository
2. Set up environment
3. Configure systemd service
4. Start the bot

## Step 5: Configure Auto-Start
The bot will automatically start on boot and restart if it crashes.

## Monitoring
- Check bot status: `sudo systemctl status discord-bot`
- View logs: `sudo journalctl -u discord-bot -f`
- Restart bot: `sudo systemctl restart discord-bot`

## Cost Optimization
- Use B1s VM size (~$5-10/month)
- Enable auto-shutdown during low usage hours
- Consider Azure Spot VMs for 60-90% cost savings

