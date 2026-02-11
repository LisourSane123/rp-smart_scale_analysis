# Smart Scale Data Logger

## Overview

This project is a Python script that continuously scans for a Xiaomi Mi Smart Scale 2 (or compatible device), captures stabilized weight and impedance data, calculates a comprehensive set of body metrics, and saves them to a CSV file. It's designed to run in the background, automatically logging new measurements while intelligently ignoring duplicates.

## How to Run

1.  **Configuration**: Open `smart_scale/config.py` and update these settings:
    *   `MAC_ADDRESS`: The MAC address of your smart scale.
    *   `SCAN_INTERVAL`: Time in seconds between scan cycles (e.g., `30`).
    *   `DEFAULT_HEIGHT`, `DEFAULT_AGE`, `DEFAULT_SEX`: These will be used if no specific user profile is found.
    
    Then set up user profiles using the user management tool (see "Managing User Profiles" section below).

2.  **Activate Virtual Environment**:
    ```bash
    source .venv/bin/activate
    ```

3.  **Run the Script**:
    ```bash
    python3 -m smart_scale.main
    ```
    The script will now run in a continuous loop. You can stop it at any time by pressing `Ctrl+C`.

4.  **Run the Dashboard (web UI)**:
        - Open a new terminal (keep the measurement script running in its terminal or run it as a service).
        - Activate the same virtual environment:
            ```bash
            source .venv/bin/activate
            ```
        - Start the Flask dashboard:
            ```bash
            python3 webapp/app.py
            ```
        - By default the dashboard listens on port 5000. Open http://<your-pi-ip>:5000 in a browser to view charts and download the CSV.

5.  **Run both together**:
        - Option A (development): Run each command in its own terminal after activating the venv in both.
        - Option B (production): Run `smart_scale.main` as a background service (systemd) and run the dashboard in the foreground or behind a reverse proxy.

## Auto-Starting on Raspberry Pi Boot

This project is designed to run on a Raspberry Pi Zero 2 W. You can set up the services to start automatically on boot using either the automated setup script or following the manual steps.

### Option 1: Automated Setup (Recommended)

1. **Run the setup script with sudo**:
   ```bash
   sudo ./setup_autostart.sh
   ```

   This script will:
   - Create and configure the systemd service files
   - Set the appropriate permissions
   - Configure Bluetooth capabilities
   - Enable the services to start on boot
   - Start the services immediately

2. **Verify the services are running**:
   ```bash
   sudo systemctl status smart_scale.service
   sudo systemctl status scale_dashboard.service
   ```

3. **Access the dashboard** by opening a web browser and navigating to:
   ```
   http://<your-pi-ip>:5000
   ```

### Option 2: Manual Setup

If you prefer to set up the services manually, follow these steps:

1. **Copy the service files to the systemd directory**:
   ```bash
   sudo cp /home/pi/dywidenty/smart_scale.service /etc/systemd/system/
   sudo cp /home/pi/dywidenty/scale_dashboard.service /etc/systemd/system/
   ```

2. **Set proper permissions**:
   ```bash
   sudo chmod 644 /etc/systemd/system/smart_scale.service
   sudo chmod 644 /etc/systemd/system/scale_dashboard.service
   ```

3. **Reload systemd to recognize the new services**:
   ```bash
   sudo systemctl daemon-reload
   ```

4. **Enable both services to start on boot**:
   ```bash
   sudo systemctl enable smart_scale.service
   sudo systemctl enable scale_dashboard.service
   ```

5. **Start the services immediately**:
   ```bash
   sudo systemctl start smart_scale.service
   sudo systemctl start scale_dashboard.service
   ```

6. **Check status of the services**:
   ```bash
   sudo systemctl status smart_scale.service
   sudo systemctl status scale_dashboard.service
   ```

7. **View logs if there are issues**:
   ```bash
   sudo journalctl -u smart_scale.service -f
   sudo journalctl -u scale_dashboard.service -f
   ```

### Setting Bluetooth Permissions

To allow the bluetooth scanning to work without root privileges:

```bash
sudo setcap 'cap_net_raw,cap_net_admin+eip' $(readlink -f $(which python3))
```

If you're using a virtual environment:

```bash
sudo setcap 'cap_net_raw,cap_net_admin+eip' /home/pi/dywidenty/.venv/bin/python3
```

## Notes on CSV Data

The CSV file (`scale_data.csv`) is generated with the following columns:

- `weight` (kg): Your weight in kilograms
- `impedance` (ohm): Bioelectrical impedance measurement
- `lbm` (kg): Lean Body Mass
- `fat_percentage` (%): Body fat percentage
- `water_percentage` (%): Body water percentage
- `muscle_mass` (kg): Muscle mass
- `bone_mass` (kg): Bone mass
- `visceral_fat`: Visceral fat index
- `bmi`: Body Mass Index
- `bmr`: Basal Metabolic Rate (calories)
- `ideal_weight` (kg): Ideal weight based on height
- `metabolic_age` (years): Metabolic age
- `timestamp`: Date and time of measurement
- `USER_NAME`: Automatically assigned user name based on weight statistics

## Code Structure and Data Flow

The project is modular, with each component having a specific responsibility, creating a clear data flow.

1.  **`config.py`**:
    *   **Role**: Central configuration file. All user-specific settings and application parameters are stored here.
    *   **Flow**: Provides constants used by all other modules.

