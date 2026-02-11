#!/bin/bash

# Script to install required dependencies for Smart Scale prediction functionality

echo "Installing Smart Scale prediction dependencies..."

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

# Install base requirements
echo "Installing/updating base requirements..."
pip install -r requirements.txt

# Try to install Prophet, but don't fail if it doesn't work
echo "Attempting to install Prophet (optional)..."
pip install prophet || echo "Prophet installation failed. You can still use Linear Regression and ARIMA models."

echo ""
echo "Installation complete! Weight prediction functionality is now available."
echo "You can use the web dashboard to access predictions."
echo ""
echo "Note: If Prophet installation failed, you can still use Linear Regression and ARIMA models."
echo "      Facebook's Prophet requires additional dependencies and might not be available on all systems."

# Tell the user how to restart services if they exist
if [ -f "/etc/systemd/system/smart_scale.service" ] || [ -f "/etc/systemd/system/scale_dashboard.service" ]; then
    echo ""
    echo "To apply changes, restart the services with:"
    echo "sudo systemctl restart scale_dashboard.service"
    echo ""
fi