#!/bin/bash
# setup_autostart.sh - Configure the Smart Scale services to run on boot

# Make sure we're running as root
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root: sudo $0"
  exit 1
fi

# Define paths
PROJ_DIR=$(dirname "$(readlink -f "$0")")
SYSTEMD_DIR="/etc/systemd/system"
VENV_PYTHON="$PROJ_DIR/.venv/bin/python3"

echo "=== Smart Scale Autostart Setup ==="
echo "Project directory: $PROJ_DIR"

# Check if the project and virtual environment exist
if [ ! -f "$PROJ_DIR/smart_scale/main.py" ]; then
    echo "Error: smart_scale/main.py not found in $PROJ_DIR."
    echo "Please run this script from the project directory."
    exit 1
fi

if [ ! -f "$VENV_PYTHON" ]; then
    echo "Error: Virtual environment Python not found at $VENV_PYTHON"
    echo "Please create and activate a virtual environment first."
    exit 1
fi

# Create the measurement service file
echo "Creating smart_scale.service..."
cat > $SYSTEMD_DIR/smart_scale.service << EOL
[Unit]
Description=Smart Scale Measurement Service
After=network.target bluetooth.target
Wants=bluetooth.target

[Service]
Type=simple
User=$(whoami)
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

# Create the dashboard service file
echo "Creating scale_dashboard.service..."
cat > $SYSTEMD_DIR/scale_dashboard.service << EOL
[Unit]
Description=Smart Scale Dashboard Service
After=network.target smart_scale.service
Wants=smart_scale.service

[Service]
Type=simple
User=$(whoami)
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

# Set proper permissions
echo "Setting permissions..."
chmod 644 $SYSTEMD_DIR/smart_scale.service
chmod 644 $SYSTEMD_DIR/scale_dashboard.service

# Set Bluetooth capabilities
echo "Setting Bluetooth capabilities for Python..."
setcap 'cap_net_raw,cap_net_admin+eip' $VENV_PYTHON

# Reload systemd
echo "Reloading systemd daemon..."
systemctl daemon-reload

# Enable services
echo "Enabling services to start on boot..."
systemctl enable smart_scale.service
systemctl enable scale_dashboard.service

echo "Starting services now..."
systemctl start smart_scale.service
systemctl start scale_dashboard.service

echo ""
echo "=== Setup Complete! ==="
echo "Services are now configured to start automatically on boot."
echo ""
echo "To check status:"
echo "  sudo systemctl status smart_scale.service"
echo "  sudo systemctl status scale_dashboard.service"
echo ""
echo "To view logs:"
echo "  sudo journalctl -u smart_scale.service -f"
echo "  sudo journalctl -u scale_dashboard.service -f"
echo ""
echo "Access the dashboard at: http://$(hostname -I | awk '{print $1}'):5000"