2.  **`main.py`**:
    *   **Role**: The main entry point and orchestrator of the application.
    *   **Flow**:
        1.  Initializes all components (`BluetoothReader`, `DataAnalyzer`, `DataStorage`, `UserIdentifier`).
        2.  Starts an infinite loop to ensure continuous operation.
        3.  In each cycle, it calls `BluetoothReader` to scan for data.
        4.  It maintains a **cache** of the last measurement to avoid saving duplicate data.
        5.  If new, unique data is received, it's passed to `DataAnalyzer`.
        6.  The calculated metrics are then sent to `DataStorage` to be saved.
        7.  Finally, it waits for the configured `SCAN_INTERVAL` before starting the next cycle.

3.  **`bluetooth_reader.py`**:
    *   **Role**: Handles all Bluetooth Low Energy (BLE) communication.
    *   **Flow**: Scans for advertisement packets from the scale's MAC address. It inspects these packets to find one that contains a **stabilized measurement with impedance**, which is the signal that a valid measurement is complete.

4.  **`data_analyzer.py`**:
    *   **Role**: The "brain" of the application. Contains the core logic for calculating body metrics.
    *   **Flow**: Receives the raw byte data from `BluetoothReader`. It then uses a series of complex, scientifically-derived formulas to compute all the health indicators.

5.  **`data_storage.py`**:
    *   **Role**: Manages the persistence of the data.
    *   **Flow**: Takes the final dictionary of calculated metrics from `DataAnalyzer` and appends it as a new row to the specified CSV file. If the file doesn't exist, it creates it and adds the appropriate headers.

6.  **`user_identifier.py`**:
    *   **Role**: Identifies which user a measurement belongs to based on weight statistics.
    *   **Flow**: Uses historical data to calculate mean and standard deviation of weights for each user, then scores new measurements to determine the most likely user.

7.  **`user_manager.py`**:
    *   **Role**: Manages user profiles with individual height, age, sex, and display name.
    *   **Flow**: Loads and saves user profiles from/to a JSON file, and provides methods to add, update, or delete users.

## Weight Prediction

The Smart Scale now features advanced weight prediction capabilities to help you track your weight trends and forecast future values. The prediction system offers multiple forecasting models with confidence intervals:

### Prediction Models

1. **Linear Regression**:
   - Simple and intuitive model that predicts future weight based on linear trends in your historical data
   - Provides 95% confidence intervals for prediction uncertainty
   - Works well with limited data (minimum 5 measurements)

2. **ARIMA (AutoRegressive Integrated Moving Average)**:
   - More sophisticated time series forecasting model that captures complex patterns
   - Automatically detects if your weight data is stationary and adjusts accordingly
   - Provides robust predictions with confidence intervals
   - Requires more historical data (minimum 10 measurements)

3. **Prophet**:
   - Facebook's advanced forecasting model designed for time series with seasonality
   - Capable of detecting weekly patterns in your weight data
   - Handles missing data and trend changes well
   - Provides detailed 95% confidence intervals
   - Requires Prophet package installation (optional)

### Using the Prediction Feature

1. In the web dashboard, scroll to the "Weight Prediction" section
2. Select your desired prediction model from the dropdown:
   - Linear Regression (default)
   - ARIMA
   - Prophet (if installed)
   - Compare All Models
3. Choose your desired prediction timeframe:
   - 1 Week
   - 1 Month (default)
   - 3 Months
   - 6 Months
   - 1 Year
4. Click "Update Prediction" to generate the forecast
5. The chart will display your historical weight measurements, predicted future values, and 95% confidence intervals

### How It Works

The prediction system analyzes your historical weight data to identify patterns and trends. Based on the selected model, it calculates the most likely future weight values along with statistical confidence intervals. The 95% confidence intervals represent the range where your actual future weight is likely to fall with 95% probability, allowing you to understand the uncertainty of the predictions.

## Managing User Profiles

The smart scale now supports multiple users with individual profiles. Each user can have their own height, age, sex, and display name. When a measurement is taken, the system automatically identifies the most likely user based on weight statistics and uses that user's profile parameters for body metrics calculations.

### Using the User Management Tool

A command-line tool is provided to manage user profiles:

1. **List all users**:
   ```bash
   ./manage_users.py list
   ```

2. **Add a new user**:
   ```bash
   ./manage_users.py add username "Display Name" height birthdate sex
   ```
   Example:
   ```bash
   ./manage_users.py add john "John Smith" 182 1990-05-15 male
   ```

3. **Update an existing user**:
   ```bash
   ./manage_users.py update username --display-name "New Name" --height 180 --birthdate 1990-05-15 --sex male
   ```
   You can update any combination of fields.

4. **Show user details**:
   ```bash
   ./manage_users.py show username
   ```

5. **Delete a user**:
   ```bash
   ./manage_users.py delete username
   ```

6. **Export all users to a file**:
   ```bash
   ./manage_users.py export users_backup.json
   ```

7. **Import users from a file**:
   ```bash
   ./manage_users.py import users_backup.json
   ```

### How User Identification Works

When a measurement is taken:

1. The system first determines the weight value
2. It looks at historical measurements to calculate average weights for each user
3. It assigns the measurement to the most statistically likely user based on weight patterns
4. It uses that user's personal profile data (height, birthdate-calculated age, sex) to calculate accurate body metrics

This allows multiple people to use the same scale while maintaining separate, personalized measurements.