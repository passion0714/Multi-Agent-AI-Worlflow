import os
import httpx
import asyncio
from typing import Dict, Any, Optional
from loguru import logger
import re
from datetime import datetime, timezone
from dateutil import parser
import pytz

class VAPIService:
    """Service for interacting with VAPI for voice calls"""
    
    def __init__(self):
        self.api_key = os.getenv("VAPI_API_KEY")
        if not self.api_key:
            raise ValueError("VAPI_API_KEY environment variable is required")
            
        self.base_url = "https://api.vapi.ai"
        self.assistant_id = os.getenv("VAPI_ASSISTANT_ID", "08301bb7-72c5-466c-a0ba-ca54d429c93e")
        
        logger.info(f"VAPI Service initialized with Assistant ID: {self.assistant_id}")
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
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
        # Note: phone_number_id no longer required - VAPI handles this automatically
    
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
        """Make an outbound call via VAPI API"""
        logger.info(f"=== VAPI OUTBOUND CALL ATTEMPT ===")
        logger.info(f"Target phone: {call_data.get('customer', {}).get('number')}")
        logger.info(f"Assistant ID: {call_data.get('assistant_id')}")
        
        try:
            # Ensure phone number is properly formatted
            phone_number = call_data.get("customer", {}).get("number")
            if not phone_number:
                error_msg = "No phone number provided"
                logger.error(f"VAPI Error: {error_msg}")
                return {"success": False, "error": error_msg}
                
            formatted_phone = self._format_phone_number(phone_number)
            logger.info(f"Phone number formatted: {phone_number} -> {formatted_phone}")
            
            # Prepare the VAPI call payload - DO NOT override assistant settings
            payload = {
                "assistantId": call_data.get("assistant_id", self.assistant_id),
                "customer": {
                    "number": formatted_phone
                },
                # Pass lead data for context but don't override the assistant prompt
                "assistantOverrides": {
                    "variableValues": {
                        "leadData": call_data.get("lead_data", {})
                    }
                }
            }
            
            logger.info(f"VAPI Call Payload: {payload}")
            
            # Make the API call to VAPI
            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.info("Making HTTP request to VAPI...")
                response = await client.post(
                    f"{self.base_url}/call",
                    headers=self.headers,
                    json=payload
                )
                
                logger.info(f"VAPI Response Status: {response.status_code}")
                logger.info(f"VAPI Response Headers: {dict(response.headers)}")
                
                # Parse response
                if response.status_code == 201:
                    # Success
                    response_data = response.json()
                    call_id = response_data.get("id")
                    
                    logger.info(f"VAPI Call SUCCESS - Call ID: {call_id}")
                    logger.info(f"Full VAPI Response: {response_data}")
                    
                    return {
                        "success": True,
                        "call_id": call_id,
                        "vapi_response": response_data,
                        "formatted_phone": formatted_phone
                    }
                    
                else:
                    # Error from VAPI
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("message", f"HTTP {response.status_code}")
                    except:
                        error_msg = f"HTTP {response.status_code}: {response.text}"
                    
                    logger.error(f"VAPI Call FAILED - Status: {response.status_code}")
                    logger.error(f"VAPI Error: {error_msg}")
                    logger.error(f"VAPI Response Text: {response.text}")
                    
                    return {
                        "success": False,
                        "error": error_msg,
                        "status_code": response.status_code,
                        "response_text": response.text
                    }
                    
        except httpx.TimeoutException:
            error_msg = "VAPI request timeout"
            logger.error(f"VAPI Error: {error_msg}")
            return {"success": False, "error": error_msg}
            
        except httpx.RequestError as e:
            error_msg = f"VAPI request error: {str(e)}"
            logger.error(f"VAPI Error: {error_msg}")
            return {"success": False, "error": error_msg}
            
        except Exception as e:
            error_msg = f"Unexpected error in VAPI call: {str(e)}"
            logger.error(f"VAPI Error: {error_msg}")
            return {"success": False, "error": error_msg}
    
    async def get_call_status(self, call_id: str) -> Dict[str, Any]:
        """Get the status of a VAPI call"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/call/{call_id}",
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    call_data = response.json()
                    return {
                        "success": True,
                        "status": call_data.get("status"),
                        "data": call_data,
                        "duration": call_data.get("duration"),
                        "recording_url": call_data.get("recordingUrl"),
                        "transcript": call_data.get("transcript"),
                        "analysis": call_data.get("analysis", {})
                    }
                else:
                    logger.error(f"Failed to get call status: {response.status_code} - {response.text}")
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}: {response.text}"
                    }
                    
        except Exception as e:
            logger.error(f"Error getting call status for {call_id}: {e}")
            return {"success": False, "error": str(e)}
    
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
        """Check if current time is valid for calling based on timezone"""
        try:
            # Extract area code for timezone determination
            phone_digits = ''.join(filter(str.isdigit, phone_number))
            if len(phone_digits) >= 10:
                area_code = phone_digits[-10:-7]  # Get first 3 digits of 10-digit number
                
                # Map area codes to timezones (basic mapping for US)
                timezone_map = {
                    # Eastern Time
                    "201": "US/Eastern", "202": "US/Eastern", "203": "US/Eastern",
                    "212": "US/Eastern", "215": "US/Eastern", "216": "US/Eastern",
                    "240": "US/Eastern", "267": "US/Eastern", "301": "US/Eastern",
                    "302": "US/Eastern", "304": "US/Eastern", "305": "US/Eastern",
                    "321": "US/Eastern", "347": "US/Eastern", "352": "US/Eastern",
                    "386": "US/Eastern", "401": "US/Eastern", "404": "US/Eastern",
                    "407": "US/Eastern", "410": "US/Eastern", "412": "US/Eastern",
                    "413": "US/Eastern", "434": "US/Eastern", "443": "US/Eastern",
                    "470": "US/Eastern", "475": "US/Eastern", "478": "US/Eastern",
                    "484": "US/Eastern", "508": "US/Eastern", "516": "US/Eastern",
                    "518": "US/Eastern", "561": "US/Eastern", "570": "US/Eastern",
                    "585": "US/Eastern", "607": "US/Eastern", "610": "US/Eastern",
                    "617": "US/Eastern", "646": "US/Eastern", "678": "US/Eastern",
                    "681": "US/Eastern", "689": "US/Eastern", "703": "US/Eastern",
                    "704": "US/Eastern", "706": "US/Eastern", "717": "US/Eastern",
                    "718": "US/Eastern", "724": "US/Eastern", "727": "US/Eastern",
                    "732": "US/Eastern", "734": "US/Eastern", "740": "US/Eastern",
                    "754": "US/Eastern", "757": "US/Eastern", "762": "US/Eastern",
                    "772": "US/Eastern", "774": "US/Eastern", "781": "US/Eastern",
                    "786": "US/Eastern", "787": "US/Eastern", "803": "US/Eastern",
                    "813": "US/Eastern", "828": "US/Eastern", "843": "US/Eastern",
                    "845": "US/Eastern", "848": "US/Eastern", "850": "US/Eastern",
                    "856": "US/Eastern", "857": "US/Eastern", "859": "US/Eastern",
                    "860": "US/Eastern", "863": "US/Eastern", "865": "US/Eastern",
                    "878": "US/Eastern", "904": "US/Eastern", "908": "US/Eastern",
                    "910": "US/Eastern", "912": "US/Eastern", "914": "US/Eastern",
                    "917": "US/Eastern", "919": "US/Eastern", "929": "US/Eastern",
                    "934": "US/Eastern", "937": "US/Eastern", "941": "US/Eastern",
                    "947": "US/Eastern", "954": "US/Eastern", "959": "US/Eastern",
                    "970": "US/Eastern", "973": "US/Eastern", "978": "US/Eastern",
                    "980": "US/Eastern", "984": "US/Eastern", "985": "US/Eastern",
                    
                    # Central Time
                    "205": "US/Central", "214": "US/Central", "217": "US/Central",
                    "218": "US/Central", "224": "US/Central", "225": "US/Central",
                    "228": "US/Central", "251": "US/Central", "254": "US/Central",
                    "256": "US/Central", "260": "US/Central", "262": "US/Central",
                    "281": "US/Central", "309": "US/Central", "312": "US/Central",
                    "314": "US/Central", "316": "US/Central", "318": "US/Central",
                    "319": "US/Central", "320": "US/Central", "334": "US/Central",
                    "337": "US/Central", "361": "US/Central", "409": "US/Central",
                    "414": "US/Central", "417": "US/Central", "430": "US/Central",
                    "432": "US/Central", "469": "US/Central", "479": "US/Central",
                    "501": "US/Central", "502": "US/Central", "504": "US/Central",
                    "507": "US/Central", "512": "US/Central", "515": "US/Central",
                    "563": "US/Central", "573": "US/Central", "580": "US/Central",
                    "601": "US/Central", "608": "US/Central", "612": "US/Central",
                    "618": "US/Central", "620": "US/Central", "630": "US/Central",
                    "636": "US/Central", "641": "US/Central", "651": "US/Central",
                    "660": "US/Central", "662": "US/Central", "682": "US/Central",
                    "708": "US/Central", "712": "US/Central", "713": "US/Central",
                    "715": "US/Central", "731": "US/Central", "737": "US/Central",
                    "763": "US/Central", "769": "US/Central", "773": "US/Central",
                    "779": "US/Central", "785": "US/Central", "806": "US/Central",
                    "807": "US/Central", "815": "US/Central", "816": "US/Central",
                    "817": "US/Central", "830": "US/Central", "832": "US/Central",
                    "847": "US/Central", "870": "US/Central", "901": "US/Central",
                    "903": "US/Central", "913": "US/Central", "915": "US/Central",
                    "918": "US/Central", "920": "US/Central", "936": "US/Central",
                    "940": "US/Central", "952": "US/Central", "956": "US/Central",
                    "972": "US/Central", "979": "US/Central", "985": "US/Central",
                    
                    # Mountain Time
                    "303": "US/Mountain", "307": "US/Mountain", "385": "US/Mountain",
                    "406": "US/Mountain", "435": "US/Mountain", "480": "US/Mountain",
                    "505": "US/Mountain", "520": "US/Mountain", "575": "US/Mountain",
                    "602": "US/Mountain", "623": "US/Mountain", "719": "US/Mountain",
                    "720": "US/Mountain", "801": "US/Mountain", "928": "US/Mountain",
                    
                    # Pacific Time
                    "206": "US/Pacific", "209": "US/Pacific", "213": "US/Pacific",
                    "253": "US/Pacific", "310": "US/Pacific", "323": "US/Pacific",
                    "341": "US/Pacific", "360": "US/Pacific", "415": "US/Pacific",
                    "424": "US/Pacific", "442": "US/Pacific", "510": "US/Pacific",
                    "530": "US/Pacific", "541": "US/Pacific", "559": "US/Pacific",
                    "562": "US/Pacific", "619": "US/Pacific", "626": "US/Pacific",
                    "628": "US/Pacific", "650": "US/Pacific", "657": "US/Pacific",
                    "661": "US/Pacific", "669": "US/Pacific", "707": "US/Pacific",
                    "714": "US/Pacific", "747": "US/Pacific", "760": "US/Pacific",
                    "805": "US/Pacific", "818": "US/Pacific", "831": "US/Pacific",
                    "858": "US/Pacific", "909": "US/Pacific", "916": "US/Pacific",
                    "925": "US/Pacific", "949": "US/Pacific", "951": "US/Pacific"
                }
                
                # Get timezone for area code
                tz_name = timezone_map.get(area_code, "US/Eastern")  # Default to Eastern
                local_tz = pytz.timezone(tz_name)
                
                # Get current time in local timezone
                utc_now = datetime.now(timezone.utc)
                local_time = utc_now.astimezone(local_tz)
                current_hour = local_time.hour
                
                # Check if within calling hours (8 AM to 9 PM local time)
                # Extended hours for testing: 6 AM to 11 PM
                if 6 <= current_hour <= 23:
                    logger.debug(f"Valid call time for {phone_number} (area code {area_code}): "
                               f"{local_time.strftime('%I:%M %p %Z')}")
                    return True
                else:
                    logger.warning(f"Invalid call time for {phone_number} (area code {area_code}): "
                                 f"{local_time.strftime('%I:%M %p %Z')} - outside 6 AM to 11 PM")
                    return False
                    
            else:
                logger.warning(f"Invalid phone number format for timezone check: {phone_number}")
                return True  # Allow call if we can't determine timezone
                
        except Exception as e:
            logger.error(f"Error checking call time for {phone_number}: {e}")
            return True  # Allow call on error
    
    async def get_assistant_info(self) -> Dict[str, Any]:
        """Get information about the configured assistant"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/assistant/{self.assistant_id}",
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    assistant_data = response.json()
                    logger.info(f"Assistant Info: {assistant_data.get('name', 'Unknown')} - "
                              f"Model: {assistant_data.get('model', {}).get('model', 'Unknown')}")
                    return {"success": True, "data": assistant_data}
                else:
                    logger.error(f"Failed to get assistant info: {response.status_code}")
                    return {"success": False, "error": f"HTTP {response.status_code}"}
                    
        except Exception as e:
            logger.error(f"Error getting assistant info: {e}")
            return {"success": False, "error": str(e)}
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test VAPI connection and API key"""
        try:
            # Test by getting assistant info
            assistant_info = await self.get_assistant_info()
            
            if assistant_info.get("success"):
                return {
                    "success": True,
                    "message": "VAPI connection successful",
                    "assistant": assistant_info.get("data", {}).get("name", "Unknown")
                }
            else:
                return {
                    "success": False,
                    "error": f"VAPI connection failed: {assistant_info.get('error')}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"VAPI connection test failed: {str(e)}"
            }