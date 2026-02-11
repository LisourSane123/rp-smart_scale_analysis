import pandas as pd
import os
from datetime import datetime

class DataStorage:
    def __init__(self, filename):
        self.filename = filename

    def save(self, data):
        # Define and enforce a consistent column order for CSV
        COLUMNS_ORDER = [
            'weight', 'impedance', 'lbm', 'fat_percentage', 'water_percentage',
            'muscle_mass', 'bone_mass', 'visceral_fat', 'bmi', 'bmr',
            'ideal_weight', 'metabolic_age', 'timestamp', 'USER_NAME'
        ]

        # Ensure all expected keys exist in the input data; fill missing with None
        record = {k: data.get(k, None) for k in COLUMNS_ORDER}

        # Create DataFrame with enforced column order
        df = pd.DataFrame([record], columns=COLUMNS_ORDER)

        # If timestamp is None, set current time
        if df.at[0, 'timestamp'] is None:
            df.at[0, 'timestamp'] = datetime.now()

        # Write or append to CSV with fixed headers
        if not os.path.isfile(self.filename):
            df.to_csv(self.filename, index=False)
        else:
            df.to_csv(self.filename, mode='a', header=False, index=False)

        print(f"Data successfully saved to {self.filename}")
