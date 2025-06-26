#!/usr/bin/env python3
"""
Test Arizona Timezone Detection
This script tests if Arizona phone numbers are correctly identified and time validation works
"""
import asyncio
import sys
import os
from datetime import datetime

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.vapi_service import VAPIService

async def test_arizona_timezone():
    """Test Arizona timezone detection"""
    print("🌵 Testing Arizona Timezone Detection")
    print("=" * 40)
    
    # Initialize VAPI service
    vapi_service = VAPIService()
    
    # Arizona area codes and test phone numbers
    arizona_phones = [
        "4801234567",  # Phoenix area
        "5201234567",  # Tucson area  
        "6021234567",  # Phoenix area
        "6231234567",  # Phoenix area
        "9281234567",  # Flagstaff area
        "+14801234567", # With country code
        "16021234567",  # With 1 prefix
    ]
    
    print("🔍 Testing Arizona phone numbers:")
    
    for phone in arizona_phones:
        print(f"\n📱 Testing phone: {phone}")
        
        # Test phone number formatting
        formatted = vapi_service._format_phone_number(phone)
        print(f"   Formatted: {formatted}")
        
        # Test timezone detection and call time validation
        is_valid = await vapi_service.is_valid_call_time(phone)
        print(f"   Valid call time: {is_valid}")
        
        # Show current time in Arizona
        import pytz
        from datetime import timezone
        
        # Get area code
        phone_digits = ''.join(filter(str.isdigit, phone))
        if len(phone_digits) >= 10:
            area_code = phone_digits[-10:-7]
            print(f"   Area code: {area_code}")
            
            # Get Arizona time
            az_tz = pytz.timezone('US/Arizona')
            utc_now = datetime.now(timezone.utc)
            az_time = utc_now.astimezone(az_tz)
            print(f"   Current Arizona time: {az_time.strftime('%I:%M %p %Z (%z)')}")
            print(f"   Hour: {az_time.hour} (valid range: 8-20)")

    # Test non-Arizona numbers for comparison
    print("\n🔍 Testing non-Arizona phone numbers for comparison:")
    
    other_phones = [
        "2121234567",  # New York (Eastern)
        "3101234567",  # Los Angeles (Pacific)
        "3031234567",  # Denver (Mountain)
        "7131234567",  # Houston (Central)
    ]
    
    for phone in other_phones:
        print(f"\n📱 Testing phone: {phone}")
        is_valid = await vapi_service.is_valid_call_time(phone)
        print(f"   Valid call time: {is_valid}")

if __name__ == "__main__":
    print("🧪 Arizona Timezone Test")
    print("=" * 30)
    
    try:
        asyncio.run(test_arizona_timezone())
        print("\n✅ Test completed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc() 