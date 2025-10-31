#!/bin/bash
# ============================================
# ISTHT Founty Bot - Complete Debian Setup
# Ready to Run with One Command!
# ============================================

set -e

echo "=================================================="
echo "🤖 ISTHT Founty Inventory Bot - Setup for Debian"
echo "=================================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# ============ STEP 1: Update System ============
echo -e "${BLUE}[Step 1/5]${NC} Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# ============ STEP 2: Install Python 3.11 ============
echo -e "${BLUE}[Step 2/5]${NC} Installing Python 3.11..."
sudo apt-get install -y python3.11 python3.11-venv python3-pip
sudo apt-get install -y git curl wget nano

# ============ STEP 3: Create Bot Directory ============
echo -e "${BLUE}[Step 3/5]${NC} Creating bot directory..."
BOT_DIR="/opt/istht-bot"
sudo mkdir -p $BOT_DIR
sudo chown $(whoami):$(whoami) $BOT_DIR
cd $BOT_DIR

# ============ STEP 4: Verify Bot Files ============
echo -e "${BLUE}[Step 4/5]${NC} Checking bot files..."

REQUIRED_FILES=("bot_debian.py" "requirements.txt")
MISSING_FILES=()

for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        MISSING_FILES+=("$file")
    fi
done

if [ ${#MISSING_FILES[@]} -ne 0 ]; then
    echo -e "${RED}❌ ERROR: Missing files:${NC}"
    for file in "${MISSING_FILES[@]}"; do
        echo "   - $file"
    done
    echo ""
    echo "Please copy all files to: $BOT_DIR"
    exit 1
fi

echo -e "${GREEN}✅ All bot files found!${NC}"

# ============ STEP 5: Create Virtual Environment ============
echo -e "${BLUE}[Step 5/5]${NC} Setting up Python environment..."
python3.11 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install Python dependencies
echo "Installing Python packages..."
pip install -r requirements.txt

echo -e "${GREEN}✅ Python environment ready!${NC}"

# ============ STEP 6: Create Systemd Service ============
echo "Creating systemd service..."

cat > /tmp/istht-bot.service << 'EOF'
[Unit]
Description=ISTHT Founty Inventory Telegram Bot
After=network.target
StartLimitBurst=5
StartLimitIntervalSec=60

[Service]
Type=simple
User=BOT_USER_PLACEHOLDER
WorkingDirectory=BOT_DIR_PLACEHOLDER
Environment="PATH=BOT_DIR_PLACEHOLDER/venv/bin"
Environment="BOT_TOKEN=BOT_TOKEN_PLACEHOLDER"
ExecStart=BOT_DIR_PLACEHOLDER/venv/bin/python3.11 bot_debian.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Replace placeholders
sed -i "s|BOT_USER_PLACEHOLDER|$(whoami)|g" /tmp/istht-bot.service
sed -i "s|BOT_DIR_PLACEHOLDER|$BOT_DIR|g" /tmp/istht-bot.service
sed -i "s|BOT_TOKEN_PLACEHOLDER|YOUR_BOT_TOKEN_HERE|g" /tmp/istht-bot.service

sudo cp /tmp/istht-bot.service /etc/systemd/system/istht-bot.service
sudo systemctl daemon-reload

echo -e "${GREEN}✅ Systemd service created!${NC}"

# ============ DISPLAY NEXT STEPS ============
echo ""
echo "=================================================="
echo -e "${GREEN}✅ Setup Complete!${NC}"
echo "=================================================="
echo ""
echo -e "${YELLOW}📝 NEXT STEPS - Please read carefully:${NC}"
echo ""
echo "1️⃣  Get your bot token:"
echo "   • Open Telegram"
echo "   • Search: @BotFather"
echo "   • Send: /newbot"
echo "   • Follow the instructions"
echo "   • Copy your token (example: 1234567890:ABC...)"
echo ""
echo "2️⃣  Set the bot token in systemd service:"
echo "   ${BLUE}sudo nano /etc/systemd/system/istht-bot.service${NC}"
echo ""
echo "   Find this line:"
echo "   ${YELLOW}Environment=\"BOT_TOKEN=YOUR_BOT_TOKEN_HERE\"${NC}"
echo ""
echo "   Replace ${YELLOW}YOUR_BOT_TOKEN_HERE${NC} with your actual token"
echo "   Save: ${BLUE}Ctrl+O${NC}, then ${BLUE}Enter${NC}, then ${BLUE}Ctrl+X${NC}"
echo ""
echo "3️⃣  Enable and start the bot:"
echo "   ${BLUE}sudo systemctl daemon-reload${NC}"
echo "   ${BLUE}sudo systemctl enable istht-bot${NC}"
echo "   ${BLUE}sudo systemctl start istht-bot${NC}"
echo ""
echo "4️⃣  Check if bot is running:"
echo "   ${BLUE}sudo systemctl status istht-bot${NC}"
echo ""
echo "   You should see: ${GREEN}Active: active (running)${NC}"
echo ""
echo "5️⃣  View logs (to check everything is working):"
echo "   ${BLUE}sudo journalctl -u istht-bot -f${NC}"
echo ""
echo "   Look for: ${GREEN}🚀 Bot ISTHT Founty démarré avec succès!${NC}"
echo "   (Press Ctrl+C to exit logs)"
echo ""
echo "6️⃣  Test your bot in Telegram:"
echo "   • Open Telegram"
echo "   • Find your bot"
echo "   • Send: /start"
echo "   • Bot should respond!"
echo ""
echo "=================================================="
echo -e "${BLUE}Useful Commands:${NC}"
echo "=================================================="
echo "Start bot:      ${BLUE}sudo systemctl start istht-bot${NC}"
echo "Stop bot:       ${BLUE}sudo systemctl stop istht-bot${NC}"
echo "Restart bot:    ${BLUE}sudo systemctl restart istht-bot${NC}"
echo "Check status:   ${BLUE}sudo systemctl status istht-bot${NC}"
echo "View logs:      ${BLUE}sudo journalctl -u istht-bot -f${NC}"
echo "Last 50 logs:   ${BLUE}sudo journalctl -u istht-bot -n 50${NC}"
echo ""
echo "=================================================="
echo -e "${BLUE}Admin Panel Login:${NC}"
echo "=================================================="
echo "Default PIN: ${YELLOW}1234${NC}"
echo -e "${RED}⚠️  CHANGE THIS IMMEDIATELY!${NC}"
echo ""
echo "Edit file: ${BLUE}$BOT_DIR/bot_debian.py${NC}"
echo "Find line: ${YELLOW}ADMIN_PIN = \"1234\"${NC}"
echo "Change to: ${YELLOW}ADMIN_PIN = \"YOUR_SECURE_PIN\"${NC}"
echo "Then restart: ${BLUE}sudo systemctl restart istht-bot${NC}"
echo ""
echo "=================================================="
echo ""
echo -e "${GREEN}Your bot is ready! Follow the steps above.${NC}"
echo ""
