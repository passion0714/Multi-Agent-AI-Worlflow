"""
Call Settings Configuration Module

This module contains configuration settings for call attempts and scheduling.
"""
import os
import json
import logging

# Call attempt configuration
# This defines how many call attempts should be made per day and minimum intervals between calls

# Progressive call attempt schedule: 5, 4, 2, 2, 2 attempts per day
CALL_ATTEMPT_SETTINGS = {
    1: {  # Day 1: 5 attempts
        "max_attempts": 5,
        "min_interval_minutes": 45  # 45 minutes between calls
    },
    2: {  # Day 2: 4 attempts
        "max_attempts": 4,
        "min_interval_minutes": 60  # 1 hour between calls
    },
    3: {  # Day 3: 2 attempts
        "max_attempts": 2,
        "min_interval_minutes": 120  # 2 hours between calls
    },
    4: {  # Day 4: 2 attempts
        "max_attempts": 2,
        "min_interval_minutes": 120  # 2 hours between calls
    },
    5: {  # Day 5: 2 attempts
        "max_attempts": 2,
        "min_interval_minutes": 120  # 2 hours between calls
    }
}

# Maximum number of days to keep attempting calls
MAX_CALL_DAYS = 5

# Maximum total attempts across all days (safety limit)
MAX_TOTAL_ATTEMPTS = 15  # 5+4+2+2+2 = 15 total attempts

# Rate limiting for system processing (calls per minute)
SYSTEM_RATE_LIMIT = 10  # 10 calls per minute maximum

# Time restrictions (hours in 24-hour format)
ALLOWED_CALL_HOURS = {
    "start": 6,   # 6 AM local time (extended for testing)
    "end": 23     # 11 PM local time (extended for testing)
}

# Days of week allowed for calling (0=Monday, 6=Sunday)
ALLOWED_CALL_DAYS = [0, 1, 2, 3, 4, 5, 6]  # All days (extended for testing)

def get_call_settings_summary():
    """Get a summary of call settings for debugging"""
    total_attempts = sum(day_config["max_attempts"] for day_config in CALL_ATTEMPT_SETTINGS.values())
    
    return {
        "schedule": CALL_ATTEMPT_SETTINGS,
        "max_days": MAX_CALL_DAYS,
        "total_attempts_possible": total_attempts,
        "rate_limit_per_minute": SYSTEM_RATE_LIMIT,
        "call_hours": f"{ALLOWED_CALL_HOURS['start']:02d}:00 - {ALLOWED_CALL_HOURS['end']:02d}:59",
        "allowed_days": len(ALLOWED_CALL_DAYS)
    }

def validate_call_settings():
    """Validate call settings configuration"""
    errors = []
    
    # Validate day settings
    for day, settings in CALL_ATTEMPT_SETTINGS.items():
        if not isinstance(settings.get("max_attempts"), int) or settings["max_attempts"] < 0:
            errors.append(f"Day {day}: Invalid max_attempts")
        if not isinstance(settings.get("min_interval_minutes"), int) or settings["min_interval_minutes"] < 0:
            errors.append(f"Day {day}: Invalid min_interval_minutes")
    
    # Validate max days
    if MAX_CALL_DAYS != max(CALL_ATTEMPT_SETTINGS.keys()):
        errors.append("MAX_CALL_DAYS doesn't match highest day in CALL_ATTEMPT_SETTINGS")
    
    # Validate total attempts
    calculated_total = sum(day_config["max_attempts"] for day_config in CALL_ATTEMPT_SETTINGS.values())
    if MAX_TOTAL_ATTEMPTS != calculated_total:
        errors.append(f"MAX_TOTAL_ATTEMPTS ({MAX_TOTAL_ATTEMPTS}) doesn't match calculated total ({calculated_total})")
    
    return errors

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