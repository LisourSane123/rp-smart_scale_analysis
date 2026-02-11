import pandas as pd
import numpy as np
import os
import smart_scale.config as config
from smart_scale.user_manager import UserManager

class UserIdentifier:
    """
    Class responsible for identifying which user a measurement belongs to
    based on statistical likelihood from historical data.
    """
    
    def __init__(self, csv_file, user_manager=None):
        """
        Initialize with the path to the CSV file containing historical measurements.
        """
        self.csv_file = csv_file
        if user_manager:
            self.user_manager = user_manager
        else:
            self.user_manager = UserManager(config.USERS_FILE)
        
    def get_user_stats(self):
        """
        Calculate mean and standard deviation of weight for each user
        from historical data.
        
        Returns:
            dict: Dictionary with user names as keys and tuples of (mean, std) as values
        """
        # Get usernames from user profiles
        usernames = self.user_manager.get_usernames()
        
        # If no users are defined, use a default user
        if not usernames:
            usernames = [config.DEFAULT_USER]
            
        # Default stats for users with no history
        # Use reasonable defaults as fallback: mean=70kg, std=5kg
        default_stats = {user: (70.0, 5.0) for user in usernames}
        
        # If file doesn't exist, return default stats
        if not os.path.exists(self.csv_file):
            return default_stats
            
        try:
            df = pd.read_csv(self.csv_file)
            
            # Check if required columns exist
            if 'USER_NAME' not in df.columns or 'weight' not in df.columns:
                return default_stats
                
            # Calculate stats for each user
            stats = {}
            for username in usernames:
                user_data = df[df['USER_NAME'] == username]
                
                if len(user_data) >= 2:  # Need at least 2 data points for std
                    mean = user_data['weight'].mean()
                    std = user_data['weight'].std()
                    # Ensure std is never zero to avoid division by zero
                    if std < 0.1:  # If std is very small
                        std = 0.1  # Set a minimum standard deviation
                    stats[username] = (mean, std)
                else:
                    # Not enough data points for this user
                    stats[username] = default_stats[username]
                    
            return stats
        except Exception as e:
            print(f"Error calculating user stats: {e}")
            return default_stats
            
    def calculate_scores(self, weight):
        """
        Calculate score for each user based on the formula:
        score = (weight - mean_weight) / std_weight
        
        Lower absolute score means higher likelihood of being that user.
        
        Args:
            weight (float): New weight measurement
            
        Returns:
            dict: Dictionary with user names as keys and scores as values
        """
        stats = self.get_user_stats()
        scores = {}
        
        for user, (mean, std) in stats.items():
            # Calculate z-score (how many standard deviations from the mean)
            z_score = (weight - mean) / std
            # Use absolute value as score (lower is better)
            scores[user] = abs(z_score)
            
        return scores
        
    def identify_user(self, weight):
        """
        Identify the most likely user for a given weight measurement.
        
        Args:
            weight (float): New weight measurement
            
        Returns:
            str: Name of the most likely user
        """
        scores = self.calculate_scores(weight)
        
        if not scores:
            print(f"No user profiles found. Using default user.")
            return config.DEFAULT_USER
            
        # Find user with lowest score (closest to their typical weight distribution)
        most_likely_user = min(scores.items(), key=lambda x: x[1])[0]
        
        print(f"Weight: {weight}kg - Identified as user '{most_likely_user}' (scores: {scores})")
        return most_likely_user