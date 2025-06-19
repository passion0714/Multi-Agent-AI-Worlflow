import os
import httpx
from typing import Dict, Any, Optional
from loguru import logger
import re
from datetime import datetime
from dateutil import parser
import pytz

class VAPIService:
    """Service for interacting with VAPI for voice calls"""
    
    def __init__(self):
        self.api_key = os.getenv("VAPI_API_KEY")
        self.phone_number = os.getenv("VAPI_PHONE_NUMBER")
        self.phone_number_id = os.getenv("VAPI_PHONE_NUMBER_ID")
        self.assistant_id = os.getenv("VAPI_ASSISTANT_ID", "08301bb7-72c5-466c-a0ba-ca54d429c93e")  # Zoe from Eluminus
        self.base_url = "https://api.vapi.ai"
        
        # Call time settings for TCPA compliance
        self.min_call_hour = 9  # 9:00 AM
        self.max_call_hour = 18  # 6:00 PM (18:00)
        
        # US time zones mapping
        self.us_timezones = {
            "Eastern": "US/Eastern",
            "Central": "US/Central", 
            "Mountain": "US/Mountain",
            "Pacific": "US/Pacific",
            "Alaska": "US/Alaska",
            "Hawaii": "US/Hawaii"
        }
        
        # Area code to time zone mapping (simplified)
        self.area_code_to_timezone = {
            "Eastern": [
                "201", "202", "203", "207", "212", "215", "216", "217", "218", "219",
                "223", "224", "228", "229", "231", "234", "239", "240", "248", "251",
                "252", "267", "269", "276", "301", "302", "304", "305", "313", "317", 
                "321", "330", "336", "339", "351", "352", "401", "404", "410", "412",
                "413", "419", "423", "434", "440", "443", "470", "475", "478", "484",
                "502", "508", "513", "517", "518", "540", "551", "561", "567", "571",
                "585", "586", "603", "607", "609", "610", "614", "616", "617", "631",
                "646", "678", "704", "716", "717", "718", "724", "727", "732", "734",
                "757", "770", "772", "781", "786", "810", "813", "814", "828", "843",
                "845", "856", "859", "863", "864", "904", "908", "914", "919", "937",
                "941", "954", "973", "978", "980"
            ],
            "Central": [
                "205", "210", "214", "225", "254", "256", "262", "281", "309", "312", 
                "314", "316", "318", "319", "320", "331", "334", "337", "361", "402",
                "405", "409", "414", "417", "430", "432", "469", "479", "501", "504",
                "507", "512", "515", "563", "573", "574", "601", "605", "608", "612",
                "615", "618", "620", "630", "636", "641", "651", "660", "662", "682",
                "708", "712", "713", "715", "731", "763", "769", "773", "785", "815",
                "816", "817", "830", "832", "847", "870", "901", "903", "913", "915",
                "918", "920", "925", "936", "940", "952", "956", "972", "979", "985"
            ],
            "Mountain": [
                "303", "307", "385", "406", "435", "505", "575", "602", "623", "719",
                "720", "801", "907", "915", "928", "970"
            ],
            "Pacific": [
                "209", "213", "279", "310", "323", "408", "415", "424", "442", "503",
                "510", "530", "541", "559", "562", "619", "626", "628", "650", "657",
                "661", "669", "702", "707", "714", "725", "747", "760", "775", "805",
                "818", "831", "858", "909", "916", "925", "949", "951", "971", "206",
                "253", "360", "406", "425", "509", "509", "530"
            ],
            "Alaska": ["907"],
            "Hawaii": ["808"]
        }
        
        # Validate required configuration
        if not self.api_key:
            raise ValueError("VAPI_API_KEY environment variable is required")
        if not self.phone_number_id:
            logger.warning("VAPI_PHONE_NUMBER_ID not configured - calls will fail")
        if not self.assistant_id:
            logger.warning("VAPI_ASSISTANT_ID not configured - calls will fail")
    
    def _format_phone_number(self, phone: str) -> str:
        """Format phone number to E.164 format"""
        if not phone:
            logger.error("Phone number is empty or None")
            return ""
            
        # Log the original phone number for debugging
        logger.info(f"Formatting phone number: '{phone}'")
            
        # Remove all non-digit characters
        digits_only = re.sub(r'\D', '', phone)
        logger.info(f"Digits only: '{digits_only}'")
        
        # Always ensure US numbers have a "1" prefix
        if len(digits_only) == 10:
            # 10-digit US number without country code, add +1
            formatted = f"+1{digits_only}"
        elif len(digits_only) == 11:
            if digits_only.startswith('1'):
                # 11-digit with "1" prefix, add "+"
                formatted = f"+{digits_only}"
            else:
                # 11-digit without "1" prefix, add "+1"
                formatted = f"+1{digits_only}"
        elif phone.startswith('+'):
            # Already has "+" prefix, keep as is
            formatted = phone
        else:
            # For any other format, ensure it has "+1" prefix
            formatted = f"+1{digits_only}"
            
        logger.info(f"Formatted phone number: '{formatted}'")
        return formatted
    
    def _calculate_duration(self, started_at: str, ended_at: str) -> Optional[int]:
        """Calculate call duration in seconds from timestamp strings"""
        try:
            if not started_at or not ended_at:
                return None
            
            # Parse ISO timestamp strings to datetime objects
            start_time = parser.parse(started_at)
            end_time = parser.parse(ended_at)
            
            # Calculate duration in seconds
            duration = (end_time - start_time).total_seconds()
            return int(duration)
        except Exception as e:
            logger.warning(f"Could not calculate call duration: {str(e)}")
            return None
    
    async def make_outbound_call(self, call_data: Dict[str, Any]) -> Dict[str, Any]:
        """Make an outbound call via VAPI"""
        try:
            # Validate configuration
            if not self.phone_number_id:
                return {
                    "success": False,
                    "error": "VAPI_PHONE_NUMBER_ID not configured. Please set this in your .env file."
                }
            
            if not self.assistant_id:
                return {
                    "success": False,
                    "error": "VAPI_ASSISTANT_ID not configured. Please set this in your .env file."
                }
                
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Check if call_data already has customer.number set
            if "customer" in call_data and "number" in call_data["customer"]:
                customer_number = call_data["customer"]["number"]
                logger.info(f"Using provided customer.number: {customer_number}")
            elif "phone_number" in call_data:
                # Format phone number to E.164
                phone_number = call_data["phone_number"]
                customer_number = self._format_phone_number(phone_number)
                logger.info(f"Formatted phone_number {phone_number} to {customer_number}")
            else:
                error_msg = f"Missing phone number in call_data: {call_data}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg
                }
            
            if not customer_number:
                error_msg = f"Failed to format phone number"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg
                }
            
            # Prepare call payload
            payload = {
                "phoneNumberId": self.phone_number_id,
                "assistantId": self.assistant_id,
                "customer": {
                    "number": customer_number
                },
                "assistantOverrides": {
                    "variableValues": {
                        "leadData": call_data["lead_data"]
                    }
                }
            }
            
            # Log the full payload for debugging
            logger.info(f"VAPI call payload: {payload}")
            logger.info(f"Making VAPI call to {customer_number} with assistant {self.assistant_id}")
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/call",
                    headers=headers,
                    json=payload,
                    timeout=30.0
                )
                
                if response.status_code == 201:
                    call_response = response.json()
                    logger.info(f"Successfully initiated call: {call_response.get('id')}")
                    return {
                        "success": True,
                        "call_id": call_response.get("id"),
                        "status": call_response.get("status"),
                        "data": call_response
                    }
                else:
                    error_msg = f"VAPI call failed: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    return {
                        "success": False,
                        "error": error_msg
                    }
                    
        except Exception as e:
            error_msg = f"Error making VAPI call: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
    
    async def get_call_status(self, call_id: str) -> Dict[str, Any]:
        """Get the status of a VAPI call"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/call/{call_id}",
                    headers=headers,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    call_data = response.json()
                    
                    # Calculate duration properly
                    duration = None
                    started_at = call_data.get("startedAt")
                    ended_at = call_data.get("endedAt")
                    
                    if started_at and ended_at:
                        duration = self._calculate_duration(started_at, ended_at)
                    
                    return {
                        "success": True,
                        "status": call_data.get("status"),
                        "duration": duration,
                        "recording_url": call_data.get("recordingUrl"),
                        "transcript": call_data.get("transcript"),
                        "analysis": call_data.get("analysis", {}),
                        "data": call_data
                    }
                else:
                    logger.error(f"Failed to get call status: {response.status_code} - {response.text}")
                    return {
                        "success": False,
                        "error": f"Failed to get call status: {response.status_code}"
                    }
                    
        except Exception as e:
            logger.error(f"Error getting call status: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_call_recording(self, call_id: str) -> Optional[str]:
        """Get the recording URL for a completed call"""
        try:
            call_status = await self.get_call_status(call_id)
            if call_status.get("success"):
                return call_status.get("recording_url")
            return None
        except Exception as e:
            logger.error(f"Error getting call recording: {str(e)}")
            return None
    
    def _generate_first_message(self, lead_data: Dict[str, Any]) -> str:
        """Generate the first message for Zoe based on lead data"""
        first_name = lead_data.get("first_name", "")
        
        # Customize the first message based on lead data
        message = f"""Hi {first_name}, this is Zoe from Eluminus. I'm calling to confirm some information we have on file for you and see if you're still interested in our services. 

