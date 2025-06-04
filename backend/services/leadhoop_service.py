import os
from typing import Dict, Any, Optional
from loguru import logger

class LeadHoopService:
    """Service for Lead Hoop integration utilities"""
    
    def __init__(self):
        self.login_url = os.getenv("LEADHOOP_LOGIN_URL", "https://leadhoop.com/login")
        self.portal_url = os.getenv("LEADHOOP_PORTAL_URL", "https://leadhoop.com/portal")
        self.username = os.getenv("LEADHOOP_USERNAME")
        self.password = os.getenv("LEADHOOP_PASSWORD")
    
    def validate_lead_data(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate lead data before submission to Lead Hoop"""
        errors = []
        warnings = []
        
        # Required fields validation
        required_fields = ["first_name", "last_name", "email", "phone"]
        for field in required_fields:
            if not lead_data.get(field):
                errors.append(f"Missing required field: {field}")
        
        # Email validation
        email = lead_data.get("email", "")
        if email and "@" not in email:
            errors.append("Invalid email format")
        
        # Phone validation
        phone = lead_data.get("phone", "")
        if phone:
            # Remove non-digits
            phone_digits = ''.join(filter(str.isdigit, phone))
            if len(phone_digits) != 10:
                warnings.append("Phone number should be 10 digits")
        
        # TCPA consent validation
        if not lead_data.get("tcpa_opt_in"):
            warnings.append("TCPA consent not provided - may affect lead quality")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def format_lead_data_for_entry(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format lead data for Lead Hoop entry"""
        formatted_data = {}
        
        # Name formatting
        formatted_data["first_name"] = (lead_data.get("first_name", "")).strip().title()
        formatted_data["last_name"] = (lead_data.get("last_name", "")).strip().title()
        
        # Email formatting
        formatted_data["email"] = (lead_data.get("email", "")).strip().lower()
        
        # Phone formatting - remove all non-digits and format
        phone = lead_data.get("phone", "")
        phone_digits = ''.join(filter(str.isdigit, phone))
        if len(phone_digits) == 10:
            formatted_data["phone"] = f"({phone_digits[:3]}) {phone_digits[3:6]}-{phone_digits[6:]}"
        else:
            formatted_data["phone"] = phone
        
        # Address formatting
        formatted_data["address"] = (lead_data.get("address", "")).strip().title()
        formatted_data["city"] = (lead_data.get("city", "")).strip().title()
        formatted_data["state"] = (lead_data.get("state", "")).strip().upper()
        formatted_data["zip_code"] = (lead_data.get("zip_code", "")).strip()
        
        # Area of interest
        formatted_data["area_of_interest"] = lead_data.get("area_of_interest", "")
        
        # TCPA consent
        formatted_data["tcpa_opt_in"] = bool(lead_data.get("tcpa_opt_in", False))
        
        return formatted_data
    
    def get_form_field_mappings(self) -> Dict[str, list]:
        """Get possible form field selectors for Lead Hoop portal"""
        return {
            "first_name": [
                'input[name="first_name"]',
                'input[name="firstName"]',
                'input[name="fname"]',
                '#first_name',
                '#firstName',
                '.first-name input',
                'input[placeholder*="First"]'
            ],
            "last_name": [
                'input[name="last_name"]',
                'input[name="lastName"]',
                'input[name="lname"]',
                '#last_name',
                '#lastName',
                '.last-name input',
                'input[placeholder*="Last"]'
            ],
            "email": [
                'input[name="email"]',
                'input[type="email"]',
                '#email',
                '.email input',
                'input[placeholder*="email"]'
            ],
            "phone": [
                'input[name="phone"]',
                'input[name="telephone"]',
                'input[type="tel"]',
                '#phone',
                '#telephone',
                '.phone input',
                'input[placeholder*="phone"]'
            ],
            "address": [
                'input[name="address"]',
                'input[name="street"]',
                '#address',
                '#street',
                '.address input',
                'textarea[name="address"]'
            ],
            "city": [
                'input[name="city"]',
                '#city',
                '.city input'
            ],
            "state": [
                'select[name="state"]',
                'input[name="state"]',
                '#state',
                '.state select',
                '.state input'
            ],
            "zip_code": [
                'input[name="zip"]',
                'input[name="zipcode"]',
                'input[name="postal_code"]',
                '#zip',
                '#zipcode',
                '.zip input'
            ],
            "area_of_interest": [
                'select[name="interest"]',
                'select[name="area_of_interest"]',
                'input[name="interest"]',
                '#interest',
                '.interest select'
            ],
            "tcpa_consent": [
                'input[name="tcpa"]',
                'input[name="consent"]',
                'input[name="agree"]',
                '#tcpa',
                '#consent',
                '.tcpa input',
                '.consent input'
            ]
        }
    
    def get_success_indicators(self) -> list:
        """Get possible success indicators after form submission"""
        return [
            '.success',
            '.confirmation',
            '.thank-you',
            '.submitted',
            '.complete',
            '[class*="success"]',
            '[class*="confirmation"]',
            '[class*="thank"]'
        ]
    
    def get_error_indicators(self) -> list:
        """Get possible error indicators after form submission"""
        return [
            '.error',
            '.alert-danger',
            '.validation-error',
            '.form-error',
            '.field-error',
            '[class*="error"]',
            '[class*="invalid"]',
            '.alert.alert-danger'
        ]
    
    def extract_lead_id_patterns(self) -> list:
        """Get regex patterns for extracting lead IDs from success messages"""
        return [
            r'lead\s+id[:\s]+(\w+)',
            r'id[:\s]+(\w+)',
            r'reference[:\s]+(\w+)',
            r'confirmation[:\s]+(\w+)',
            r'number[:\s]+(\w+)'
        ] 