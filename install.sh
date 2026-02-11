#!/bin/bash
# install.sh - Complete setup script for Smart Scale Analysis on Raspberry Pi 5
# Run with: sudo bash install.sh

set -e

# Make sure we're running as root
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root: sudo $0"
  exit 1
fi

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Define paths
PROJ_DIR=$(dirname "$(readlink -f "$0")")
VENV_DIR="$PROJ_DIR/.venv"
SYSTEMD_DIR="/etc/systemd/system"
PI_USER=$(logname 2>/dev/null || echo "$SUDO_USER")
PI_HOME=$(eval echo ~$PI_USER)
VENV_PYTHON="$VENV_DIR/bin/python3"
CONFIG_FILE="$PROJ_DIR/smart_scale/config.py"

# Dashboard port
DASHBOARD_PORT=11230

echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}   Smart Scale Analysis - Installer${NC}"
echo -e "${GREEN}   Target: Raspberry Pi 5${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo -e "Project directory: ${CYAN}$PROJ_DIR${NC}"
echo -e "Installing for user: ${CYAN}$PI_USER${NC}"
echo ""

# =============================================
# STEP 1: Ask user for scan interval
# =============================================
echo -e "${YELLOW}=== Configuration ===${NC}"
echo ""
echo -e "How often should the scale scan for measurements?"
echo -e "  Min: ${CYAN}10${NC} seconds"
echo -e "  Max: ${CYAN}540${NC} seconds (9 minutes)"
echo -e "  Default: ${CYAN}30${NC} seconds"
echo ""

while true; do
    read -p "Enter scan interval in seconds [30]: " SCAN_INTERVAL
    SCAN_INTERVAL=${SCAN_INTERVAL:-30}

    # Validate: must be a number
    if ! [[ "$SCAN_INTERVAL" =~ ^[0-9]+$ ]]; then
        echo -e "${RED}Error: Please enter a valid number.${NC}"
        continue
    fi

    # Validate: range 10-540
    if [ "$SCAN_INTERVAL" -lt 10 ] || [ "$SCAN_INTERVAL" -gt 540 ]; then
        echo -e "${RED}Error: Value must be between 10 and 540 seconds.${NC}"
        continue
    fi

    echo -e "${GREEN}Scan interval set to: ${SCAN_INTERVAL} seconds${NC}"
    break
done

echo ""

# =============================================
# STEP 2: Install system dependencies
# =============================================
echo -e "${YELLOW}=== [1/6] Installing system dependencies ===${NC}"
apt-get update -qq
apt-get install -y \
    python3-pip \
    python3-venv \
    python3-dev \
    bluez \
    bluez-tools \
    bluetooth \
    libbluetooth-dev \
    libglib2.0-dev

echo -e "${GREEN}System dependencies installed.${NC}"

# =============================================
# STEP 3: Create virtual environment
# =============================================
echo -e "\n${YELLOW}=== [2/6] Setting up Python virtual environment ===${NC}"
if [ ! -d "$VENV_DIR" ]; then
    sudo -u $PI_USER python3 -m venv $VENV_DIR
    echo -e "${GREEN}Virtual environment created.${NC}"
else
    echo -e "Virtual environment already exists, skipping."
fi

# =============================================
# STEP 4: Install Python dependencies
# =============================================
echo -e "\n${YELLOW}=== [3/6] Installing Python dependencies ===${NC}"
sudo -u $PI_USER $VENV_DIR/bin/pip install --upgrade pip -q
sudo -u $PI_USER $VENV_DIR/bin/pip install -r "$PROJ_DIR/requirements.txt" -q

# Try to install Prophet (optional, often fails on RPi)
echo -e "Attempting to install Prophet (optional)..."
sudo -u $PI_USER $VENV_DIR/bin/pip install prophet -q 2>/dev/null && \
    echo -e "${GREEN}Prophet installed successfully.${NC}" || \
    echo -e "${YELLOW}Prophet not available - Linear Regression and ARIMA will still work.${NC}"

echo -e "${GREEN}Python dependencies installed.${NC}"

# =============================================
# STEP 5: Configure scan interval
# =============================================
echo -e "\n${YELLOW}=== [4/6] Applying configuration ===${NC}"

# Update SCAN_INTERVAL in config.py
if [ -f "$CONFIG_FILE" ]; then
    sed -i "s/^SCAN_INTERVAL = .*/SCAN_INTERVAL = ${SCAN_INTERVAL}  # Time in seconds between scans/" "$CONFIG_FILE"
    echo -e "Scan interval set to ${CYAN}${SCAN_INTERVAL}${NC} seconds in config.py"
