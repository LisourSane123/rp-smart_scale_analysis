#!/bin/bash
# install.sh - Complete setup script for Smart Scale Analysis project
# Run with: sudo bash install.sh

# Make sure we're running as root
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root: sudo $0"
  exit 1
fi

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Define paths
PROJ_DIR=$(dirname "$(readlink -f "$0")")
VENV_DIR="$PROJ_DIR/.venv"
PI_USER=$(logname)
PI_HOME=$(eval echo ~$PI_USER)

echo -e "${GREEN}=== Smart Scale Analysis Installation ===${NC}"
echo -e "Project directory: $PROJ_DIR"
echo -e "Installing for user: $PI_USER"

# Install system dependencies
echo -e "\n${YELLOW}Installing system dependencies...${NC}"
apt-get update
apt-get install -y \
    python3-pip \
    python3-venv \
    python3-dev \
    bluez \
    bluez-tools \
    bluetooth \
    libbluetooth-dev \
    libglib2.0-dev

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo -e "\n${YELLOW}Creating Python virtual environment...${NC}"
    sudo -u $PI_USER python3 -m venv $VENV_DIR
fi

# Install Python dependencies
echo -e "\n${YELLOW}Installing Python dependencies...${NC}"
sudo -u $PI_USER $VENV_DIR/bin/pip install -r "$PROJ_DIR/requirements.txt"

# Set permissions for Bluetooth access
echo -e "\n${YELLOW}Setting Bluetooth permissions...${NC}"
setcap 'cap_net_raw,cap_net_admin+eip' $VENV_DIR/bin/python3

# Fix ownership of project files
echo -e "\n${YELLOW}Setting correct file ownership...${NC}"
chown -R $PI_USER:$PI_USER $PROJ_DIR

# Make setup script executable
chmod +x "$PROJ_DIR/setup_autostart.sh"

echo -e "\n${GREEN}=== Installation Complete! ===${NC}"
echo -e "You can now configure your user settings in ${YELLOW}smart_scale/config.py${NC}"
echo -e "Then run the autostart setup script with: ${YELLOW}sudo $PROJ_DIR/setup_autostart.sh${NC}"
echo -e "\nOr run manually with:"
echo -e "${YELLOW}source $VENV_DIR/bin/activate${NC}"
echo -e "${YELLOW}python3 -m smart_scale.main${NC}"
echo -e "\nFor the web dashboard, open another terminal and run:"
echo -e "${YELLOW}source $VENV_DIR/bin/activate${NC}"
echo -e "${YELLOW}python3 webapp/app.py${NC}"