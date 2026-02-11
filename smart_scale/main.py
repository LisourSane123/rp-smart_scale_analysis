import time
import os
from smart_scale.bluetooth_reader import BluetoothReader
from smart_scale.data_analyzer import DataAnalyzer
from smart_scale.data_storage import DataStorage
from smart_scale.user_identifier import UserIdentifier
from smart_scale.user_manager import UserManager
import smart_scale.config as config

def process_measurement(reader, analyzer_factory, storage, user_identifier, user_manager, last_raw_data_cache):
    """Scans, analyzes, and stores a single measurement, avoiding duplicates."""
    print("\n--- Starting new scan cycle ---")
    user_manager.reload()
    raw_data = reader.get_data()

    if raw_data:
        if raw_data == last_raw_data_cache:
            print("Duplicate measurement detected. Skipping.")
            return last_raw_data_cache  # Return the same cache

        print("New measurement received.")
        
        # First, use a default analyzer to get the weight
        default_analyzer = analyzer_factory(config.DEFAULT_HEIGHT, config.DEFAULT_AGE, config.DEFAULT_SEX)
        temp_data = default_analyzer.analyze(raw_data)
        
        if temp_data:
            # Identify the most likely user based on weight
            weight = temp_data['weight']
            identified_username = user_identifier.identify_user(weight)
            
            # Get user profile
            user_profile = user_manager.get_user(identified_username)
            
            if user_profile:
                print(f"Using profile for user: {user_profile['display_name']}")
                
                # Get age from birthdate or use age directly if it's an older profile
                if "birthdate" in user_profile:
                    current_age = user_manager.calculate_age(user_profile["birthdate"])
                    print(f"Age calculated from birthdate: {current_age} years")
                else:
                    current_age = user_profile.get("age", config.DEFAULT_AGE)
                    print(f"Using stored age: {current_age} years")
                
                # Create a personalized analyzer with the user's parameters
                user_analyzer = analyzer_factory(
                    user_profile['height'],
                    current_age,
                    user_profile['sex']
                )
                
                # Re-analyze with the user's specific parameters
                analyzed_data = user_analyzer.analyze(raw_data)
            else:
                print(f"No profile found for '{identified_username}', using default parameters")
                analyzed_data = temp_data
            
            if analyzed_data:
                print("Analysis complete. Metrics:", analyzed_data)
                
                # Add identified user to the data
                analyzed_data['USER_NAME'] = identified_username
                
                print(f"Measurement assigned to user: {identified_username}")
                print("Saving data to CSV file...")
                storage.save(analyzed_data)
                print(f"Data saved to {config.CSV_FILE}")
                return raw_data  # Return new data to update cache
        else:
            print("Could not analyze data. Please try again.")
    else:
        print(f"No valid data received from {config.MAC_ADDRESS}. Make sure the scale is on and in range.")
    
    return last_raw_data_cache # Return old cache if no new data was saved

def main():
    # Initialize components
    reader = BluetoothReader(config.MAC_ADDRESS)
    storage = DataStorage(config.CSV_FILE)
    
    # Initialize user manager and user identifier
    user_manager = UserManager(config.USERS_FILE)
    user_identifier = UserIdentifier(config.CSV_FILE, user_manager)
    
    # Create an analyzer factory function (to create analyzers with different parameters)
    def create_analyzer(height, age, sex):
        return DataAnalyzer(height, age, sex)
    
    last_raw_data_cache = None

    # Get available usernames from profiles
    usernames = user_manager.get_usernames()
    
    print("Smart Scale script started. Running in continuous mode.")
    print(f"Scanning for {config.MAC_ADDRESS} every {config.SCAN_INTERVAL} seconds.")
    print(f"Available user profiles: {', '.join(usernames) if usernames else 'None - using defaults'}")
    print("Press Ctrl+C to exit.")

    while True:
        try:
            last_raw_data_cache = process_measurement(
                reader, 
                create_analyzer, 
                storage, 
                user_identifier, 
                user_manager,
                last_raw_data_cache
            )
            print(f"Waiting for {config.SCAN_INTERVAL} seconds before next scan...")
            time.sleep(config.SCAN_INTERVAL)

        except KeyboardInterrupt:
            print("\nScript interrupted by user. Exiting.")
            break
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            print("Retrying in 30 seconds...")
            time.sleep(30)


if __name__ == "__main__":
    main()
