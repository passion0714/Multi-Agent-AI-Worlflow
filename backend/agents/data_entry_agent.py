import os
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
from loguru import logger
from sqlalchemy.orm import Session
from playwright.async_api import async_playwright, Browser, Page

from database.database import get_db_session
from database.models import Lead, LeadStatus, DataEntryLog
from services.leadhoop_service import LeadHoopService

class DataEntryAgent:
    """AI Data Entry Agent that automates data entry into Lead Hoop portal"""
    
    def __init__(self):
        self.leadhoop_service = LeadHoopService()
        self.running = False
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        
    async def start(self):
        """Start the data entry agent to process confirmed leads"""
        self.running = True
        logger.info("Data Entry Agent started")
        
        # Initialize browser
        await self._initialize_browser()
        
        while self.running:
            try:
                await self._process_confirmed_leads()
                await asyncio.sleep(15)  # Check for confirmed leads every 15 seconds
            except Exception as e:
                logger.error(f"Error in data entry agent main loop: {e}")
                await asyncio.sleep(60)  # Wait longer on error
                
        # Cleanup browser
        await self._cleanup_browser()
    
    def stop(self):
        """Stop the data entry agent"""
        self.running = False
        logger.info("Data Entry Agent stopped")
    
    async def _initialize_browser(self):
        """Initialize Playwright browser for UI automation"""
        try:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(
                headless=True,  # Set to False for debugging
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            self.page = await self.browser.new_page()
            
            # Set viewport and user agent
            await self.page.set_viewport_size({"width": 1920, "height": 1080})
            await self.page.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            
            logger.info("Browser initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing browser: {e}")
            raise
    
    async def _cleanup_browser(self):
        """Cleanup browser resources"""
        try:
            if self.page:
                await self.page.close()
            if self.browser:
                await self.browser.close()
            logger.info("Browser cleanup completed")
        except Exception as e:
            logger.error(f"Error during browser cleanup: {e}")
    
    async def _process_confirmed_leads(self):
        """Process leads with confirmed status"""
        db = get_db_session()
        try:
            # Get leads that are confirmed and ready for data entry
            # Use atomic update to prevent race conditions
            confirmed_leads = db.query(Lead).filter(
                Lead.status == LeadStatus.CONFIRMED
            ).limit(3).all()  # Process 3 leads at a time
            
            for lead in confirmed_leads:
                try:
                    # Atomically update status to prevent other instances from picking up the same lead
                    updated_rows = db.query(Lead).filter(
                        Lead.id == lead.id,
                        Lead.status == LeadStatus.CONFIRMED
                    ).update({
                        "status": LeadStatus.ENTRY_IN_PROGRESS,
                        "updated_at": datetime.utcnow()
                    })
                    
                    if updated_rows > 0:
                        db.commit()
                        await self._process_single_lead(lead, db)
                    else:
                        # Another instance already picked up this lead
                        continue
                        
                except Exception as e:
                    logger.error(f"Error processing lead {lead.id}: {e}")
                    self._update_lead_status(lead, LeadStatus.ENTRY_FAILED, db, error=str(e))
                    db.commit()
                    
        finally:
            db.close()
    
    async def _process_single_lead(self, lead: Lead, db: Session):
        """Process a single lead by entering data into Lead Hoop"""
        logger.info(f"Processing data entry for lead {lead.id} - {lead.phone1}")
        
        # Create data entry log
        entry_log = DataEntryLog(
            lead_id=lead.id,
            attempt_number=lead.leadhoop_entry_attempts + 1,
            started_at=datetime.utcnow()
        )
        db.add(entry_log)
        
        try:
            # Prepare lead data for entry
            lead_data = {
                "first_name": lead.first_name,
                "last_name": lead.last_name,
                "email": lead.confirmed_email or lead.email,
                "phone": lead.confirmed_phone or lead.phone1,
                "address": lead.confirmed_address or lead.address,
                "city": lead.city,
                "state": lead.state,
                "zip_code": lead.zip_code,
                "area_of_interest": lead.area_of_interest,
                "tcpa_opt_in": lead.tcpa_opt_in
            }
            
            # Attempt data entry
            entry_result = await self._enter_lead_data(lead_data, entry_log, db)
            
            if entry_result.get("success"):
                # Update lead status to entered
                lead.leadhoop_entry_success = True
                lead.leadhoop_lead_id = entry_result.get("leadhoop_lead_id")
                self._update_lead_status(lead, LeadStatus.ENTERED, db)
                
                # Update entry log
                entry_log.success = True
                entry_log.leadhoop_lead_id = entry_result.get("leadhoop_lead_id")
                entry_log.leadhoop_response = entry_result
                
                logger.info(f"Successfully entered lead {lead.id} into Lead Hoop")
                
            else:
                # Entry failed
                error_msg = entry_result.get("error", "Data entry failed")
                lead.leadhoop_entry_attempts += 1
                
                # Retry logic - if less than 3 attempts, set back to confirmed for retry
                if lead.leadhoop_entry_attempts < 3:
                    self._update_lead_status(lead, LeadStatus.CONFIRMED, db, error=error_msg)
                    logger.warning(f"Data entry failed for lead {lead.id}, will retry. Attempt {lead.leadhoop_entry_attempts}")
                else:
                    self._update_lead_status(lead, LeadStatus.ENTRY_FAILED, db, error=error_msg)
                    logger.error(f"Data entry failed for lead {lead.id} after 3 attempts")
                
                # Update entry log
                entry_log.success = False
                entry_log.error_message = error_msg
                
        except Exception as e:
            error_msg = f"Exception during data entry: {str(e)}"
            lead.leadhoop_entry_attempts += 1
            self._update_lead_status(lead, LeadStatus.ENTRY_FAILED, db, error=error_msg)
            
            entry_log.success = False
            entry_log.error_message = error_msg
            
        finally:
            entry_log.completed_at = datetime.utcnow()
            db.commit()
    
    async def _enter_lead_data(self, lead_data: Dict[str, Any], entry_log: DataEntryLog, db: Session) -> Dict[str, Any]:
        """Enter lead data into Lead Hoop portal using UI automation"""
        try:
            # Navigate to Lead Hoop login page
            login_url = os.getenv("LEADHOOP_LOGIN_URL", "https://leadhoop.com/login")
            await self.page.goto(login_url, wait_until="networkidle")
            
            # Login to Lead Hoop
            await self._login_to_leadhoop()
            
            # Navigate to lead entry form
            portal_url = os.getenv("LEADHOOP_PORTAL_URL", "https://leadhoop.com/portal")
            await self.page.goto(portal_url, wait_until="networkidle")
            
            # Wait for the form to load
            await self.page.wait_for_selector("form", timeout=10000)
            
            # Fill out the form fields
            await self._fill_lead_form(lead_data)
            
            # Submit the form
            submit_result = await self._submit_lead_form()
            
            if submit_result.get("success"):
                return {
                    "success": True,
                    "leadhoop_lead_id": submit_result.get("lead_id"),
                    "message": "Lead successfully entered into Lead Hoop"
                }
            else:
                # Take screenshot for debugging
                screenshot_path = f"screenshots/error_lead_{entry_log.lead_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                await self.page.screenshot(path=screenshot_path)
                entry_log.screenshot_path = screenshot_path
                
                return {
                    "success": False,
                    "error": submit_result.get("error", "Form submission failed")
                }
                
        except Exception as e:
            logger.error(f"Error during Lead Hoop data entry: {e}")
            
            # Take screenshot for debugging
            try:
                screenshot_path = f"screenshots/error_lead_{entry_log.lead_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                await self.page.screenshot(path=screenshot_path)
                entry_log.screenshot_path = screenshot_path
            except:
                pass
            
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _login_to_leadhoop(self):
        """Login to Lead Hoop portal"""
        username = os.getenv("LEADHOOP_USERNAME")
        password = os.getenv("LEADHOOP_PASSWORD")
        
        if not username or not password:
            raise ValueError("Lead Hoop credentials not configured")
        
        # Fill login form
        await self.page.fill('input[name="username"], input[name="email"], #username, #email', username)
        await self.page.fill('input[name="password"], #password', password)
        
        # Submit login form
        await self.page.click('button[type="submit"], input[type="submit"], .login-button')
        
        # Wait for successful login (adjust selector based on Lead Hoop's actual UI)
        await self.page.wait_for_selector('.dashboard, .portal, .main-content', timeout=10000)
        
        logger.info("Successfully logged into Lead Hoop")
    
    async def _fill_lead_form(self, lead_data: Dict[str, Any]):
        """Fill the lead entry form with confirmed data"""
        # Map lead data to form fields (adjust selectors based on actual Lead Hoop form)
        field_mappings = {
            "first_name": ['input[name="first_name"], #first_name, .first-name'],
            "last_name": ['input[name="last_name"], #last_name, .last-name'],
            "email": ['input[name="email"], #email, .email'],
            "phone": ['input[name="phone"], #phone, .phone'],
            "address": ['input[name="address"], #address, .address'],
            "city": ['input[name="city"], #city, .city'],
            "state": ['select[name="state"], #state, .state'],
            "zip_code": ['input[name="zip"], #zip, .zip'],
            "area_of_interest": ['select[name="interest"], #interest, .interest']
        }
        
        for field_name, selectors in field_mappings.items():
            value = lead_data.get(field_name)
            if value:
                for selector in selectors:
                    try:
                        element = await self.page.query_selector(selector)
                        if element:
                            # Check if it's a select element
                            tag_name = await element.evaluate("el => el.tagName.toLowerCase()")
                            if tag_name == "select":
                                await self.page.select_option(selector, value)
                            else:
                                await self.page.fill(selector, str(value))
                            break
                    except:
                        continue
        
        # Handle TCPA opt-in checkbox
        if lead_data.get("tcpa_opt_in"):
            tcpa_selectors = ['input[name="tcpa"], #tcpa, .tcpa-consent']
            for selector in tcpa_selectors:
                try:
                    await self.page.check(selector)
                    break
                except:
                    continue
        
        logger.info("Form filled with lead data")
    
    async def _submit_lead_form(self) -> Dict[str, Any]:
        """Submit the lead form and handle response"""
        try:
            # Submit the form
            submit_selectors = ['button[type="submit"], input[type="submit"], .submit-button']
            for selector in submit_selectors:
                try:
                    await self.page.click(selector)
                    break
                except:
                    continue
            
            # Wait for response/redirect
            await self.page.wait_for_load_state("networkidle", timeout=15000)
            
            # Check for success indicators
            success_selectors = ['.success', '.confirmation', '.thank-you']
            error_selectors = ['.error', '.alert-danger', '.validation-error']
            
            # Check for success
            for selector in success_selectors:
                try:
                    success_element = await self.page.query_selector(selector)
                    if success_element:
                        # Try to extract lead ID from success message
                        success_text = await success_element.text_content()
                        lead_id = self._extract_lead_id_from_text(success_text)
                        
                        return {
                            "success": True,
                            "lead_id": lead_id,
                            "message": success_text
                        }
                except:
                    continue
            
            # Check for errors
            for selector in error_selectors:
                try:
                    error_element = await self.page.query_selector(selector)
                    if error_element:
                        error_text = await error_element.text_content()
                        return {
                            "success": False,
                            "error": error_text
                        }
                except:
                    continue
            
            # If no clear success/error indicators, assume success if no errors
            current_url = self.page.url
            if "success" in current_url.lower() or "thank" in current_url.lower():
                return {
                    "success": True,
                    "lead_id": None,
                    "message": "Form submitted successfully"
                }
            
            return {
                "success": False,
                "error": "Unable to determine submission status"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Form submission error: {str(e)}"
            }
    
    def _extract_lead_id_from_text(self, text: str) -> Optional[str]:
        """Extract lead ID from success message text"""
        import re
        # Look for patterns like "Lead ID: 12345" or "ID: 12345"
        patterns = [
            r'lead\s+id[:\s]+(\w+)',
            r'id[:\s]+(\w+)',
            r'reference[:\s]+(\w+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                return match.group(1)
        
        return None
    
    def _update_lead_status(self, lead: Lead, status: LeadStatus, db: Session, error: Optional[str] = None):
        """Update lead status and handle errors"""
        lead.status = status
        lead.updated_at = datetime.utcnow()
        
        if error:
            if not lead.error_messages:
                lead.error_messages = []
            lead.error_messages.append({
                "timestamp": datetime.utcnow().isoformat(),
                "error": error,
                "agent": "data_entry_agent"
            })
        
        logger.info(f"Updated lead {lead.id} status to {status}")

# Singleton instance
data_entry_agent = DataEntryAgent() 