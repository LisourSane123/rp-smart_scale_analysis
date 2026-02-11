# Smart Scale Data Logger

# Smart Scale Data Logger

## Overview

This project is a Python script that continuously scans for a Xiaomi Mi Smart Scale 2 (or compatible device), captures stabilized weight and impedance data, calculates a comprehensive set of body metrics, and saves them to a CSV file. It's designed to run in the background, automatically logging new measurements while intelligently ignoring duplicates.

## How to Run

1.  **Configuration**: Open `smart_scale/config.py` and fill in your personal details:
    *   `MAC_ADDRESS`: The MAC address of your smart scale.
    *   `HEIGHT`: Your height in cm.
    *   `AGE`: Your current age.
    *   `SEX`: Your biological sex (`"male"` or `"female"`).
    *   `SCAN_INTERVAL`: Time in seconds between scan cycles (e.g., `30`).

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
        - Option B (production): Run `smart_scale.main` as a background service (systemd) and run the dashboard in the foreground or behind a reverse proxy. Example minimal systemd unit (edit paths and user):

            ```ini
            [Unit]
            Description=Smart Scale measurement service
            After=network.target

            [Service]
            User=pi
            WorkingDirectory=/home/pi/dywidenty
            ExecStart=/home/pi/dywidenty/.venv/bin/python3 -m smart_scale.main
            Restart=always

            [Install]
            WantedBy=multi-user.target
            ```

            Save as `/etc/systemd/system/smart_scale.service`, then enable/start with `sudo systemctl enable --now smart_scale.service`.

6.  **Notes / Permissions**:
        - If you get Bluetooth permission errors when scanning, either run the measurement script as root or grant the Python executable the required capabilities (example):
            ```bash
            sudo setcap 'cap_net_raw,cap_net_admin+eip' $(which python3)
            ```
        - The CSV file generated is `../scale_data.csv` relative to this directory (project root). By default it's ignored by git.

## Code Structure and Data Flow

The project is modular, with each component having a specific responsibility, creating a clear data flow.

1.  **`config.py`**:
    *   **Role**: Central configuration file. All user-specific settings and application parameters are stored here.
    *   **Flow**: Provides constants used by all other modules.

2.  **`main.py`**:
    *   **Role**: The main entry point and orchestrator of the application.
    *   **Flow**:
        1.  Initializes all components (`BluetoothReader`, `DataAnalyzer`, `DataStorage`).
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

## Data Metrics Description

The script saves the following metrics to `scale_data.csv`:

*   **`weight` (kg)**: Your weight in kilograms.
*   **`impedance` (ohm)**: Bioelectrical impedance. A measure of your body's resistance to a small, safe electrical current. It is a key value used to calculate the rest of the metrics, as different body tissues (fat, muscle, water) have different conductivity.
*   **`lbm` (kg)**: Lean Body Mass. Your total weight minus all fat mass. This includes the weight of your muscles, bones, organs, and water.
*   **`fat_percentage` (%)**: The percentage of your body's total mass that is composed of fat tissue.
*   **`water_percentage` (%)**: The percentage of water in your body. Proper hydration is crucial for overall health.
*   **`bone_mass` (kg)**: The estimated mass of your skeleton.
*   **`muscle_mass` (kg)**: The estimated total mass of all muscles in your body.
*   **`visceral_fat`**: An index for the fat stored around your internal organs in the abdomen (truncal fat). High levels are strongly linked to health risks like heart disease and type 2 diabetes.
*   **`bmi`**: Body Mass Index. A simple ratio of weight to height, used to quickly classify if your weight is in a healthy range.
*   **`bmr`**: Basal Metabolic Rate. The number of calories your body burns at rest over 24 hours to maintain vital functions like breathing and circulation.
*   **`ideal_weight` (kg)**: An estimated ideal weight for your height and sex, based on common health formulas.
*   **`metabolic_age` (years)**: Compares your Basal Metabolic Rate (BMR) to the average BMR of your chronological age group. If your metabolic age is lower than your actual age, it's a good indicator of a healthy metabolism.

