import os
import httpx
from typing import Dict, Any, Optional
from loguru import logger
import re

class VAPIService:
    """Service for interacting with VAPI for voice calls"""
    
    def __init__(self):
        self.api_key = os.getenv("VAPI_API_KEY")
        self.phone_number = os.getenv("VAPI_PHONE_NUMBER")
        self.phone_number_id = os.getenv("VAPI_PHONE_NUMBER_ID")
        self.assistant_id = os.getenv("VAPI_ASSISTANT_ID")
        self.base_url = "https://api.vapi.ai"
        
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
            return phone
            
        # Remove all non-digit characters
        digits_only = re.sub(r'\D', '', phone)
        
        # If it's a US number without country code, add +1
        if len(digits_only) == 10:
            return f"+1{digits_only}"
        elif len(digits_only) == 11 and digits_only.startswith('1'):
            return f"+{digits_only}"
        elif phone.startswith('+'):
            return phone
        else:
            # Assume US number and add +1
            return f"+1{digits_only}"
    
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
            
            # Format phone number to E.164
            formatted_phone = self._format_phone_number(call_data["phone_number"])
            
            # Prepare call payload
            payload = {
                "phoneNumberId": self.phone_number_id,
                "assistantId": self.assistant_id,
                "customer": {
                    "number": formatted_phone
                },
                "assistantOverrides": {
                    "variableValues": {
                        "leadData": call_data["lead_data"]
                    },
                    "firstMessage": self._generate_first_message(call_data["lead_data"])
                }
            }
            
            logger.info(f"Making VAPI call to {formatted_phone} with assistant {self.assistant_id}")
            
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
                    return {
                        "success": True,
                        "status": call_data.get("status"),
                        "duration": call_data.get("endedAt") and call_data.get("startedAt") and 
                                  (call_data.get("endedAt") - call_data.get("startedAt")) // 1000,
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