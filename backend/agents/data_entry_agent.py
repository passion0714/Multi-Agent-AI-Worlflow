import os
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
from loguru import logger
from sqlalchemy.orm import Session
import httpx

from database.database import get_db_session
from database.models import Lead, LeadStatus, DataEntryLog
from services.leadhoop_service import EnhancedLeadHoopService as LeadHoopService

class DataEntryAgent:
    """AI Data Entry Agent that automates data entry into Lead Hoop portal using pre-fill URL"""
    
    def __init__(self):
        self.leadhoop_service = LeadHoopService()
        self._running = False
        self.base_prefill_url = os.getenv("LEADHOOP_PREFILL_URL", "https://ieim-portal.leadhoop.com/consumer/new/aSuRzy0E8XWWKeLJngoDiQ")
        
    @property
    def running(self):
        """Check if the agent is running"""
        return self._running
    
    @running.setter
    def running(self, value):
        """Set the running status"""
        self._running = value
        logger.info(f"Data entry agent running state set to: {value}")

    async def start(self):
        """Start the data entry agent to process confirmed leads"""
        logger.info("Starting Data Entry Agent...")
        print("DataEntryAgent.start() method called")
        
        # Avoid starting if already running
        if self._running:
            logger.warning("Data entry agent is already running")
            print("Data entry agent is already running - skipping start")
            return
        
        try:
            logger.info("Data Entry Agent using HTTP requests mode")
            print("Setting data entry agent running flag to True")
            
            # Set running state
            self._running = True
            logger.info(f"Data Entry Agent started successfully (running={self._running})")
            print(f"Data Entry Agent started successfully (running={self._running})")
            
            # Main processing loop
            print("Starting data entry agent main processing loop")
            while self._running:
                try:
                    # Process confirmed leads using HTTP requests
                    print("Processing confirmed leads...")
                    await self._process_confirmed_leads_http()
                    print("Sleeping for 15 seconds before next check...")
                    await asyncio.sleep(15)  # Check for confirmed leads every 15 seconds
                except Exception as e:
                    error_msg = f"Error in data entry agent main loop: {e}"
                    logger.error(error_msg)
                    print(error_msg)
                    await asyncio.sleep(60)  # Wait longer on error
                    
        except Exception as e:
            error_msg = f"Failed to start Data Entry Agent: {e}"
            logger.error(error_msg)
            print(error_msg)
            self._running = False
            logger.info(f"Data Entry Agent stopped due to error (running={self._running})")
            print(f"Data Entry Agent stopped due to error (running={self._running})")
            
        print("Data entry agent start method completed")
    
    def stop(self):
        """Stop the data entry agent"""
        logger.info("Data Entry Agent stop requested")
        self._running = False

    async def _process_confirmed_leads_http(self):
        """Process leads with confirmed status using HTTP requests"""
        db = None
        try:
            db = get_db_session()
            # Get leads that are confirmed and ready for data entry
            confirmed_leads = db.query(Lead).filter(
                Lead.status == LeadStatus.CONFIRMED
            ).limit(3).all()  # Process 3 leads at a time
            
            if not confirmed_leads:
                logger.debug("No confirmed leads found for data entry")
                return
            
            logger.info(f"Found {len(confirmed_leads)} confirmed leads for data entry")
            
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
                        await self._process_single_lead_http(lead, db)
                    else:
                        # Another instance already picked up this lead
                        logger.debug(f"Lead {lead.id} already picked up by another instance")
                        continue
                        
                except Exception as e:
                    logger.error(f"Error processing lead {lead.id}: {e}")
                    try:
                        self._update_lead_status(lead, LeadStatus.ENTRY_FAILED, db, error=str(e))
                        db.commit()
                    except Exception as commit_error:
                        logger.error(f"Error updating lead status after error: {commit_error}")
                    
        except Exception as e:
            logger.error(f"Error in _process_confirmed_leads_http: {e}")
        finally:
            if db:
                try:
                    db.close()
                except:
                    pass
    
    async def _process_single_lead_http(self, lead: Lead, db: Session):
        """Process a single lead using HTTP requests"""
        logger.info(f"Processing data entry for lead {lead.id} - {lead.phone1}")
        
        # Create data entry log
        try:
            entry_log = DataEntryLog(
                lead_id=lead.id,
                attempt_number=getattr(lead, 'leadhoop_entry_attempts', 0) + 1,
                started_at=datetime.utcnow()
            )
            db.add(entry_log)
            db.commit()
        except Exception as e:
            logger.error(f"Error creating entry log: {e}")
            entry_log = None
        
        try:
            # Generate pre-fill URL with all lead data
            prefill_url = self._generate_prefill_url(lead)
            logger.info(f"Generated pre-fill URL for lead {lead.id}")
            
            # Send HTTP request to the pre-fill URL
            async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
                # First request - load the pre-fill URL
                logger.info(f"Sending HTTP request to pre-fill URL")
                response = await client.get(prefill_url)
                
                response_info = {
                    "status_code": response.status_code,
                    "prefill_url_length": len(prefill_url),
                    "response_length": len(response.content) if response.content else 0
                }
                
                logger.info(f"Response info: {response_info}")
                
                if response.status_code != 200:
                    logger.error(f"Failed to load pre-fill URL. Status code: {response.status_code}")
                    if entry_log:
                        entry_log.success = False
                        entry_log.error_message = f"Failed to load pre-fill URL. Status code: {response.status_code}"
                        entry_log.completed_at = datetime.utcnow()
                    
                    attempts = getattr(lead, 'leadhoop_entry_attempts', 0) + 1
                    if hasattr(lead, 'leadhoop_entry_attempts'):
                        lead.leadhoop_entry_attempts = attempts
                    
                    if attempts < 3:
                        self._update_lead_status(lead, LeadStatus.CONFIRMED, db, 
                                                error=f"Failed to load pre-fill URL. Status code: {response.status_code}")
                    else:
                        self._update_lead_status(lead, LeadStatus.ENTRY_FAILED, db, 
                                                error=f"Failed to load pre-fill URL after 3 attempts")
                    
                    db.commit()
                    return
                
                # Record the pre-fill URL in the entry log
                if entry_log:
                    entry_log.leadhoop_response = {
                        "status_code": response.status_code,
                        "message": "Pre-fill URL loaded successfully"
                    }
                    entry_log.success = True
                    entry_log.completed_at = datetime.utcnow()
                
                # Update lead status to entered status
                if hasattr(lead, 'leadhoop_entry_success'):
                    lead.leadhoop_entry_success = True
                
                self._update_lead_status(lead, LeadStatus.ENTERED, db)
                
                logger.info(f"Successfully processed lead {lead.id}")
                db.commit()
                
        except Exception as e:
            error_msg = f"Exception during HTTP data entry: {str(e)}"
            logger.error(f"Exception processing lead {lead.id}: {e}")
            
            try:
                attempts = getattr(lead, 'leadhoop_entry_attempts', 0) + 1
                if hasattr(lead, 'leadhoop_entry_attempts'):
                    lead.leadhoop_entry_attempts = attempts
                
                self._update_lead_status(lead, LeadStatus.ENTRY_FAILED, db, error=error_msg)
                
                if entry_log:
                    entry_log.success = False
                    entry_log.error_message = error_msg
                    entry_log.completed_at = datetime.utcnow()
                
                db.commit()
            except Exception as update_error:
                logger.error(f"Error updating lead status after exception: {update_error}")
    
    def _update_lead_status(self, lead: Lead, status: LeadStatus, db: Session, error: Optional[str] = None):
        """Update lead status and handle errors"""
        try:
            lead.status = status
            lead.updated_at = datetime.utcnow()
            
            if error:
                try:
                    if not hasattr(lead, 'error_messages') or not lead.error_messages:
                        lead.error_messages = []
                    
                    lead.error_messages.append({
                        "timestamp": datetime.utcnow().isoformat(),
                        "error": error,
                        "agent": "data_entry_agent"
                    })
                except Exception as e:
                    logger.error(f"Error adding error message to lead: {e}")
            
            logger.info(f"Updated lead {lead.id} status to {status}")
        except Exception as e:
            logger.error(f"Failed to update lead status: {e}")
    
    def _generate_prefill_url(self, lead: Lead) -> str:
        """Generate a pre-fill URL with all lead data"""
        # Build query parameters from lead data
        params = {
            "phone1": self._format_phone(lead.phone1),
            "email": getattr(lead, 'confirmed_email', None) or lead.email,
            "ip": getattr(lead, 'ip', ''),
            "firstname": lead.first_name,
            "lastname": lead.last_name,
            "gender": getattr(lead, 'gender', ''),
            "dob": self._format_date(getattr(lead, 'dob', None)),
            "address": getattr(lead, 'confirmed_address', None) or lead.address,
            "address2": getattr(lead, 'address2', ''),
            "zip": lead.zip_code,
            "city": lead.city,
            "state": lead.state,
            "enrolled_status": self._map_enrollment_status(getattr(lead, 'enrollment_status', '')),
            "grad_year": getattr(lead, 'grad_year', ''),
            "education_level_id": self._map_education_level(getattr(lead, 'education', '')),
            "start_date": self._map_start_date(getattr(lead, 'start_date', None)),
            "school_type_ids": self._map_campus_type(getattr(lead, 'campus_type', '')),
            "military_type": self._map_military_type(getattr(lead, 'military_type', '')),
            "level_interest": getattr(lead, 'level_of_interest', '10'),
            "us_citizen": self._map_boolean_value(getattr(lead, 'us_citizen', ''), 'citizenship'),
            "internet_pc": self._map_boolean_value(getattr(lead, 'computer_usage', ''), 'computer-with-internet'),
            "rn_license": self._map_boolean_value(getattr(lead, 'registered_nurse', ''), 'registered-nurse'),
            "teaching_license": self._map_boolean_value(getattr(lead, 'teaching_license', ''), 'teaching-license'),
            "area_study_ids": self._map_area_of_study(getattr(lead, 'area_of_study', '')),
            "subid": getattr(lead, 'subid', ''),
            "subid2": getattr(lead, 'subid2', ''),
            "pub_transaction_id": "Eluminus-Merge-142",
            "signup_url": getattr(lead, 'signup_url', ''),
            "consent_url": getattr(lead, 'consent_url', '')
        }
        
        # Remove empty parameters and build query string
        query_params = "&".join([f"{k}={v}" for k, v in params.items() if v])
        
        # Construct the full URL
        full_url = f"{self.base_prefill_url}?{query_params}"
        return full_url
    
    def _format_phone(self, phone: str) -> str:
        """Format phone number for URL"""
        if not phone:
            return ""
        
        # Remove all non-digit characters
        digits = ''.join(filter(str.isdigit, phone))
        
        # Format as (XXX)XXX-XXXX if we have 10 digits
        if len(digits) == 10:
            return f"({digits[0:3]}){digits[3:6]}-{digits[6:10]}"
        elif len(digits) == 11 and digits[0] == '1':
            return f"({digits[1:4]}){digits[4:7]}-{digits[7:11]}"
        else:
            return phone  # Return original if can't format
    
    def _format_date(self, date_value) -> str:
        """Format date for URL"""
        if not date_value:
            return ""
        
        # If it's already a string, return it
        if isinstance(date_value, str):
            return date_value
        
        # If it's a datetime object, format it as YYYY-MM-DD
        try:
            return date_value.strftime("%Y-%m-%d")
        except:
            return ""
    
    def _map_education_level(self, education: str) -> str:
        """Map education level to the format expected by LeadHoop"""
        education_map = {
            "high school": "education-level-high-school-diploma",
            "ged": "education-level-ged",
            "some college": "education-level-some-college",
            "associate": "education-level-associates-degree",
            "bachelor": "education-level-bachelors-degree",
            "master": "education-level-masters-degree",
            "doctorate": "education-level-doctorate",
        }
        
        if not education:
            return ""
            
        education_lower = education.lower()
        for key, value in education_map.items():
            if key in education_lower:
                return value
                
        return ""
    
    def _map_start_date(self, start_date) -> str:
        """Map start date to format expected by LeadHoop"""
        # If we have an actual date, convert it to the appropriate range
        if start_date:
            try:
                # If it's a string, parse it
                if isinstance(start_date, str):
                    from datetime import datetime
                    start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
                
                # Calculate difference from today
                from datetime import date, timedelta
                today = date.today()
                diff_days = (start_date - today).days
                
                if diff_days < 0:
                    return "desired-start-date-immediately"
                elif diff_days <= 30:
                    return "desired-start-date-immediately"
                elif diff_days <= 90:
                    return "desired-start-date-1-3-months"
                elif diff_days <= 180:
                    return "desired-start-date-3-6-months"
                else:
                    return "desired-start-date-6-plus-months"
            except:
                # If any error in parsing, return empty
                return ""
        
        return "desired-start-date-1-3-months"  # Default value
    
    def _map_campus_type(self, campus_type: str) -> str:
        """Map campus type to format expected by LeadHoop"""
        campus_map = {
            "online": "online",
            "campus": "campus",
            "both": "both"
        }
        
        if not campus_type:
            return "both"  # Default to both
            
        campus_lower = campus_type.lower()
        for key, value in campus_map.items():
            if key in campus_lower:
                return value
                
        return "both"  # Default to both
    
    def _map_military_type(self, military_type: str) -> str:
        """Map military type to format expected by LeadHoop"""
        if not military_type:
            return "military-no-military-affiliation"
            
        military_lower = military_type.lower()
        
        if "no" in military_lower or "none" in military_lower:
            return "military-no-military-affiliation"
        elif "veteran" in military_lower:
            return "military-veteran"
        elif "active" in military_lower:
            return "military-active-duty"
        elif "spouse" in military_lower or "dependent" in military_lower:
            return "military-spouse-dependent"
        elif "reserve" in military_lower:
            return "military-reserves-national-guard"
        
        return "military-no-military-affiliation"  # Default
    
    def _map_boolean_value(self, value: str, prefix: str) -> str:
        """Map yes/no values to format expected by LeadHoop"""
        if not value:
            return ""
            
        value_lower = value.lower()
        
        if value_lower in ["yes", "true", "y", "1"]:
            return f"{prefix}-yes"
        elif value_lower in ["no", "false", "n", "0"]:
            return f"{prefix}-no"
            
        return ""
    
    def _map_area_of_study(self, area: str) -> str:
        """Map area of study to format expected by LeadHoop"""
        area_map = {
            "business": "business",
            "healthcare": "healthcare",
            "nursing": "nursing",
            "medical": "healthcare",
            "education": "education",
            "teaching": "education",
            "technology": "technology",
            "computer": "technology",
            "it": "technology",
            "criminal justice": "criminal-justice",
            "psychology": "psychology",
            "legal": "legal",
            "law": "legal",
            "science": "science",
            "engineering": "engineering",
            "trades": "trades",
            "art": "arts-design"
        }
        
        if not area:
            return ""
            
        area_lower = area.lower()
        for key, value in area_map.items():
            if key in area_lower:
                return value
                
        return ""
    
    def _map_enrollment_status(self, status: str) -> str:
        """Map enrollment status to yes/no value"""
        if not status:
            return "No"
            
        status_lower = status.lower()
        
        if "enrolled" in status_lower or "current" in status_lower:
            return "Yes"
        
        return "No"

# Singleton instance
data_entry_agent = DataEntryAgent()