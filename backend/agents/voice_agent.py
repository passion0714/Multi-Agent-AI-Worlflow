import os
import asyncio
import httpx
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from loguru import logger
from sqlalchemy.orm import Session

from database.database import get_db_session
from database.models import Lead, LeadStatus, CallLog
from services.vapi_service import VAPIService
from services.s3_service import S3Service
from config.call_settings import CALL_ATTEMPT_SETTINGS, MAX_CALL_DAYS, MAX_TOTAL_ATTEMPTS

class VoiceAgent:
    """AI Voice Agent that handles outbound calls via VAPI"""
    
    def __init__(self):
        self.vapi_service = VAPIService()
        self.s3_service = S3Service()
        self.running = False
        
    async def start(self):
        """Start the voice agent to process pending leads"""
        self.running = True
        logger.info("Voice Agent started")
        
        while self.running:
            try:
                await self._process_pending_leads()
                await asyncio.sleep(30)  # Check for new leads every 30 seconds
            except Exception as e:
                logger.error(f"Error in voice agent main loop: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    def stop(self):
        """Stop the voice agent"""
        self.running = False
        logger.info("Voice Agent stopped")
    
    async def _process_pending_leads(self):
        """Process leads with pending status"""
        db = get_db_session()
        try:
            # Get leads that are pending and ready for calling
            pending_leads = db.query(Lead).filter(
                Lead.status == LeadStatus.PENDING
            ).limit(5).all()  # Process 5 leads at a time
            
            for lead in pending_leads:
                try:
                    # Check if we should still attempt calls for this lead based on configuration
                    if await self._should_attempt_call(lead, db):
                        await self._process_single_lead(lead, db)
                    else:
                        # Max attempts reached, mark as no-contact
                        self._update_lead_status(lead, LeadStatus.NO_CONTACT, db, 
                                               error="Maximum call attempts reached")
                        db.commit()
                except Exception as e:
                    logger.error(f"Error processing lead {lead.id}: {e}")
                    self._update_lead_status(lead, LeadStatus.CALL_FAILED, db, error=str(e))
                    
        finally:
            db.close()
    
    async def _should_attempt_call(self, lead: Lead, db: Session) -> bool:
        """Determine if we should attempt to call this lead based on call settings"""
        # Get the current call logs for this lead
        call_logs = db.query(CallLog).filter(CallLog.lead_id == lead.id).all()
        
        # If no call logs, this is the first attempt
        if not call_logs:
            return True
            
        # Calculate days since first call attempt
        first_call = min(log.started_at for log in call_logs if log.started_at)
        days_since_first_call = (datetime.utcnow() - first_call).days + 1  # +1 to count today
        
        # If beyond max days, don't call
        if days_since_first_call > MAX_CALL_DAYS:
            return False
            
        # Get max attempts for current day
        day_settings = CALL_ATTEMPT_SETTINGS.get(
            min(days_since_first_call, max(CALL_ATTEMPT_SETTINGS.keys()))
        )
        
        # If day config says 0 attempts, don't call
        if day_settings["max_attempts"] == 0:
            return False
            
        # Count calls made today
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        calls_today = sum(1 for log in call_logs if log.started_at and log.started_at >= today_start)
        
        # If reached max attempts for today, don't call
        if calls_today >= day_settings["max_attempts"]:
            return False
            
        # Check total attempts across all days
        if len(call_logs) >= MAX_TOTAL_ATTEMPTS:
            return False
            
        # Check if minimum interval has passed since last call
        if call_logs:
            last_call = max(log.started_at for log in call_logs if log.started_at)
            min_interval = timedelta(minutes=day_settings["min_interval_minutes"])
            
            if datetime.utcnow() - last_call < min_interval:
                return False
                
        # All checks passed, we can call
        return True
    
    async def _process_single_lead(self, lead: Lead, db: Session):
        """Process a single lead by making an outbound call"""
        logger.info(f"Processing lead {lead.id} - {lead.phone1}")
        
        # Update status to calling
        self._update_lead_status(lead, LeadStatus.CALLING, db)
        db.commit()  # Ensure status is committed
        
        # Validate phone number
        if not lead.phone1 or len(lead.phone1.strip()) < 10:
            error_msg = f"Invalid phone number: {lead.phone1}"
            logger.error(error_msg)
            self._update_lead_status(lead, LeadStatus.CALL_FAILED, db, error=error_msg)
            db.commit()
            return
            
        # Check if this is a valid time to call based on compliance rules
        # is_valid_time = await self.vapi_service.is_valid_call_time(lead.phone1)
        # if not is_valid_time:
        #     error_msg = f"Outside of allowed calling hours for number: {lead.phone1}"
        #     logger.warning(error_msg)
        #     # Set back to pending for retry later
        #     self._update_lead_status(lead, LeadStatus.PENDING, db, error=error_msg)
        #     db.commit()
        #     return
        
        # # Debug log the phone number
        # logger.info(f"Phone number for outbound call: '{lead.phone1}'")
        
        # Format phone number to E.164 format
        formatted_phone = self.vapi_service._format_phone_number(lead.phone1.strip())
        
        # Prepare call data with proper customer.number field
        call_data = {
            "assistant_id": os.getenv("VAPI_ASSISTANT_ID", "08301bb7-72c5-466c-a0ba-ca54d429c93e"),  # Zoe from Eluminus
            "customer": {
                "number": formatted_phone
            },
            "lead_data": {
                "first_name": lead.first_name,
                "last_name": lead.last_name,
                "email": lead.email,
                "phone": lead.phone1,
                "address": lead.address,
                "city": lead.city,
                "state": lead.state,
                "zip_code": lead.zip_code
            }
        }
        
        # Make the call via VAPI
        call_result = await self.vapi_service.make_outbound_call(call_data)
        
        if call_result.get("success"):
            # Log the call
            call_log = CallLog(
                lead_id=lead.id,
                call_sid=call_result.get("call_id"),
                phone_number=lead.phone1,
                call_status="initiated",
                vapi_call_data=call_result,
                started_at=datetime.utcnow()
            )
            db.add(call_log)
            
            # Update lead with call information
            lead.call_sid = call_result.get("call_id")
            lead.call_started_at = datetime.utcnow()
            
            # Wait for call completion and process results
            await self._monitor_call_completion(lead, call_result.get("call_id"), db)
            
        else:
            # Call failed to initiate
            error_msg = call_result.get("error", "Failed to initiate call")
            self._update_lead_status(lead, LeadStatus.CALL_FAILED, db, error=error_msg)
            
        db.commit()
    
    async def _monitor_call_completion(self, lead: Lead, call_id: str, db: Session):
        """Monitor call completion and process results"""
        max_wait_time = 600  # 10 minutes max wait
        check_interval = 10  # Check every 10 seconds
        elapsed_time = 0
        
        while elapsed_time < max_wait_time:
            try:
                call_status = await self.vapi_service.get_call_status(call_id)
                
                if call_status.get("status") in ["completed", "failed", "no-answer", "busy"]:
                    await self._process_call_completion(lead, call_status, db)
                    return
                    
                await asyncio.sleep(check_interval)
                elapsed_time += check_interval
                
            except Exception as e:
                logger.error(f"Error monitoring call {call_id}: {e}")
                break
        
        # Timeout - mark as failed
        self._update_lead_status(lead, LeadStatus.CALL_FAILED, db, error="Call monitoring timeout")
    
    async def _process_call_completion(self, lead: Lead, call_status: Dict[str, Any], db: Session):
        """Process completed call and extract confirmed data"""
        logger.info(f"Processing call completion for lead {lead.id}")
        
        # Update call information
        lead.call_ended_at = datetime.utcnow()
        lead.call_duration = call_status.get("duration", 0)
        lead.call_recording_url = call_status.get("recording_url")
        
        # Update call log
        call_log = db.query(CallLog).filter(CallLog.call_sid == lead.call_sid).first()
        if call_log:
            call_log.call_status = call_status.get("status")
            call_log.call_duration = call_status.get("duration", 0)
            call_log.recording_url = call_status.get("recording_url")
            call_log.ended_at = datetime.utcnow()
            call_log.vapi_call_data = call_status
        
        # Extract confirmed data from call transcript/analysis
        confirmed_data = await self._extract_confirmed_data(call_status)
        
        if confirmed_data.get("success"):
            # Update lead with confirmed data
            lead.confirmed_email = confirmed_data.get("email", lead.email)
            lead.confirmed_phone = confirmed_data.get("phone", lead.phone1)
            lead.confirmed_address = confirmed_data.get("address", lead.address)
            lead.tcpa_opt_in = confirmed_data.get("tcpa_opt_in", False)
            lead.area_of_interest = confirmed_data.get("area_of_interest")
            
            if confirmed_data.get("interested", False) and lead.tcpa_opt_in:
                self._update_lead_status(lead, LeadStatus.CONFIRMED, db)
                
                # Upload call recording to S3 if available
                if lead.call_recording_url:
                    await self._upload_call_recording(lead, db)
            else:
                self._update_lead_status(lead, LeadStatus.NOT_INTERESTED, db)
        else:
            error_msg = confirmed_data.get("error", "Failed to extract confirmed data")
            self._update_lead_status(lead, LeadStatus.CALL_FAILED, db, error=error_msg)
    
    async def _extract_confirmed_data(self, call_status: Dict[str, Any]) -> Dict[str, Any]:
        """Extract confirmed data from VAPI call results"""
        try:
            # This would typically involve analyzing the call transcript
            # For now, we'll use the structured data returned by VAPI
            transcript = call_status.get("transcript", "")
            analysis = call_status.get("analysis", {})
            
            # Extract structured data from VAPI analysis
            confirmed_data = {
                "success": True,
                "email": analysis.get("confirmed_email"),
                "phone": analysis.get("confirmed_phone"),
                "address": analysis.get("confirmed_address"),
                "tcpa_opt_in": analysis.get("tcpa_consent", False),
                "area_of_interest": analysis.get("area_of_interest"),
                "interested": analysis.get("interested", False)
            }
            
            return confirmed_data
            
        except Exception as e:
            logger.error(f"Error extracting confirmed data: {e}")
            return {"success": False, "error": str(e)}
    
    async def _upload_call_recording(self, lead: Lead, db: Session):
        """Upload call recording to S3 for LeadHoop"""
        try:
            if not lead.call_recording_url:
                return
            
            # Download recording from VAPI
            async with httpx.AsyncClient() as client:
                response = await client.get(lead.call_recording_url)
                if response.status_code == 200:
                    recording_data = response.content
                    
                    # Generate S3 filename according to LeadHoop specs
                    # Format: {phone}_{publisher_id}_{timestamp}.mp3
                    timestamp = lead.call_started_at.strftime("%Y%m%d%H%M%S")
                    filename = f"{lead.phone1}_{os.getenv('PUBLISHER_ID', '142')}_{timestamp}.mp3"
                    
                    # Upload to S3
                    s3_key = await self.s3_service.upload_recording(recording_data, filename)
                    
                    # Update call log with S3 key
                    call_log = db.query(CallLog).filter(CallLog.call_sid == lead.call_sid).first()
                    if call_log:
                        call_log.recording_s3_key = s3_key
                    
                    logger.info(f"Uploaded recording for lead {lead.id} to S3: {s3_key}")
                    
        except Exception as e:
            logger.error(f"Error uploading call recording for lead {lead.id}: {e}")
    
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
                "agent": "voice_agent"
            })
        
        logger.info(f"Updated lead {lead.id} status to {status}")

# Singleton instance
voice_agent = VoiceAgent() 