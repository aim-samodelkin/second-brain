#!/bin/bash
# Second Brain - Server Setup Script
# Run this script on a fresh Ubuntu 22.04 VPS
# Usage: bash setup-server.sh

set -e

echo "=========================================="
echo "  Second Brain - Server Setup"
echo "=========================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run as root (sudo bash setup-server.sh)${NC}"
    exit 1
fi

echo -e "${YELLOW}Step 1: Updating system...${NC}"
apt update && apt upgrade -y

echo -e "${YELLOW}Step 2: Installing basic packages...${NC}"
apt install -y curl wget git nano htop ufw fail2ban

echo -e "${YELLOW}Step 3: Setting up firewall...${NC}"
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp comment 'SSH'
ufw allow 80/tcp comment 'HTTP'
ufw allow 443/tcp comment 'HTTPS'
ufw --force enable
ufw status verbose

echo -e "${YELLOW}Step 4: Installing Docker...${NC}"

# Remove old versions
apt remove docker docker-engine docker.io containerd runc -y 2>/dev/null || true

# Install dependencies
apt install -y ca-certificates curl gnupg lsb-release

# Add Docker GPG key
mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Add Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

echo -e "${YELLOW}Step 5: Configuring Docker for current user...${NC}"

# Get the user who ran sudo (if applicable)
SUDO_USER=${SUDO_USER:-$USER}
if [ "$SUDO_USER" != "root" ]; then
    usermod -aG docker $SUDO_USER
    echo -e "${GREEN}Added $SUDO_USER to docker group${NC}"
fi

echo -e "${YELLOW}Step 6: Verifying installation...${NC}"
docker --version
docker compose version

echo ""
echo -e "${GREEN}=========================================="
echo "  Server setup complete!"
echo "==========================================${NC}"
echo ""
echo "Next steps:"
echo "1. Log out and log back in (for docker group to take effect)"
echo "2. Copy the second-brain project to ~/second-brain/"
echo "3. Copy .env.example to .env and configure"
echo "4. Run: docker compose up -d"
echo ""
echo "If using a non-root user, run:"
echo "  su - $SUDO_USER"
echo ""
