# Discord Bot Azure VM Deployment Guide

This guide will help you deploy your Discord bot to Azure VM for 24/7 hosting.

## 🚀 Quick Start

### Option 1: Automated Deployment (Recommended)
1. Install [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli)
2. Login to Azure: `az login`
3. Run the deployment script: `bash deploy-to-azure.sh`

### Option 2: Manual Deployment
Follow the step-by-step guide below.

## 📋 Prerequisites

- Azure account with active subscription
- Azure CLI installed
- Discord bot token and API keys configured
- SSH client (Windows: use WSL, Git Bash, or PowerShell with OpenSSH)

## 🔧 Step-by-Step Manual Deployment

### 1. Create Azure VM

#### Using Azure Portal:
1. Go to [Azure Portal](https://portal.azure.com)
2. Click "Create a resource" → "Virtual Machine"
3. Configure:
   - **Resource Group**: `discord-bot-rg`
   - **VM Name**: `discord-bot-vm`
   - **Region**: Choose closest to your users
   - **Image**: Ubuntu Server 22.04 LTS
   - **Size**: B1s (1 vCPU, 1GB RAM) - sufficient for Discord bot
   - **Authentication**: SSH public key (recommended)
   - **Public inbound ports**: Allow SSH (22)

#### Using Azure CLI:
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

### 2. Connect to VM
```bash
# Get VM IP
az vm show -d --resource-group discord-bot-rg --name discord-bot-vm --query publicIps -o tsv

# Connect via SSH
ssh azureuser@<your-vm-ip>
```

### 3. Deploy Bot Files

#### Upload files to VM:
```bash
# From your local machine (Windows PowerShell/Git Bash)
scp -r *.py *.txt *.sh azureuser@<vm-ip>:/home/azureuser/
```

#### Or use Git (if your bot is in a repository):
```bash
# On the VM
git clone <your-repo-url>
cd <your-repo-name>
```

### 4. Run Setup Scripts

On the VM, run these scripts in order:

```bash
# Make scripts executable
chmod +x azure-setup.sh security-setup.sh backup-setup.sh

# Run initial setup
sudo ./azure-setup.sh

# Configure security
sudo ./security-setup.sh

# Set up backups
sudo ./backup-setup.sh
```

### 5. Configure Bot

Edit your `config.py` file with your API keys:
```bash
sudo nano /opt/discord-bot/config.py
```

Make sure to set:
- `DISCORD_TOKEN` - Your Discord bot token
- `OPENAI_API_KEY` - OpenAI API key (if using)
- `GEMINI_API_KEY` - Google Gemini API key
- `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET` - Spotify API credentials

### 6. Start the Bot

```bash
# Start the bot service
sudo systemctl start discord-bot

# Enable auto-start on boot
sudo systemctl enable discord-bot

# Check status
sudo systemctl status discord-bot
```

## 🔧 Management Commands

### Bot Control
```bash
# Check status
sudo systemctl status discord-bot

# Start bot
sudo systemctl start discord-bot

# Stop bot
sudo systemctl stop discord-bot

# Restart bot
sudo systemctl restart discord-bot

# View logs
sudo journalctl -u discord-bot -f
```

### Monitoring
```bash
# Run monitoring script
/opt/discord-bot/monitor.sh

# Check security status
/opt/discord-bot/security-monitor.sh

# Check backup status
/opt/backups/backup-status.sh
```

### Updates
```bash
# Deploy updates
/opt/discord-bot/deploy.sh

# Manual backup
/opt/backups/backup-bot.sh daily

# Restore from backup
/opt/backups/recover-bot.sh <backup-file>
```

## 💰 Cost Optimization

### VM Sizing
- **B1s** (1 vCPU, 1GB RAM): ~$5-10/month - Good for basic bots
- **B1ms** (1 vCPU, 2GB RAM): ~$10-15/month - Better for bots with heavy features
- **B2s** (2 vCPU, 4GB RAM): ~$20-25/month - For high-traffic bots

### Cost Saving Tips
1. **Enable auto-shutdown**:
   ```bash
   az vm auto-shutdown -g discord-bot-rg -n discord-bot-vm --time 2200
   ```

2. **Use Azure Spot VMs** (60-90% cost savings):
   ```bash
   az vm create --priority Spot --max-price -1 ...
   ```

3. **Monitor costs** in Azure Portal

## 🔒 Security Features

The setup includes:
- ✅ Fail2ban (intrusion prevention)
- ✅ UFW firewall (only SSH, HTTP, HTTPS allowed)
- ✅ SSH hardening (password auth disabled)
- ✅ Automatic security updates
- ✅ File integrity monitoring
- ✅ Log monitoring

## 💾 Backup Strategy

Automated backups:
- **Daily**: 2:00 AM (keeps 7 days)
- **Weekly**: Sunday 3:00 AM (keeps 4 weeks)
- **Monthly**: 1st of month 4:00 AM (keeps 12 months)

Backup location: `/opt/backups/discord-bot/`

## 🚨 Troubleshooting

### Bot won't start
```bash
# Check logs
sudo journalctl -u discord-bot -n 50

# Check config
sudo -u discordbot cat /opt/discord-bot/config.py

# Test Python environment
sudo -u discordbot /opt/discord-bot/venv/bin/python -c "import discord; print('OK')"
```

### Connection issues
```bash
# Check network
ping discord.com

# Check firewall
sudo ufw status

# Check SSH
sudo systemctl status ssh
```

### High resource usage
```bash
# Check system resources
htop
df -h
free -h

# Check bot logs for errors
sudo journalctl -u discord-bot --since "1 hour ago"
```

## 📞 Support

If you encounter issues:
1. Check the logs: `sudo journalctl -u discord-bot -f`
2. Verify your API keys in `config.py`
3. Ensure your Discord bot has proper permissions
4. Check Azure VM status in the portal

## 🔄 Updates and Maintenance

### Regular Maintenance
- Monitor bot logs weekly
- Check backup status monthly
- Update system packages: `sudo apt update && sudo apt upgrade`
- Review Azure costs monthly

### Bot Updates
1. Upload new files to VM
2. Run: `/opt/discord-bot/deploy.sh`
3. Check status: `sudo systemctl status discord-bot`

---

**🎉 Your Discord bot is now running 24/7 on Azure VM!**

For questions or issues, check the logs first, then refer to the troubleshooting section above.




















