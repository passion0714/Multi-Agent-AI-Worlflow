#!/usr/bin/env python3
"""
VAPI Configuration Setup Helper

This script helps you configure VAPI properly for the Multi-Agent AI Workflow system.
"""

import os
import asyncio
import httpx
from dotenv import load_dotenv

load_dotenv()

class VAPISetupHelper:
    def __init__(self):
        self.api_key = os.getenv("VAPI_API_KEY")
        self.base_url = "https://api.vapi.ai"
    
    async def list_phone_numbers(self):
        """List available phone numbers in your VAPI account"""
        if not self.api_key:
            print("❌ VAPI_API_KEY not found in .env file")
            return
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/phone-number",
                    headers=headers,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    phone_numbers = response.json()
                    print("📞 Available Phone Numbers:")
                    print("-" * 50)
                    for phone in phone_numbers:
                        print(f"ID: {phone.get('id')}")
                        print(f"Number: {phone.get('number')}")
                        print(f"Provider: {phone.get('provider')}")
                        print("-" * 30)
                    
                    if phone_numbers:
                        print(f"\n✅ Use this in your .env file:")
                        print(f"VAPI_PHONE_NUMBER_ID={phone_numbers[0].get('id')}")
                    else:
                        print("❌ No phone numbers found. Please purchase a phone number in your VAPI dashboard.")
                else:
                    print(f"❌ Failed to fetch phone numbers: {response.status_code} - {response.text}")
                    
        except Exception as e:
            print(f"❌ Error fetching phone numbers: {e}")
    
    async def list_assistants(self):
        """List available assistants in your VAPI account"""
        if not self.api_key:
            print("❌ VAPI_API_KEY not found in .env file")
            return
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/assistant",
                    headers=headers,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    assistants = response.json()
                    print("🤖 Available Assistants:")
                    print("-" * 50)
                    for assistant in assistants:
                        print(f"ID: {assistant.get('id')}")
                        print(f"Name: {assistant.get('name', 'Unnamed')}")
                        print(f"Model: {assistant.get('model', {}).get('model', 'Unknown')}")
                        print("-" * 30)
                    
                    if assistants:
                        print(f"\n✅ Use this in your .env file:")
                        print(f"VAPI_ASSISTANT_ID={assistants[0].get('id')}")
                    else:
                        print("❌ No assistants found. Please create an assistant in your VAPI dashboard.")
                else:
                    print(f"❌ Failed to fetch assistants: {response.status_code} - {response.text}")
                    
        except Exception as e:
            print(f"❌ Error fetching assistants: {e}")
    
    async def create_zoe_assistant(self):
        """Create the Zoe assistant for lead qualification"""
        if not self.api_key:
            print("❌ VAPI_API_KEY not found in .env file")
            return
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            assistant_config = {
                "name": "Zoe - Lead Qualification Assistant",
                "model": {
                    "provider": "openai",
                    "model": "gpt-4",
                    "messages": [
                        {
                            "role": "system",
                            "content": """You are Zoe, a professional and friendly AI assistant working for Eluminus - Merge. Your role is to make outbound calls to leads to:

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
                        }
                    ]
                },
                "voice": {
                    "provider": "11labs",
                    "voiceId": "21m00Tcm4TlvDq8ikWAM"  # Rachel voice
                },
                "firstMessage": "Hi there! This is Zoe from Eluminus. I'm calling to confirm some information we have on file for you. Do you have a quick moment to chat?",
                "recordingEnabled": True,
                "endCallMessage": "Thank you for your time! Have a great day!",
                "maxDurationSeconds": 300  # 5 minutes max
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/assistant",
                    headers=headers,
                    json=assistant_config,
                    timeout=30.0
                )
                
                if response.status_code == 201:
                    assistant = response.json()
                    print("✅ Successfully created Zoe assistant!")
                    print(f"Assistant ID: {assistant.get('id')}")
                    print(f"\n✅ Add this to your .env file:")
                    print(f"VAPI_ASSISTANT_ID={assistant.get('id')}")
                    return assistant.get('id')
                else:
                    print(f"❌ Failed to create assistant: {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            print(f"❌ Error creating assistant: {e}")
            return None
    
    async def test_configuration(self):
        """Test the current VAPI configuration"""
        print("🔍 Testing VAPI Configuration...")
        print("=" * 50)
        
        # Check API key
        if self.api_key:
            print("✅ VAPI_API_KEY is set")
        else:
            print("❌ VAPI_API_KEY is missing")
            return
        
        # Check phone number ID
        phone_number_id = os.getenv("VAPI_PHONE_NUMBER_ID")
        if phone_number_id and phone_number_id != "your_vapi_phone_number_uuid_here":
            print("✅ VAPI_PHONE_NUMBER_ID is set")
        else:
            print("❌ VAPI_PHONE_NUMBER_ID is missing or not configured")
        
        # Check assistant ID
        assistant_id = os.getenv("VAPI_ASSISTANT_ID")
        if assistant_id and assistant_id != "your_vapi_assistant_uuid_here":
            print("✅ VAPI_ASSISTANT_ID is set")
        else:
            print("❌ VAPI_ASSISTANT_ID is missing or not configured")
        
        print("\n" + "=" * 50)

async def main():
    helper = VAPISetupHelper()
    
    print("🚀 VAPI Configuration Setup Helper")
    print("=" * 50)
    
    while True:
        print("\nWhat would you like to do?")
        print("1. Test current configuration")
        print("2. List available phone numbers")
        print("3. List available assistants")
        print("4. Create Zoe assistant")
        print("5. Exit")
        
        choice = input("\nEnter your choice (1-5): ").strip()
        
        if choice == "1":
            await helper.test_configuration()
        elif choice == "2":
            await helper.list_phone_numbers()
        elif choice == "3":
            await helper.list_assistants()
        elif choice == "4":
            await helper.create_zoe_assistant()
        elif choice == "5":
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please enter 1-5.")

if __name__ == "__main__":
    asyncio.run(main()) 