else
    echo -e "${RED}Warning: config.py not found at $CONFIG_FILE${NC}"
fi

# =============================================
# STEP 6: Set permissions
# =============================================
echo -e "\n${YELLOW}=== [5/6] Setting permissions ===${NC}"

# Set Bluetooth capabilities
setcap 'cap_net_raw,cap_net_admin+eip' $VENV_PYTHON
echo -e "Bluetooth capabilities set for Python."

# Fix ownership
chown -R $PI_USER:$PI_USER $PROJ_DIR
echo -e "File ownership set to ${CYAN}$PI_USER${NC}."

# =============================================
# STEP 7: Create and install systemd services
# =============================================
echo -e "\n${YELLOW}=== [6/6] Installing systemd services ===${NC}"

# Check prerequisites
if [ ! -f "$PROJ_DIR/smart_scale/main.py" ]; then
    echo -e "${RED}Error: smart_scale/main.py not found.${NC}"
    exit 1
fi

if [ ! -f "$VENV_PYTHON" ]; then
    echo -e "${RED}Error: Python not found at $VENV_PYTHON${NC}"
    exit 1
fi

# Create smart_scale measurement service
cat > $SYSTEMD_DIR/smart_scale.service << EOL
[Unit]
Description=Smart Scale Measurement Service
After=network.target bluetooth.target
Wants=bluetooth.target

[Service]
Type=simple
User=$PI_USER
WorkingDirectory=$PROJ_DIR
ExecStart=$VENV_PYTHON -m smart_scale.main
Restart=always
RestartSec=10
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=smart_scale
Environment="PYTHONUNBUFFERED=1"

[Install]
WantedBy=multi-user.target
EOL

# Create dashboard service
cat > $SYSTEMD_DIR/scale_dashboard.service << EOL
[Unit]
Description=Smart Scale Dashboard Service
After=network.target smart_scale.service
Wants=smart_scale.service

[Service]
Type=simple
User=$PI_USER
WorkingDirectory=$PROJ_DIR
ExecStart=$VENV_PYTHON webapp/app.py
Restart=always
RestartSec=10
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=scale_dashboard
Environment="PYTHONUNBUFFERED=1"

[Install]
WantedBy=multi-user.target
EOL

# Set permissions and reload
chmod 644 $SYSTEMD_DIR/smart_scale.service
chmod 644 $SYSTEMD_DIR/scale_dashboard.service
systemctl daemon-reload

# Enable services
systemctl enable smart_scale.service
systemctl enable scale_dashboard.service

echo -e "${GREEN}Services installed and enabled.${NC}"

# =============================================
# DONE
# =============================================
echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}   Installation Complete!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo -e "Configuration:"
echo -e "  Scan interval:  ${CYAN}${SCAN_INTERVAL} seconds${NC}"
echo -e "  Dashboard port: ${CYAN}${DASHBOARD_PORT}${NC}"
echo -e "  Dashboard URL:  ${CYAN}http://<raspberry-pi-ip>:${DASHBOARD_PORT}${NC}"
echo ""
echo -e "Service commands:"
echo -e "  ${CYAN}sudo systemctl start smart_scale${NC}        - Start scale scanner"
echo -e "  ${CYAN}sudo systemctl start scale_dashboard${NC}    - Start web dashboard"
echo -e "  ${CYAN}sudo systemctl status smart_scale${NC}       - Check scanner status"
echo -e "  ${CYAN}sudo systemctl status scale_dashboard${NC}   - Check dashboard status"
echo ""
echo -e "Manual usage:"
echo -e "  ${CYAN}source $VENV_DIR/bin/activate${NC}"
echo -e "  ${CYAN}python3 -m smart_scale.main${NC}             - Run scanner"
echo -e "  ${CYAN}python3 webapp/app.py${NC}                   - Run dashboard"
echo ""
echo -e "User management:"
echo -e "  ${CYAN}python3 manage_users.py list${NC}            - List users"
echo -e "  ${CYAN}python3 manage_users.py add <args>${NC}      - Add user"
echo ""

# Ask if user wants to start services now
read -p "Start services now? (y/N): " START_NOW
if [[ "$START_NOW" =~ ^[yY]$ ]]; then
    systemctl start smart_scale.service
    systemctl start scale_dashboard.service
    echo -e "${GREEN}Services started!${NC}"
    echo -e "Dashboard available at: ${CYAN}http://$(hostname -I | awk '{print $1}'):${DASHBOARD_PORT}${NC}"
fi
