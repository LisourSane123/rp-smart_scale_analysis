#!/usr/bin/env python3
"""
Script to fix malformed CSV data in the scale_data.csv file.
This script will:
1. Read the current CSV file
2. Detect and fix malformed rows
3. Ensure all data is in the correct format
4. Save the fixed data back to the file
"""

import pandas as pd
import os
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Path to the CSV file
CSV_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scale_data.csv')
BACKUP_FILE_PATH = CSV_FILE_PATH + '.bak'

def fix_csv_file():
    """Fix the CSV file by ensuring all data is in the correct format."""
    logging.info(f"Checking CSV file: {CSV_FILE_PATH}")
    
    # Create a backup if it doesn't exist
    if not os.path.exists(BACKUP_FILE_PATH):
        logging.info(f"Creating backup at: {BACKUP_FILE_PATH}")
        try:
            with open(CSV_FILE_PATH, 'r') as src, open(BACKUP_FILE_PATH, 'w') as dst:
                dst.write(src.read())
        except Exception as e:
            logging.error(f"Failed to create backup: {e}")
            return
    
    # Read the CSV file
    try:
        df = pd.read_csv(CSV_FILE_PATH)
        logging.info(f"Read {len(df)} rows from CSV")
    except Exception as e:
        logging.error(f"Failed to read CSV: {e}")
        return
    
    # Check if we have the expected headers (matching smart_scale/data_storage.py)
    expected_headers = ['weight', 'impedance', 'lbm', 'fat_percentage', 'water_percentage',
                      'muscle_mass', 'bone_mass', 'visceral_fat', 'bmi', 'bmr', 'ideal_weight',
                      'metabolic_age', 'timestamp', 'USER_NAME']
    
    # Check if columns are present
    missing_cols = [col for col in expected_headers if col not in df.columns]
    if missing_cols:
         logging.warning(f"Missing columns: {missing_cols}. Adding them with empty values.")
         for col in missing_cols:
             df[col] = None

    # Reorder columns to match expected order
    df = df[expected_headers]

    malformed_rows = 0
    fixed_rows = 0
    
    # Check for rows with username in first column
    if df.iloc[:, 0].astype(str).str.contains('[a-zA-Z]').any():
        malformed_rows = df.iloc[:, 0].astype(str).str.contains('[a-zA-Z]').sum()
        logging.info(f"Found {malformed_rows} rows with non-numeric values in first column")
        
        # Filter out these rows
        df = df[~df.iloc[:, 0].astype(str).str.contains('[a-zA-Z]')]
        fixed_rows += malformed_rows
    
    # Make sure weight column contains only numeric values
    try:
        df['weight'] = pd.to_numeric(df['weight'], errors='coerce')
        nan_count = df['weight'].isna().sum()
        if nan_count > 0:
            logging.info(f"Found {nan_count} rows with non-numeric weight values")
            df = df.dropna(subset=['weight'])
            fixed_rows += nan_count
    except Exception as e:
        logging.warning(f"Error processing weight column: {e}")
    
    # Make sure timestamp is in correct format
    try:
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        nan_count = df['timestamp'].isna().sum()
        if nan_count > 0:
            logging.info(f"Found {nan_count} rows with invalid timestamp values")
            df = df.dropna(subset=['timestamp'])
            fixed_rows += nan_count
    except Exception as e:
        logging.warning(f"Error processing timestamp column: {e}")
    
    # Save the fixed data
    try:
        df.to_csv(CSV_FILE_PATH, index=False)
        logging.info(f"Saved {len(df)} rows to CSV file after fixing {fixed_rows} issues")
    except Exception as e:
        logging.error(f"Failed to save fixed CSV: {e}")
        return
    
    logging.info("CSV fix completed successfully")

if __name__ == "__main__":
    fix_csv_file()