#!/usr/bin/env python3
import argparse
import os

def update_config_file(config_path, username):
    """Update the DEFAULT_USER in the config file"""
    if not os.path.exists(config_path):
        print(f"Error: Config file not found at {config_path}")
        return False
        
    with open(config_path, 'r') as file:
        config_content = file.readlines()
    
    # Find and replace the DEFAULT_USER line
    default_user_updated = False
    for i, line in enumerate(config_content):
        if line.strip().startswith('DEFAULT_USER'):
            config_content[i] = f'DEFAULT_USER = "{username}"  # Default name (fallback)\n'
            default_user_updated = True
            break
    
    # If DEFAULT_USER not found, add it to the file
    if not default_user_updated:
        config_content.append(f'DEFAULT_USER = "{username}"  # Default name (fallback)\n')
    
    with open(config_path, 'w') as file:
        file.writelines(config_content)
    
    print(f"Successfully updated DEFAULT_USER to '{username}' in {config_path}")
    return True

def main():
    parser = argparse.ArgumentParser(description='Update the DEFAULT_USER in the smart scale config file')
    parser.add_argument('--config', default='smart_scale/config.py', help='Path to config.py file')
    parser.add_argument('--username', default='lukasz', help='Username to set as default')
    
    args = parser.parse_args()
    
    # Get absolute path to config file if it's not already absolute
    config_path = args.config if os.path.isabs(args.config) else os.path.abspath(args.config)
    
    update_config_file(config_path, args.username)

if __name__ == '__main__':
    main()