I have your information as:
- Name: {lead_data.get('first_name', '')} {lead_data.get('last_name', '')}
- Email: {lead_data.get('email', '')}
- Phone: {lead_data.get('phone', '')}
- Address: {lead_data.get('address', '')}, {lead_data.get('city', '')}, {lead_data.get('state', '')} {lead_data.get('zip_code', '')}

Is this information still correct? And are you still interested in learning more about our services?"""
        
        return message
    
    async def update_assistant_instructions(self, instructions: str) -> bool:
        """Update the assistant instructions for better lead qualification"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": {
                    "provider": "openai",
                    "model": "gpt-4",
                    "messages": [
                        {
                            "role": "system",
                            "content": instructions
                        }
                    ]
                }
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    f"{self.base_url}/assistant/{self.assistant_id}",
                    headers=headers,
                    json=payload,
                    timeout=30.0
                )
                
                return response.status_code == 200
                
        except Exception as e:
            logger.error(f"Error updating assistant instructions: {str(e)}")
            return False

    def get_default_assistant_instructions(self) -> str:
        """Get default instructions for the Zoe assistant"""
        return """You are Zoe, a professional and friendly AI assistant working for Eluminus - Merge. Your role is to make outbound calls to leads to:

1. Confirm their contact information (email, phone, address)
2. Verify their interest in our services
3. Collect their area of interest
4. Obtain TCPA consent for future communications

IMPORTANT GUIDELINES:
- Be professional, friendly, and respectful
- Keep the call focused and efficient (aim for 2-3 minutes)
- Always ask for TCPA consent: "Do you consent to receive future communications from us regarding our services?"
- Confirm each piece of information clearly
- If they're not interested, politely thank them and end the call
- If they seem confused or don't remember inquiring, briefly explain they showed interest in our services online

REQUIRED INFORMATION TO COLLECT:
- Confirmed email address
- Confirmed phone number  
- Confirmed mailing address
- Area of interest (what services they're interested in)
- TCPA consent (yes/no)
- Overall interest level (interested/not interested)

CALL FLOW:
1. Introduce yourself and company
2. Confirm their identity
3. Verify contact information
4. Ask about their area of interest
5. Request TCPA consent
6. Thank them and end the call

Remember to be natural and conversational while gathering this information efficiently."""

    async def is_valid_call_time(self, phone_number: str) -> bool:
        """
        Check if the current time is valid for making outbound calls to the given phone number
        based on telemarketing regulations.
        
        Returns:
            bool: True if it's a valid time to call, False otherwise
        """
        try:
            # Default to True in case we can't determine time zone
            # This ensures calls won't be blocked due to technical issues
            if not phone_number:
                logger.warning("Empty phone number provided to is_valid_call_time")
                return False
                
            return self._is_valid_call_time_for_datetime(phone_number, datetime.now())
        except Exception as e:
            logger.error(f"Error in is_valid_call_time: {e}")
            return True  # Default to allowing calls if there's an error
    
    def _is_valid_call_time_for_datetime(self, phone_number: str, check_time: datetime) -> bool:
        """
        Check if a specific datetime is valid for making outbound calls to the given phone number.
        
        Args:
            phone_number: The phone number to call
            check_time: The UTC datetime to check
            
        Returns:
            bool: True if it's a valid time to call, False otherwise
        """
        try:
            # Only call Monday-Friday (not on weekends)
            if check_time.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
                logger.info(f"Call to {phone_number} rejected: weekend calling not allowed")
                return False
                
            # Get the time zone for the phone number based on area code
            phone_tz = self._get_timezone_for_phone(phone_number)
            if not phone_tz:
                logger.warning(f"Could not determine time zone for {phone_number}, defaulting to Eastern")
                phone_tz = pytz.timezone("US/Eastern")
                
            # Convert current time to the recipient's time zone
            recipient_time = check_time.astimezone(phone_tz)
            recipient_hour = recipient_time.hour
            
            # Check if the time is between allowed hours (9 AM - 6 PM)
            if recipient_hour < self.min_call_hour or recipient_hour >= self.max_call_hour:
                logger.info(f"Call to {phone_number} rejected: outside allowed hours (time: {recipient_time.strftime('%H:%M')} {phone_tz.zone})")
                return False
                
            logger.info(f"Call time valid for {phone_number}: {recipient_time.strftime('%H:%M')} {phone_tz.zone}")
            return True
            
        except Exception as e:
            logger.error(f"Error validating call time for {phone_number}: {e}")
            return True  # Default to allowing calls if there's an error
            
    def _get_timezone_for_phone(self, phone_number: str) -> Optional[pytz.timezone]:
        """
        Determine the timezone for a US phone number based on area code.
        
        Args:
            phone_number: The phone number to check
            
        Returns:
            Optional[pytz.timezone]: The timezone for the phone number, or None if it can't be determined
        """
        try:
            # Clean the phone number
            cleaned = re.sub(r'[^0-9]', '', phone_number)
            
            # Extract area code
            if len(cleaned) >= 10:
                if cleaned.startswith('1') and len(cleaned) >= 11:
                    area_code = cleaned[1:4]
                else:
                    area_code = cleaned[0:3]
                    
                logger.info(f"Extracted area code {area_code} from {phone_number}")
                
                # Look up timezone based on area code first 3 digits
                for zone_name, codes in self.area_code_to_timezone.items():
                    if area_code in codes:
                        tz_id = self.us_timezones.get(zone_name)
                        if tz_id:
                            return pytz.timezone(tz_id)
                            
                # Default to Eastern if no match
                logger.warning(f"No timezone match for area code {area_code}, defaulting to Eastern")
                return pytz.timezone("US/Eastern")
            else:
                logger.warning(f"Phone number too short to extract area code: {phone_number}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting timezone for {phone_number}: {e}")
            return None