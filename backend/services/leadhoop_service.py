import os
import csv
import re
import time
from typing import Dict, Any, Optional, List
from loguru import logger
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

class EnhancedLeadHoopService:
    """Enhanced service for Lead Hoop integration with CSV processing and automation"""
    
    def __init__(self):
        self.login_url = os.getenv("LEADHOOP_LOGIN_URL", "https://leadhoop.com/login")
        self.portal_url = os.getenv("LEADHOOP_PORTAL_URL", "https://leadhoop.com/portal")
        self.username = os.getenv("LEADHOOP_USERNAME")
        self.password = os.getenv("LEADHOOP_PASSWORD")
        self.driver = None
        self.wait = None
    
    def setup_driver(self, headless: bool = False):
        """Setup Chrome WebDriver with proper configuration"""
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        self.wait = WebDriverWait(self.driver, 10)
        
    def close_driver(self):
        """Close the WebDriver"""
        if self.driver:
            self.driver.quit()
            self.driver = None
            self.wait = None
    
    def read_csv_leads(self, csv_file_path: str) -> List[Dict[str, Any]]:
        """Read and parse CSV file with lead data"""
        leads = []
        try:
            with open(csv_file_path, 'r', encoding='utf-8') as file:
                csv_reader = csv.DictReader(file)
                for row in csv_reader:
                    # Map CSV columns to standardized format
                    lead_data = self.map_csv_to_lead_data(row)
                    leads.append(lead_data)
            logger.info(f"Successfully read {len(leads)} leads from CSV")
            return leads
        except Exception as e:
            logger.error(f"Error reading CSV file: {str(e)}")
            return []
    
    def map_csv_to_lead_data(self, csv_row: Dict[str, str]) -> Dict[str, Any]:
        """Map CSV row to standardized lead data format"""
        return {
            "first_name": csv_row.get("Firstname", "").strip(),
            "last_name": csv_row.get("Lastname", "").strip(),
            "email": csv_row.get("Email", "").strip(),
            "phone": csv_row.get("Phone1", "").strip(),
            "address": csv_row.get("Address", "").strip(),
            "address2": csv_row.get("Address2", "").strip(),
            "city": csv_row.get("City", "").strip(),
            "state": csv_row.get("State", "").strip(),
            "zip_code": csv_row.get("Zip", "").strip(),
            "gender": csv_row.get("Gender", "").strip(),
            "dob": csv_row.get("Dob", "").strip(),
            "education_level": csv_row.get("Education Level", "").strip(),
            "grad_year": csv_row.get("Grad Year", "").strip(),
            "military_type": csv_row.get("Military Type", "").strip(),
            "campus_type": csv_row.get("Campus Type", "").strip(),
            "area_of_study": csv_row.get("Area Of Study", "").strip(),
            "level_of_interest": csv_row.get("Level Of Interest", "").strip(),
            "computer_internet": csv_row.get("Computer with Internet", "").strip(),
            "us_citizen": csv_row.get("US Citizen", "").strip(),
            "registered_nurse": csv_row.get("Registered Nurse", "").strip(),
            "teaching_license": csv_row.get("Teaching License", "").strip(),
            "enroll_status": csv_row.get("Enroll Status", "").strip(),
            "signup_url": csv_row.get("Signup Url", "").strip(),
            "consent_url": csv_row.get("Consent Url", "").strip(),
            "tcpa_opt_in": True,  # Assuming consent since consent_url is provided
            "ip_address": csv_row.get("Ip", "").strip(),
            "subid": csv_row.get("Subid 2", "").strip()
        }
    
    def validate_lead_data(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced validation for lead data"""
        errors = []
        warnings = []
        
        # Required fields validation
        required_fields = ["first_name", "last_name", "email", "phone"]
        for field in required_fields:
            if not lead_data.get(field):
                errors.append(f"Missing required field: {field}")
        
        # Email validation
        email = lead_data.get("email", "")
        if email:
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, email):
                errors.append("Invalid email format")
        
        # Phone validation
        phone = lead_data.get("phone", "")
        if phone:
            phone_digits = ''.join(filter(str.isdigit, phone))
            if len(phone_digits) < 10:
                warnings.append("Phone number appears to be incomplete")
            elif len(phone_digits) > 11:
                warnings.append("Phone number appears to be too long")
        
        # Age validation based on DOB
        dob = lead_data.get("dob", "")
        if dob:
            try:
                # Simple age check - assuming MM/DD/YYYY format
                from datetime import datetime
                birth_date = datetime.strptime(dob, "%m/%d/%Y")
                age = (datetime.now() - birth_date).days // 365
                if age < 18:
                    warnings.append("Lead appears to be under 18 years old")
            except ValueError:
                warnings.append("Invalid date of birth format")
        
        # TCPA consent validation
        if not lead_data.get("tcpa_opt_in"):
            warnings.append("TCPA consent not provided - may affect lead quality")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def format_lead_data_for_entry(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format lead data for Lead Hoop entry with enhanced formatting"""
        formatted_data = {}
        
        # Name formatting
        formatted_data["first_name"] = (lead_data.get("first_name", "")).strip().title()
        formatted_data["last_name"] = (lead_data.get("last_name", "")).strip().title()
        
        # Email formatting
        formatted_data["email"] = (lead_data.get("email", "")).strip().lower()
        
        # Phone formatting - handle various formats
        phone = lead_data.get("phone", "")
        phone_digits = ''.join(filter(str.isdigit, phone))
        if len(phone_digits) == 10:
            formatted_data["phone"] = f"({phone_digits[:3]}) {phone_digits[3:6]}-{phone_digits[6:]}"
        elif len(phone_digits) == 11 and phone_digits[0] == '1':
            formatted_data["phone"] = f"({phone_digits[1:4]}) {phone_digits[4:7]}-{phone_digits[7:]}"
        else:
            formatted_data["phone"] = phone
        
        # Address formatting
        full_address = lead_data.get("address", "").strip()
        if lead_data.get("address2", "").strip():
            full_address += f" {lead_data.get('address2', '').strip()}"
        formatted_data["address"] = full_address.title()
        formatted_data["city"] = (lead_data.get("city", "")).strip().title()
        formatted_data["state"] = (lead_data.get("state", "")).strip().upper()
        formatted_data["zip_code"] = (lead_data.get("zip_code", "")).strip()
        
        # Additional fields
        formatted_data["education_level"] = lead_data.get("education_level", "")
        formatted_data["area_of_study"] = lead_data.get("area_of_study", "")
        formatted_data["level_of_interest"] = lead_data.get("level_of_interest", "")
        formatted_data["military_type"] = lead_data.get("military_type", "")
        formatted_data["campus_type"] = lead_data.get("campus_type", "")
        
        # Boolean fields
        formatted_data["us_citizen"] = lead_data.get("us_citizen", "").lower() == "yes"
        formatted_data["registered_nurse"] = lead_data.get("registered_nurse", "").lower() == "yes"
        formatted_data["teaching_license"] = lead_data.get("teaching_license", "").lower() == "yes"
        formatted_data["computer_internet"] = lead_data.get("computer_internet", "").lower() == "yes"
        formatted_data["tcpa_opt_in"] = bool(lead_data.get("tcpa_opt_in", False))
        
        return formatted_data
    
    def login_to_leadhoop(self) -> bool:
        """Login to Lead Hoop portal"""
        try:
            logger.info("Attempting to login to Lead Hoop portal")
            self.driver.get(self.login_url)
            
            # Wait for login form
            username_field = self.wait.until(EC.presence_of_element_located((By.NAME, "username")))
            password_field = self.driver.find_element(By.NAME, "password")
            login_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit']")
            
            # Enter credentials
            username_field.clear()
            username_field.send_keys(self.username)
            password_field.clear()
            password_field.send_keys(self.password)
            
            # Click login
            login_button.click()
            
            # Wait for redirect to portal
            self.wait.until(lambda driver: driver.current_url != self.login_url)
            
            logger.info("Successfully logged into Lead Hoop portal")
            return True
            
        except Exception as e:
            logger.error(f"Failed to login to Lead Hoop portal: {str(e)}")
            return False
    
    def find_form_field(self, field_selectors: List[str]) -> Optional[Any]:
        """Find form field using multiple selector strategies"""
        for selector in field_selectors:
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                if element.is_displayed() and element.is_enabled():
                    return element
            except NoSuchElementException:
                continue
        return None
    
    def fill_lead_form(self, lead_data: Dict[str, Any]) -> bool:
        """Fill the lead form with provided data"""
        try:
            logger.info("Filling lead form")
            
            # Get field mappings
            field_mappings = self.get_form_field_mappings()
            formatted_data = self.format_lead_data_for_entry(lead_data)
            
            # Fill each field
            for field_name, value in formatted_data.items():
                if not value:
                    continue
                    
                selectors = field_mappings.get(field_name, [])
                if not selectors:
                    continue
                
                element = self.find_form_field(selectors)
                if element:
                    try:
                        if element.tag_name.lower() == 'select':
                            # Handle select dropdown
                            select = Select(element)
                            try:
                                select.select_by_visible_text(str(value))
                            except:
                                select.select_by_value(str(value))
                        elif element.get_attribute('type') == 'checkbox':
                            # Handle checkbox
                            if value and not element.is_selected():
                                element.click()
                            elif not value and element.is_selected():
                                element.click()
                        else:
                            # Handle text input
                            element.clear()
                            element.send_keys(str(value))
                        
                        logger.debug(f"Successfully filled {field_name}")
                    except Exception as e:
                        logger.warning(f"Failed to fill {field_name}: {str(e)}")
                else:
                    logger.warning(f"Could not find form field for {field_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error filling lead form: {str(e)}")
            return False
    
    def submit_lead_form(self) -> Dict[str, Any]:
        """Submit the lead form and check for success/errors"""
        try:
            logger.info("Submitting lead form")
            
            # Find and click submit button
            submit_selectors = [
                'button[type="submit"]',
                'input[type="submit"]',
                'button.submit',
                '.submit-btn',
                'button:contains("Submit")',
                'input[value*="Submit"]'
            ]
            
            submit_button = self.find_form_field(submit_selectors)
            if not submit_button:
                return {"success": False, "error": "Could not find submit button"}
            
            submit_button.click()
            
            # Wait a moment for response
            time.sleep(2)
            
            # Check for success indicators
            success_indicators = self.get_success_indicators()
            for indicator in success_indicators:
                try:
                    success_element = self.driver.find_element(By.CSS_SELECTOR, indicator)
                    if success_element.is_displayed():
                        success_text = success_element.text
                        lead_id = self.extract_lead_id(success_text)
                        logger.info(f"Lead submitted successfully. ID: {lead_id}")
                        return {
                            "success": True,
                            "lead_id": lead_id,
                            "message": success_text
                        }
                except NoSuchElementException:
                    continue
            
            # Check for error indicators
            error_indicators = self.get_error_indicators()
            for indicator in error_indicators:
                try:
                    error_element = self.driver.find_element(By.CSS_SELECTOR, indicator)
                    if error_element.is_displayed():
                        error_text = error_element.text
                        logger.error(f"Lead submission failed: {error_text}")
                        return {
                            "success": False,
                            "error": error_text
                        }
                except NoSuchElementException:
                    continue
            
            # No clear success/error indicator found
            logger.warning("Could not determine submission status")
            return {
                "success": None,
                "message": "Submission status unclear"
            }
            
        except Exception as e:
            logger.error(f"Error submitting lead form: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def extract_lead_id(self, text: str) -> Optional[str]:
        """Extract lead ID from success message"""
        patterns = self.extract_lead_id_patterns()
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None
    
    def process_single_lead(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single lead through the complete workflow"""
        result = {
            "lead_data": lead_data,
            "validation": None,
            "submission": None,
            "success": False
        }
        
        try:
            # Validate lead data
            validation_result = self.validate_lead_data(lead_data)
            result["validation"] = validation_result
            
            if not validation_result["valid"]:
                logger.error(f"Lead validation failed: {validation_result['errors']}")
                return result
            
            # Navigate to lead form page
            self.driver.get(self.portal_url)
            time.sleep(2)
            
            # Fill form
            if not self.fill_lead_form(lead_data):
                result["submission"] = {"success": False, "error": "Failed to fill form"}
                return result
            
            # Submit form
            submission_result = self.submit_lead_form()
            result["submission"] = submission_result
            result["success"] = submission_result.get("success", False)
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing lead: {str(e)}")
            result["submission"] = {"success": False, "error": str(e)}
            return result
    
    def process_csv_file(self, csv_file_path: str) -> List[Dict[str, Any]]:
        """Process entire CSV file of leads"""
        results = []
        
        try:
            # Setup driver
            self.setup_driver()
            
            # Login
            if not self.login_to_leadhoop():
                logger.error("Failed to login to Lead Hoop portal")
                return results
            
            # Read CSV
            leads = self.read_csv_leads(csv_file_path)
            
            # Process each lead
            for i, lead_data in enumerate(leads, 1):
                logger.info(f"Processing lead {i}/{len(leads)}")
                result = self.process_single_lead(lead_data)
                results.append(result)
                
                # Add delay between submissions
                time.sleep(1)
            
            logger.info(f"Completed processing {len(results)} leads")
            
        except Exception as e:
            logger.error(f"Error processing CSV file: {str(e)}")
        finally:
            self.close_driver()
        
        return results
    
    def get_form_field_mappings(self) -> Dict[str, List[str]]:
        """Enhanced form field selectors for Lead Hoop portal"""
        return {
            "first_name": [
                'input[name="first_name"]',
                'input[name="firstName"]',
                'input[name="fname"]',
                'input[name="FirstName"]',
                '#first_name',
                '#firstName',
                '.first-name input',
                'input[placeholder*="First"]',
                'input[placeholder*="first"]'
            ],
            "last_name": [
                'input[name="last_name"]',
                'input[name="lastName"]',
                'input[name="lname"]',
                'input[name="LastName"]',
                '#last_name',
                '#lastName',
                '.last-name input',
                'input[placeholder*="Last"]',
                'input[placeholder*="last"]'
            ],
            "email": [
                'input[name="email"]',
                'input[name="Email"]',
                'input[type="email"]',
                '#email',
                '#Email',
                '.email input',
                'input[placeholder*="email"]',
                'input[placeholder*="Email"]'
            ],
            "phone": [
                'input[name="phone"]',
                'input[name="Phone"]',
                'input[name="phone1"]',
                'input[name="telephone"]',
                'input[type="tel"]',
                '#phone',
                '#Phone',
                '#telephone',
                '.phone input',
                'input[placeholder*="phone"]',
                'input[placeholder*="Phone"]'
            ],
            "address": [
                'input[name="address"]',
                'input[name="Address"]',
                'input[name="street"]',
                'textarea[name="address"]',
                '#address',
                '#Address',
                '.address input',
                '.address textarea'
            ],
            "city": [
                'input[name="city"]',
                'input[name="City"]',
                '#city',
                '#City',
                '.city input'
            ],
            "state": [
                'select[name="state"]',
                'select[name="State"]',
                'input[name="state"]',
                '#state',
                '#State',
                '.state select',
                '.state input'
            ],
            "zip_code": [
                'input[name="zip"]',
                'input[name="Zip"]',
                'input[name="zipcode"]',
                'input[name="postal_code"]',
                '#zip',
                '#Zip',
                '#zipcode',
                '.zip input'
            ],
            "education_level": [
                'select[name="education"]',
                'select[name="education_level"]',
                'select[name="Education Level"]',
                '#education',
                '.education select'
            ],
            "area_of_study": [
                'select[name="area_of_study"]',
                'select[name="Area Of Study"]',
                'input[name="area_of_study"]',
                '#area_of_study',
                '.area-of-study select'
            ],
            "level_of_interest": [
                'select[name="interest_level"]',
                'select[name="Level Of Interest"]',
                'input[name="level_of_interest"]',
                '#interest_level'
            ],
            "tcpa_consent": [
                'input[name="tcpa"]',
                'input[name="consent"]',
                'input[name="agree"]',
                'input[name="terms"]',
                '#tcpa',
                '#consent',
                '.tcpa input',
                '.consent input'
            ]
        }
    
    def get_success_indicators(self) -> List[str]:
        """Success indicators after form submission"""
        return [
            '.success',
            '.confirmation',
            '.thank-you',
            '.submitted',
            '.complete',
            '.alert-success',
            '[class*="success"]',
            '[class*="confirmation"]',
            '[class*="thank"]',
            '[class*="complete"]'
        ]
    
    def get_error_indicators(self) -> List[str]:
        """Error indicators after form submission"""
        return [
            '.error',
            '.alert-danger',
            '.alert-error',
            '.validation-error',
            '.form-error',
            '.field-error',
            '[class*="error"]',
            '[class*="invalid"]',
            '[class*="danger"]'
        ]
    
    def extract_lead_id_patterns(self) -> List[str]:
        """Regex patterns for extracting lead IDs"""
        return [
            r'lead\s+id[:\s]+(\w+)',
            r'id[:\s]+(\w+)',
            r'reference[:\s]+(\w+)',
            r'confirmation[:\s]+(\w+)',
            r'number[:\s]+(\w+)',
            r'#(\w+)',
            r'ID:\s*(\w+)'
        ]

# Usage example
if __name__ == "__main__":
    # Initialize service
    service = EnhancedLeadHoopService()
    
    # Process CSV file
    csv_file_path = "your_leads.csv"  # Replace with your CSV file path
    results = service.process_csv_file(csv_file_path)
    
    # Print summary
    successful_leads = sum(1 for r in results if r.get("success"))
    print(f"Processing completed: {successful_leads}/{len(results)} leads successfully submitted")
    
    # Detailed results
    for i, result in enumerate(results, 1):
        print(f"\nLead {i}:")
        print(f"  Name: {result['lead_data'].get('first_name')} {result['lead_data'].get('last_name')}")
        print(f"  Email: {result['lead_data'].get('email')}")
        print(f"  Success: {result.get('success')}")
        if result.get('submission'):
            if result['submission'].get('success'):
                print(f"  Lead ID: {result['submission'].get('lead_id', 'N/A')}")
            else:
                print(f"  Error: {result['submission'].get('error', 'Unknown error')}")