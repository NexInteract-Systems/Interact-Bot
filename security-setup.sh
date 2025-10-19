#!/bin/bash

# Security Configuration Script for Discord Bot VM
# Run this script to secure your Azure VM

set -e

echo "🔒 Configuring security settings for Discord Bot VM..."

# Update system
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install fail2ban for intrusion prevention
echo "🛡️  Installing fail2ban..."
sudo apt install -y fail2ban

# Configure fail2ban for SSH protection
sudo tee /etc/fail2ban/jail.local > /dev/null << 'EOF'
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3

[sshd]
enabled = true
port = ssh
logpath = /var/log/auth.log
maxretry = 3
bantime = 3600
EOF

sudo systemctl enable fail2ban
sudo systemctl start fail2ban

# Configure UFW firewall
echo "🔥 Configuring firewall..."
sudo ufw --force reset
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH (adjust port if you changed it)
sudo ufw allow ssh
sudo ufw allow 22/tcp

# Allow HTTP/HTTPS if needed for webhooks
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Enable firewall
sudo ufw --force enable

# Configure SSH security
echo "🔐 Securing SSH..."
sudo cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup

# Disable root login and password authentication
sudo sed -i 's/#PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sudo sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo sed -i 's/PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config

# Restart SSH service
sudo systemctl restart ssh

# Set up automatic security updates
echo "🔄 Setting up automatic security updates..."
sudo apt install -y unattended-upgrades

sudo tee /etc/apt/apt.conf.d/50unattended-upgrades > /dev/null << 'EOF'
Unattended-Upgrade::Allowed-Origins {
    "${distro_id}:${distro_codename}-security";
    "${distro_id}ESMApps:${distro_codename}-apps-security";
    "${distro_id}ESM:${distro_codename}-infra-security";
};

Unattended-Upgrade::AutoFixInterruptedDpkg "true";
Unattended-Upgrade::MinimalSteps "true";
Unattended-Upgrade::Remove-Unused-Dependencies "true";
Unattended-Upgrade::Automatic-Reboot "false";
EOF

sudo tee /etc/apt/apt.conf.d/20auto-upgrades > /dev/null << 'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
EOF

# Configure log monitoring
echo "📊 Setting up log monitoring..."
sudo apt install -y logwatch

# Create log monitoring script
sudo tee /opt/discord-bot/security-monitor.sh > /dev/null << 'EOF'
#!/bin/bash

# Security Monitoring Script for Discord Bot

echo "🔒 Security Status Report"
echo "========================="

# Check fail2ban status
echo "🛡️  Fail2ban Status:"
sudo fail2ban-client status

echo ""
echo "🔥 Firewall Status:"
sudo ufw status verbose

echo ""
echo "📊 Recent Failed Login Attempts:"
sudo grep "Failed password" /var/log/auth.log | tail -5

echo ""
echo "🚨 Recent Security Events:"
sudo journalctl -p err -n 10 --no-pager

echo ""
echo "💾 System Security:"
echo "SSH Status: $(sudo systemctl is-active ssh)"
echo "Fail2ban Status: $(sudo systemctl is-active fail2ban)"
echo "UFW Status: $(sudo ufw status | head -1)"

echo ""
echo "🔧 Security Commands:"
echo "  View fail2ban logs: sudo fail2ban-client status sshd"
echo "  Unban IP: sudo fail2ban-client set sshd unbanip <IP>"
echo "  View firewall logs: sudo ufw status numbered"
EOF

sudo chmod +x /opt/discord-bot/security-monitor.sh
sudo chown discordbot:discordbot /opt/discord-bot/security-monitor.sh

# Set up file integrity monitoring
echo "🔍 Setting up file integrity monitoring..."
sudo apt install -y aide

# Initialize AIDE database
sudo aideinit
sudo mv /var/lib/aide/aide.db.new /var/lib/aide/aide.db

# Create daily integrity check
sudo tee /etc/cron.daily/aide-check > /dev/null << 'EOF'
#!/bin/bash
/usr/bin/aide --check | /usr/bin/mail -s "AIDE Integrity Check" root
EOF

sudo chmod +x /etc/cron.daily/aide-check

# Configure system limits
echo "⚙️  Configuring system limits..."
sudo tee -a /etc/security/limits.conf > /dev/null << 'EOF'

# Discord Bot limits
discordbot soft nofile 65536
discordbot hard nofile 65536
discordbot soft nproc 4096
discordbot hard nproc 4096
EOF

# Set up log rotation for security logs
sudo tee /etc/logrotate.d/security > /dev/null << 'EOF'
/var/log/auth.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 640 root adm
    postrotate
        systemctl reload rsyslog
    endscript
}

/var/log/fail2ban.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 640 root adm
    postrotate
        systemctl reload fail2ban
    endscript
}
EOF

echo ""
echo "🎉 Security configuration complete!"
echo ""
echo "🔒 Security features enabled:"
echo "  ✅ Fail2ban (intrusion prevention)"
echo "  ✅ UFW firewall"
echo "  ✅ SSH hardening"
echo "  ✅ Automatic security updates"
echo "  ✅ File integrity monitoring (AIDE)"
echo "  ✅ Log monitoring"
echo ""
echo "📋 Security monitoring:"
echo "  Run: /opt/discord-bot/security-monitor.sh"
echo ""
echo "⚠️  Important security notes:"
echo "  - SSH password authentication is disabled"
echo "  - Root login is disabled"
echo "  - Firewall is active (only SSH, HTTP, HTTPS allowed)"
echo "  - Failed login attempts will be banned for 1 hour"
echo "  - Security updates will be installed automatically"
echo ""
echo "🔧 If you get locked out:"
echo "  - Use Azure Portal to reset SSH key"
echo "  - Or use Azure Cloud Shell to access VM"

