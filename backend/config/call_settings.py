"""
Call Settings Configuration Module

This module contains configuration settings for call attempts and scheduling.
"""
import os
import json
import logging

# Call attempt settings by day
CALL_ATTEMPT_SETTINGS = {
    # Day 1: 5 attempts
    1: {
        "max_attempts": 5,
        "min_interval_minutes": 60,  # Minimum time between attempts
    },
    # Day 2: 4 attempts
    2: {
        "max_attempts": 4,
        "min_interval_minutes": 90,  # Minimum time between attempts
    },
    # Day 3: 2 attempts
    3: {
        "max_attempts": 2,
        "min_interval_minutes": 120,  # Minimum time between attempts
    },
    # Day 4: 2 attempts
    4: {
        "max_attempts": 2,
        "min_interval_minutes": 120,  # Minimum time between attempts
    },
    # Day 5: 2 attempts
    5: {
        "max_attempts": 2,
        "min_interval_minutes": 120,  # Minimum time between attempts
    },
    # Day 6 and beyond: No calls
    6: {
        "max_attempts": 0,
        "min_interval_minutes": 0,
    }
}

# Maximum days to attempt calls before giving up
MAX_CALL_DAYS = 5

# Maximum total attempts across all days
MAX_TOTAL_ATTEMPTS = 15

# Calling hours (24-hour format)
CALLING_HOURS = {
    "start_hour": 9,   # 9:00 AM
    "end_hour": 18,    # 6:00 PM
}

def load_custom_settings():
    """Load custom call settings if they exist"""
    try:
        # Get the directory of this file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        settings_path = os.path.join(current_dir, "custom_call_settings.json")
        
        if os.path.exists(settings_path):
            with open(settings_path, "r") as f:
                custom_settings = json.load(f)
                
                # Update the call attempts settings
                CALL_ATTEMPT_SETTINGS[1]["max_attempts"] = custom_settings.get("day1", 5)
                CALL_ATTEMPT_SETTINGS[2]["max_attempts"] = custom_settings.get("day2", 4)
                CALL_ATTEMPT_SETTINGS[3]["max_attempts"] = custom_settings.get("day3", 2)
                CALL_ATTEMPT_SETTINGS[4]["max_attempts"] = custom_settings.get("day4", 2)
                CALL_ATTEMPT_SETTINGS[5]["max_attempts"] = custom_settings.get("day5", 2)
                CALL_ATTEMPT_SETTINGS[6]["max_attempts"] = custom_settings.get("day6", 0)
                
                # Also update the MAX_CALL_DAYS and MAX_TOTAL_ATTEMPTS if they exist
                global MAX_CALL_DAYS, MAX_TOTAL_ATTEMPTS
                
                if "max_days" in custom_settings:
                    MAX_CALL_DAYS = custom_settings["max_days"]
                    
                if "max_total_attempts" in custom_settings:
                    MAX_TOTAL_ATTEMPTS = custom_settings["max_total_attempts"]
                    
                logging.info(f"Loaded custom call settings: {custom_settings}")
                return True
    except Exception as e:
        logging.error(f"Error loading custom call settings: {e}")
    
    return False

# Try to load custom settings on module import
load_custom_settings() 