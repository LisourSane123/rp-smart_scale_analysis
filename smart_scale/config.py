import os

# Configuration for the smart scale
MAC_ADDRESS = "88:22:b2:a7:ce:b6"
# Default values (used as fallback if user profile not found)
DEFAULT_HEIGHT = 180  # in cm
DEFAULT_AGE = 30
DEFAULT_SEX = "male"  # "male" or "female"
DEFAULT_USER = "Default User"  # Default name (fallback)

# File paths
# Get the absolute path of the directory where this project is located (root of the repo)
# Assuming config.py is in <root>/smart_scale/
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CSV_FILE = os.path.join(PROJECT_ROOT, "scale_data.csv")
USERS_FILE = os.path.join(PROJECT_ROOT, "smart_scale", "users.json")

# Scan settings
SCAN_INTERVAL = 10 # Time in seconds between scans
