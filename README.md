# Smart Scale Data Logger

## Overview

Python application for Raspberry Pi 5 that continuously scans for a Xiaomi Mi Smart Scale 2 (or compatible BLE device), captures stabilized weight and impedance data, calculates body metrics, and saves them to a CSV file. Includes a web dashboard for data visualization and weight prediction.

## Quick Start (Raspberry Pi 5)

### Installation

Everything is handled by a single install script:

```bash
sudo bash install.sh
```

During installation you will be asked to set the **scan interval** (how often the scale scans for measurements):
- Minimum: **10 seconds**
- Maximum: **540 seconds** (9 minutes)
- Default: **30 seconds**

The installer will:
1. Install system dependencies (Bluetooth, Python, etc.)
2. Create a Python virtual environment
3. Install all Python packages
4. Apply your scan interval configuration
5. Set Bluetooth permissions
6. Create and enable systemd services

### Configuration

Before running, update the scale MAC address in `smart_scale/config.py`:

```python
MAC_ADDRESS = "88:22:b2:a7:ce:b6"  # Your scale's MAC address
```

Set up user profiles:

```bash
source .venv/bin/activate
python3 manage_users.py add username "Display Name" height birthdate sex
# Example:
python3 manage_users.py add john "John Smith" 182 1990-05-15 male
```

### Service Commands

```bash
# Start/stop services
sudo systemctl start smart_scale
sudo systemctl start scale_dashboard

# Check status
sudo systemctl status smart_scale
sudo systemctl status scale_dashboard

# View logs
sudo journalctl -u smart_scale -f
sudo journalctl -u scale_dashboard -f
```

### Dashboard

The web dashboard runs on port **11230**:

```
http://<raspberry-pi-ip>:11230
```

### Manual Usage

```bash
source .venv/bin/activate
python3 -m smart_scale.main    # Run scanner
python3 webapp/app.py           # Run dashboard
```

## CSV Data Format

The CSV file (`scale_data.csv`) contains:

| Column | Unit | Description |
|--------|------|-------------|
| `weight` | kg | Weight |
| `impedance` | ohm | Bioelectrical impedance |
| `lbm` | kg | Lean Body Mass |
| `fat_percentage` | % | Body fat percentage |
| `water_percentage` | % | Body water percentage |
| `muscle_mass` | kg | Muscle mass |
| `bone_mass` | kg | Bone mass |
| `visceral_fat` | - | Visceral fat index |
| `bmi` | - | Body Mass Index |
| `bmr` | cal | Basal Metabolic Rate |
| `ideal_weight` | kg | Ideal weight |
| `metabolic_age` | years | Metabolic age |
| `timestamp` | - | Date and time |
| `USER_NAME` | - | Auto-assigned user |

## Project Structure

```
├── install.sh                 # Single unified installer
├── requirements.txt           # Python dependencies
├── manage_users.py            # CLI user management tool
├── fix_csv.py                 # CSV data repair utility
├── smart_scale/
│   ├── config.py              # Configuration (MAC, scan interval, defaults)
│   ├── main.py                # Main entry point / orchestrator
│   ├── bluetooth_reader.py    # BLE communication with scale
│   ├── data_analyzer.py       # Body metrics calculation
│   ├── data_storage.py        # CSV file persistence
│   ├── user_identifier.py     # Auto user identification by weight
│   ├── user_manager.py        # User profile CRUD
│   ├── weight_predictor.py    # Prediction models (Linear, ARIMA, Prophet)
│   ├── weight_visualizer.py   # Plotly chart generation
│   └── users.json             # User profiles storage
└── webapp/
    ├── app.py                 # Flask web dashboard (port 11230)
    └── templates/
        ├── index.html         # Main dashboard page
        └── page2.html         # Secondary page
```

## Weight Prediction

The dashboard includes weight prediction with multiple models:

- **Linear Regression** - simple trend-based (min 5 measurements)
- **ARIMA** - time series forecasting (min 10 measurements)
- **Prophet** - Facebook's seasonal model (optional, installed if available)

All models provide 95% confidence intervals. Select model and timeframe (1 week to 1 year) in the dashboard.

## Managing User Profiles

```bash
python3 manage_users.py list                                    # List all
python3 manage_users.py add john "John" 182 1990-05-15 male     # Add user
python3 manage_users.py update john --height 183                # Update
python3 manage_users.py show john                               # Show details
python3 manage_users.py delete john                             # Delete
python3 manage_users.py export backup.json                      # Export
python3 manage_users.py import backup.json                      # Import
```

The system automatically identifies users by comparing new measurements against historical weight statistics (z-score based matching).
