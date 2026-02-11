import json
import os
import logging
import datetime

class UserManager:
    """
    Manages user profiles for the smart scale application.
    Handles loading, saving, adding, editing, and retrieving user data.
    """
    
    def __init__(self, profiles_file):
        """
        Initialize the UserManager with a JSON file for storing user profiles
        
        Args:
            profiles_file (str): Path to the JSON file for storing user profiles
        """
        self.profiles_file = profiles_file
        self.profiles = self._load_profiles()
        
    def _load_profiles(self):
        """
        Load user profiles from the JSON file.
        If the file doesn't exist or has errors, returns an empty user list.
        
        Returns:
            dict: Dictionary containing user profiles
        """
        if not os.path.exists(self.profiles_file):
            # Create default profiles structure
            default_profiles = {
                "users": []
            }
            self._save_profiles(default_profiles)
            return default_profiles
            
        try:
            with open(self.profiles_file, 'r') as f:
                profiles = json.load(f)
            return profiles
        except (json.JSONDecodeError, IOError) as e:
            logging.error(f"Error loading profiles: {e}")
            # Return empty profiles structure on error
            return {"users": []}

    def reload(self):
        """Reload profiles from file."""
        self.profiles = self._load_profiles()
    
    def _save_profiles(self, profiles=None):
        """
        Save user profiles to the JSON file.
        
        Args:
            profiles (dict): Dictionary of profiles to save. If None, uses self.profiles.
        
        Returns:
            bool: True if successful, False otherwise
        """
        if profiles is None:
            profiles = self.profiles
            
        try:
            with open(self.profiles_file, 'w') as f:
                json.dump(profiles, f, indent=2)
            return True
        except IOError as e:
            logging.error(f"Error saving profiles: {e}")
            return False
    
    def save(self):
        """
        Public method to save current profiles to file
        
        Returns:
            bool: True if successful, False otherwise
        """
        return self._save_profiles()
    
    def get_all_users(self):
        """
        Get a list of all user profiles
        
        Returns:
            list: List of user profile dictionaries
        """
        return self.profiles.get("users", [])
    
    def get_user(self, username):
        """
        Get a specific user profile by username
        
        Args:
            username (str): The username to look for
            
        Returns:
            dict: User profile, or None if not found
        """
        for user in self.profiles.get("users", []):
            if user.get("username") == username:
                # If it's an old format profile with age instead of birthdate
                if "age" in user and "birthdate" not in user:
                    # Add a warning in logs but still return the profile
                    logging.warning(f"User '{username}' has old format profile with age instead of birthdate")
                return user
        return None
        
    def get_user_with_age(self, username):
        """
        Get a specific user profile by username and calculate current age
        
        Args:
            username (str): The username to look for
            
        Returns:
            dict: User profile with calculated age, or None if not found
        """
        user = self.get_user(username)
        if not user:
            return None
        
        # Make a copy of the user profile to avoid modifying the original
        user_with_age = dict(user)
        
        # If user has birthdate, calculate current age
        if "birthdate" in user:
            user_with_age["age"] = self.calculate_age(user["birthdate"])
        
        return user_with_age
    
    def get_usernames(self):
        """
        Get a list of all usernames
        
        Returns:
            list: List of usernames
        """
        return [user.get("username") for user in self.profiles.get("users", [])]
    
    def calculate_age(self, birthdate):
        """
        Calculate age from birthdate
        
        Args:
            birthdate (str): Birthdate in YYYY-MM-DD format
            
        Returns:
            int: Age in years
        """
        try:
            # Parse the birthdate string to a datetime object
            birth_date = datetime.datetime.strptime(birthdate, '%Y-%m-%d').date()
            
            # Get today's date
            today = datetime.date.today()
            
            # Calculate age
            age = today.year - birth_date.year
            
            # Adjust age if birthday hasn't occurred yet this year
            if (today.month, today.day) < (birth_date.month, birth_date.day):
                age -= 1
                
            return max(0, age)  # Ensure age is not negative
        except ValueError as e:
            logging.error(f"Error calculating age: {e}")
            return 0
    
    def add_user(self, username, display_name, height, birthdate, sex):
        """
        Add a new user profile
        
        Args:
            username (str): Unique username (used for identification)
            display_name (str): Display name for the user
            height (int): Height in cm
            birthdate (str): Birthdate in YYYY-MM-DD format
            sex (str): "male" or "female"
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Validate inputs
        if not username or not display_name:
            logging.error("Username and display name are required")
            return False
            
        if self.get_user(username):
            logging.error(f"User '{username}' already exists")
            return False
            
        try:
            height = int(height)
            sex = sex.lower()
            
            if height <= 0 or height > 250:
                logging.error("Height must be between 1 and 250 cm")
                return False
                
            # Validate birthdate format and calculate age
            try:
                datetime.datetime.strptime(birthdate, '%Y-%m-%d')
            except ValueError:
                logging.error("Birthdate must be in YYYY-MM-DD format")
                return False
            
            # Calculate current age
            age = self.calculate_age(birthdate)
            if age > 120:
                logging.error("Birthdate results in an age over 120 years")
                return False
                
            if sex not in ["male", "female"]:
                logging.error("Sex must be 'male' or 'female'")
                return False
                
        except ValueError:
            logging.error("Height must be a valid number")
            return False
        
        # Create new user profile
        new_user = {
            "username": username,
            "display_name": display_name,
            "height": height,
            "birthdate": birthdate,
            "sex": sex
        }
        
        # Add to profiles
        self.profiles["users"].append(new_user)
        return self.save()
    
    def update_user(self, username, display_name=None, height=None, birthdate=None, sex=None):
        """
        Update an existing user profile
        
        Args:
            username (str): Username of user to update
            display_name (str, optional): New display name
            height (int, optional): New height in cm
            birthdate (str, optional): New birthdate in YYYY-MM-DD format
            sex (str, optional): New sex ("male" or "female")
            
        Returns:
            bool: True if successful, False otherwise
        """
        user = self.get_user(username)
        if not user:
            logging.error(f"User '{username}' not found")
            return False
        
        # Update fields if provided
        if display_name:
            user["display_name"] = display_name
            
        if height is not None:
            try:
                height = int(height)
                if height <= 0 or height > 250:
                    logging.error("Height must be between 1 and 250 cm")
                    return False
                user["height"] = height
            except ValueError:
                logging.error("Height must be a valid number")
                return False
                
        if birthdate is not None:
            try:
                # Validate birthdate format
                datetime.datetime.strptime(birthdate, '%Y-%m-%d')
                
                # Calculate age to check if it's reasonable
                age = self.calculate_age(birthdate)
                if age > 120:
                    logging.error("Birthdate results in an age over 120 years")
                    return False
                
                user["birthdate"] = birthdate
            except ValueError:
                logging.error("Birthdate must be in YYYY-MM-DD format")
                return False
                
        if sex is not None:
            sex = sex.lower()
            if sex not in ["male", "female"]:
                logging.error("Sex must be 'male' or 'female'")
                return False
            user["sex"] = sex
            
        return self.save()
    
    def delete_user(self, username):
        """
        Delete a user profile
        
        Args:
            username (str): Username of user to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        initial_count = len(self.profiles.get("users", []))
        self.profiles["users"] = [u for u in self.profiles.get("users", []) if u.get("username") != username]
        
        # Check if any user was removed
        if len(self.profiles.get("users", [])) < initial_count:
            return self.save()
        else:
            logging.error(f"User '{username}' not found")
            return False