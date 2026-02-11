#!/usr/bin/env python3
import argparse
import os
import sys
import json
from tabulate import tabulate
from smart_scale.user_manager import UserManager

# Get the directory of the script
script_dir = os.path.dirname(os.path.abspath(__file__))
# The script is already in the project root directory
project_root = script_dir
# Add the project root to the Python path
sys.path.insert(0, project_root)

def list_users(user_manager):
    """List all users and their details in a table format"""
    users = user_manager.get_all_users()
    if not users:
        print("No users found. Use 'add' command to create a new user.")
        return
        
    # Prepare data for tabulate
    headers = ["Username", "Display Name", "Height (cm)", "Birthdate", "Age", "Sex"]
    rows = []
    
    for u in users:
        # Handle both old format (with age) and new format (with birthdate)
        birthdate = u.get("birthdate", "N/A")
        
        # Calculate current age if birthdate exists
        if birthdate != "N/A":
            age = user_manager.calculate_age(birthdate)
        else:
            age = u.get("age", "N/A")
            
        rows.append([
            u["username"], 
            u["display_name"], 
            u["height"], 
            birthdate,
            age,
            u["sex"]
        ])
    
    print("\nUser Profiles:")
    print(tabulate(rows, headers=headers, tablefmt="fancy_grid"))
    print(f"\nTotal users: {len(users)}")

def add_user(user_manager, args):
    """Add a new user with validation"""
    try:
        success = user_manager.add_user(
            args.username,
            args.display_name,
            args.height,
            args.birthdate,
            args.sex
        )
        
        if success:
            age = user_manager.calculate_age(args.birthdate)
            print(f"User '{args.username}' added successfully!")
            print(f"Current calculated age: {age} years")
            return True
        else:
            print("Failed to add user. See errors above.")
            return False
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

def update_user(user_manager, args):
    """Update an existing user"""
    try:
        success = user_manager.update_user(
            args.username,
            args.display_name,
            args.height,
            args.birthdate,
            args.sex
        )
        
        if success:
            print(f"User '{args.username}' updated successfully!")
            if args.birthdate:
                age = user_manager.calculate_age(args.birthdate)
                print(f"Current calculated age: {age} years")
            return True
        else:
            print("Failed to update user. See errors above.")
            return False
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

def delete_user(user_manager, args):
    """Delete a user after confirmation"""
    user = user_manager.get_user(args.username)
    if not user:
        print(f"User '{args.username}' not found.")
        return False
        
    if not args.force:
        confirm = input(f"Are you sure you want to delete user '{args.username}'? (y/N): ")
        if not confirm.lower().startswith('y'):
            print("Operation cancelled.")
            return False
    
    success = user_manager.delete_user(args.username)
    if success:
        print(f"User '{args.username}' deleted successfully!")
        return True
    else:
        print("Failed to delete user. See errors above.")
        return False

def show_user(user_manager, args):
    """Show details of a specific user"""
    user = user_manager.get_user(args.username)
    if not user:
        print(f"User '{args.username}' not found.")
        return False
    
    # Handle both old format (with age) and new format (with birthdate)
    birthdate = user.get("birthdate", "N/A")
    
    # Calculate current age if birthdate exists
    if birthdate != "N/A":
        age = user_manager.calculate_age(birthdate)
        age_source = "(calculated from birthdate)"
    else:
        age = user.get("age", "N/A")
        age_source = "(stored value)"
        
    print("\nUser Profile:")
    print(f"Username:     {user['username']}")
    print(f"Display Name: {user['display_name']}")
    print(f"Height:       {user['height']} cm")
    
    if birthdate != "N/A":
        print(f"Birthdate:    {birthdate}")
    
    print(f"Age:          {age} years {age_source}")
    print(f"Sex:          {user['sex']}")
    return True

def export_users(user_manager, args):
    """Export users to a specified JSON file"""
    try:
        with open(args.file, 'w') as f:
            json.dump(user_manager.profiles, f, indent=2)
        print(f"Users exported successfully to {args.file}")
        return True
    except Exception as e:
        print(f"Error exporting users: {str(e)}")
        return False

def import_users(user_manager, args):
    """Import users from a specified JSON file"""
    try:
        with open(args.file, 'r') as f:
            profiles = json.load(f)
            
        if "users" not in profiles:
            print("Error: Invalid profiles file format. Must contain a 'users' key.")
            return False
            
        # Validate each user profile
        for user in profiles["users"]:
            username = user.get("username", "unknown")
            
            # Check for either birthdate or age
            if "birthdate" not in user and "age" not in user:
                print(f"Error: User profile '{username}' missing both 'birthdate' and 'age' fields")
                return False
                
            # Check other required fields
            required_fields = ["username", "display_name", "height", "sex"]
            for field in required_fields:
                if field not in user:
                    print(f"Error: User profile '{username}' missing required field '{field}'")
                    return False
        
        # Replace existing profiles and save
        user_manager.profiles = profiles
        success = user_manager.save()
        
        if success:
            print(f"Imported {len(profiles['users'])} user profiles successfully!")
            return True
        else:
            print("Failed to save imported profiles.")
            return False
    except json.JSONDecodeError:
        print(f"Error: {args.file} is not a valid JSON file")
        return False
    except Exception as e:
        print(f"Error importing users: {str(e)}")
        return False

def main():
    # Define the default profiles file path relative to the project root
    profiles_file = os.path.join(project_root, "smart_scale", "users.json")
    user_manager = UserManager(profiles_file)
    
    # Create the argument parser
    parser = argparse.ArgumentParser(description='Smart Scale User Manager')
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List all users')
    
    # Add command
    add_parser = subparsers.add_parser('add', help='Add a new user')
    add_parser.add_argument('username', help='Username (unique identifier)')
    add_parser.add_argument('display_name', help='Display name')
    add_parser.add_argument('height', type=int, help='Height in cm')
    add_parser.add_argument('birthdate', help='Birthdate in YYYY-MM-DD format')
    add_parser.add_argument('sex', choices=['male', 'female'], help='Sex (male/female)')
    
    # Update command
    update_parser = subparsers.add_parser('update', help='Update an existing user')
    update_parser.add_argument('username', help='Username of user to update')
    update_parser.add_argument('--display-name', help='New display name')
    update_parser.add_argument('--height', type=int, help='New height in cm')
    update_parser.add_argument('--birthdate', help='New birthdate in YYYY-MM-DD format')
    update_parser.add_argument('--sex', choices=['male', 'female'], help='New sex (male/female)')
    
    # Delete command
    delete_parser = subparsers.add_parser('delete', help='Delete a user')
    delete_parser.add_argument('username', help='Username of user to delete')
    delete_parser.add_argument('-f', '--force', action='store_true', help='Delete without confirmation')
    
    # Show command
    show_parser = subparsers.add_parser('show', help='Show user details')
    show_parser.add_argument('username', help='Username of user to show')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export users to a file')
    export_parser.add_argument('file', help='File to export to')
    
    # Import command
    import_parser = subparsers.add_parser('import', help='Import users from a file')
    import_parser.add_argument('file', help='File to import from')
    
    # Parse the arguments
    args = parser.parse_args()
    
    # Execute the appropriate command
    if args.command == 'list' or args.command is None:
        list_users(user_manager)
    elif args.command == 'add':
        add_user(user_manager, args)
    elif args.command == 'update':
        update_user(user_manager, args)
    elif args.command == 'delete':
        delete_user(user_manager, args)
    elif args.command == 'show':
        show_user(user_manager, args)
    elif args.command == 'export':
        export_users(user_manager, args)
    elif args.command == 'import':
        import_users(user_manager, args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()