#!/bin/bash

# Script to install system services for smart scale and dashboard

# Get current directory
PROJECT_DIR=$(pwd)
CURRENT_USER=$(whoami)

echo "Installing Smart Scale services..."
echo "Project directory: $PROJECT_DIR"

# Copy service files to systemd directory
echo "Copying service files..."
sudo cp "$PROJECT_DIR/smart_scale.service" /etc/systemd/system/
sudo cp "$PROJECT_DIR/scale_dashboard.service" /etc/systemd/system/

# Set proper permissions
echo "Setting permissions..."
sudo chmod 644 /etc/systemd/system/smart_scale.service
sudo chmod 644 /etc/systemd/system/scale_dashboard.service

# Reload systemd to recognize the new services
echo "Reloading systemd..."
sudo systemctl daemon-reload

# Setting Bluetooth permissions if needed
echo "Setting Bluetooth permissions..."
if [ -f "$PROJECT_DIR/.venv/bin/python3" ]; then
    sudo setcap 'cap_net_raw,cap_net_admin+eip' "$PROJECT_DIR/.venv/bin/python3"
else
    echo "Warning: .venv python3 not found, skipping capabilities set."
fi

# Enable both services to start on boot
echo "Enabling services..."
sudo systemctl enable smart_scale.service
sudo systemctl enable scale_dashboard.service

echo ""
echo "Services installed successfully!"
echo ""
echo "To start the services now, run:"
echo "sudo systemctl start smart_scale.service"
echo "sudo systemctl start scale_dashboard.service"
echo ""
echo "To check service status:"
echo "sudo systemctl status smart_scale.service"
echo "sudo systemctl status scale_dashboard.service"
echo ""
