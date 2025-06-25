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
        self.call_statistics = {
            "total_attempts": 0,
            "successful_vapi_calls": 0,
            "failed_vapi_calls": 0,
            "time_restriction_blocks": 0,
            "max_attempts_reached": 0
        }
        
    async def start(self):
        """Start the voice agent to process pending leads"""
        self.running = True
        logger.info("Voice Agent started with enhanced debugging")
        logger.info(f"Call settings: {CALL_ATTEMPT_SETTINGS}")
        
        while self.running:
            try:
                await self._process_pending_leads()
                await asyncio.sleep(60)  # Check for new leads every 60 seconds
            except Exception as e:
                logger.error(f"Error in voice agent main loop: {e}")
                await asyncio.sleep(120)  # Wait longer on error
    
    def stop(self):
        """Stop the voice agent"""
        self.running = False
        logger.info(f"Voice Agent stopped. Statistics: {self.call_statistics}")
    
    async def _process_pending_leads(self):
        """Process leads with pending status"""
        db = get_db_session()
        try:
            # Get leads that are pending and ready for calling
            pending_leads = db.query(Lead).filter(
                Lead.status == LeadStatus.PENDING
            ).order_by(Lead.created_at.asc()).limit(10).all()  # Process oldest leads first
            
            if not pending_leads:
                logger.debug("No pending leads found")
                return
                
            logger.info(f"Found {len(pending_leads)} pending leads to process")
            
            for lead in pending_leads:
                try:
                    logger.info(f"=== Processing Lead {lead.id} ===")
                    logger.info(f"Lead: {lead.first_name} {lead.last_name}, Phone: {lead.phone1}")
                    
                    # Check if we should still attempt calls for this lead
                    should_call, reason = await self._should_attempt_call(lead, db)
                    
                    if should_call:
                        logger.info(f"Lead {lead.id}: Attempting call")
                        await self._process_single_lead(lead, db)
                    else:
                        logger.info(f"Lead {lead.id}: Skipping call - {reason}")
                        if "maximum attempts" in reason.lower():
                            self._update_lead_status(lead, LeadStatus.NO_CONTACT, db, error=reason)
                            self.call_statistics["max_attempts_reached"] += 1
                            db.commit()
                        # If it's just timing, leave as pending for later
                        
                except Exception as e:
                    logger.error(f"Error processing lead {lead.id}: {e}")
                    self._update_lead_status(lead, LeadStatus.CALL_FAILED, db, error=str(e))
                    self.call_statistics["failed_vapi_calls"] += 1
                    db.commit()
                    
        except Exception as e:
            logger.error(f"Error in _process_pending_leads: {e}")
        finally:
            db.close()
    
    async def _should_attempt_call(self, lead: Lead, db: Session) -> tuple[bool, str]:
        """Determine if we should attempt to call this lead based on call settings"""
        try:
            # Get the current call logs for this lead
            call_logs = db.query(CallLog).filter(CallLog.lead_id == lead.id).order_by(CallLog.started_at.desc()).all()
            
            logger.debug(f"Lead {lead.id}: Found {len(call_logs)} existing call logs")
            
            # If no call logs, this is the first attempt
            if not call_logs:
                logger.debug(f"Lead {lead.id}: First call attempt")
                return True, "First call attempt"
                
            # Calculate days since first call attempt
            first_call = min(log.started_at for log in call_logs if log.started_at)
            days_since_first_call = (datetime.utcnow() - first_call).days + 1
            
            logger.debug(f"Lead {lead.id}: Days since first call: {days_since_first_call}")
            
            # If beyond max days, don't call
            if days_since_first_call > MAX_CALL_DAYS:
                return False, f"Beyond max call days ({MAX_CALL_DAYS})"
                
            # Get max attempts for current day
            day_key = min(days_since_first_call, max(CALL_ATTEMPT_SETTINGS.keys()))
            day_settings = CALL_ATTEMPT_SETTINGS.get(day_key, {"max_attempts": 0, "min_interval_minutes": 0})
            
            logger.debug(f"Lead {lead.id}: Day {days_since_first_call} settings: {day_settings}")
            
            # If day config says 0 attempts, don't call
            if day_settings["max_attempts"] == 0:
                return False, f"No attempts allowed for day {days_since_first_call}"
                
            # Count calls made today
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            calls_today = sum(1 for log in call_logs if log.started_at and log.started_at >= today_start)
            
            logger.debug(f"Lead {lead.id}: Calls made today: {calls_today}/{day_settings['max_attempts']}")
            
            # If reached max attempts for today, don't call
            if calls_today >= day_settings["max_attempts"]:
                return False, f"Reached max attempts for today ({calls_today}/{day_settings['max_attempts']})"
                
            # Check total attempts across all days
            if len(call_logs) >= MAX_TOTAL_ATTEMPTS:
                return False, f"Reached maximum total attempts ({len(call_logs)}/{MAX_TOTAL_ATTEMPTS})"
                
            # Check if minimum interval has passed since last call
            if call_logs:
                last_call = max(log.started_at for log in call_logs if log.started_at)
                min_interval = timedelta(minutes=day_settings["min_interval_minutes"])
                time_since_last = datetime.utcnow() - last_call
                
                logger.debug(f"Lead {lead.id}: Time since last call: {time_since_last}, Min interval: {min_interval}")
                
                if time_since_last < min_interval:
                    return False, f"Minimum interval not met ({time_since_last} < {min_interval})"
                    
            # All checks passed, we can call
            return True, "All checks passed"
            
        except Exception as e:
            logger.error(f"Error in _should_attempt_call for lead {lead.id}: {e}")
            return False, f"Error in validation: {str(e)}"
    
    async def _process_single_lead(self, lead: Lead, db: Session):
        """Process a single lead by making an outbound call"""
        logger.info(f"=== MAKING CALL FOR LEAD {lead.id} ===")
        
        self.call_statistics["total_attempts"] += 1
        
        # Validate phone number first
        if not lead.phone1 or len(lead.phone1.strip()) < 10:
            error_msg = f"Invalid phone number: {lead.phone1}"
            logger.error(f"Lead {lead.id}: {error_msg}")
            self._update_lead_status(lead, LeadStatus.CALL_FAILED, db, error=error_msg)
            self.call_statistics["failed_vapi_calls"] += 1
            db.commit()
            return
            
        # Check if this is a valid time to call
        is_valid_time = await self.vapi_service.is_valid_call_time(lead.phone1)
        if not is_valid_time:
            error_msg = f"Outside of allowed calling hours"
            logger.warning(f"Lead {lead.id}: {error_msg}")
            self.call_statistics["time_restriction_blocks"] += 1
            # Leave as pending for retry later
            return
        
        # Update status to calling BEFORE making the call
        logger.info(f"Lead {lead.id}: Updating status to CALLING")
        self._update_lead_status(lead, LeadStatus.CALLING, db)
        db.commit()
        
        # Format phone number
        formatted_phone = self.vapi_service._format_phone_number(lead.phone1.strip())
        logger.info(f"Lead {lead.id}: Phone formatted from '{lead.phone1}' to '{formatted_phone}'")
        
        # Prepare call data
        call_data = {
            "assistant_id": self.vapi_service.assistant_id,
            "customer": {
                "number": formatted_phone
            },
            "lead_data": {
                "first_name": lead.first_name or "",
                "last_name": lead.last_name or "",
                "email": lead.email or "",
                "phone": lead.phone1 or "",
                "address": lead.address or "",
                "city": lead.city or "",
                "state": lead.state or "",
                "zip_code": lead.zip_code or ""
            }
        }
        
        logger.info(f"Lead {lead.id}: Prepared call data: {call_data}")
        
        # Create call log BEFORE making the call
        call_log = CallLog(
            lead_id=lead.id,
            phone_number=lead.phone1,
            call_status="attempting",
            started_at=datetime.utcnow()
        )
        db.add(call_log)
        db.commit()  # Commit to get the call log ID
        
        logger.info(f"Lead {lead.id}: Created call log {call_log.id}")
        
        try:
            # Make the actual VAPI call
            logger.info(f"Lead {lead.id}: Calling VAPI service...")
            call_result = await self.vapi_service.make_outbound_call(call_data)
            
            logger.info(f"Lead {lead.id}: VAPI call result: {call_result}")
            
            if call_result.get("success"):
                # SUCCESS: Update call log with VAPI call ID
                call_log.call_sid = call_result.get("call_id")
                call_log.call_status = "initiated"
                call_log.vapi_call_data = call_result
                
                # Update lead with call information
                lead.call_sid = call_result.get("call_id")
                lead.call_started_at = datetime.utcnow()
                
                self.call_statistics["successful_vapi_calls"] += 1
                
                logger.info(f"Lead {lead.id}: VAPI call SUCCESS - Call ID: {call_result.get('call_id')}")
                
                # Start monitoring call completion in background
                asyncio.create_task(self._monitor_call_completion(lead, call_result.get("call_id"), db.query(Lead).filter(Lead.id == lead.id).first()))
                
            else:
                # FAILURE: Log the exact error
                error_msg = call_result.get("error", "Unknown VAPI error")
                logger.error(f"Lead {lead.id}: VAPI call FAILED - {error_msg}")
                
                call_log.call_status = "failed"
                call_log.vapi_call_data = call_result
                
                self._update_lead_status(lead, LeadStatus.CALL_FAILED, db, error=error_msg)
                self.call_statistics["failed_vapi_calls"] += 1
                
        except Exception as e:
            # EXCEPTION: Log the exception
            error_msg = f"Exception during VAPI call: {str(e)}"
            logger.error(f"Lead {lead.id}: {error_msg}")
            
            call_log.call_status = "exception"
            call_log.error_message = error_msg
            
            self._update_lead_status(lead, LeadStatus.CALL_FAILED, db, error=error_msg)
            self.call_statistics["failed_vapi_calls"] += 1
        
        # Final commit
        db.commit()
        logger.info(f"Lead {lead.id}: Call processing completed")
    
    async def _monitor_call_completion(self, lead: Lead, call_id: str, updated_lead: Lead):
        """Monitor call completion and process results"""
        logger.info(f"Lead {lead.id}: Starting call monitoring for call {call_id}")
        
        max_wait_time = 300  # 5 minutes max wait
        check_interval = 15  # Check every 15 seconds
        elapsed_time = 0
        
        db = get_db_session()
        try:
            while elapsed_time < max_wait_time:
                await asyncio.sleep(check_interval)
                elapsed_time += check_interval
                
                # Get call status from VAPI
                call_status = await self.vapi_service.get_call_status(call_id)
                
                if call_status.get("success"):
                    status = call_status.get("status")
                    logger.debug(f"Lead {lead.id}: Call status check - {status}")
                    
                    if status in ["completed", "ended", "failed"]:
                        logger.info(f"Lead {lead.id}: Call completed with status: {status}")
                        await self._process_call_completion(updated_lead, call_status, db)
                        return
                        
                else:
                    logger.warning(f"Lead {lead.id}: Failed to get call status: {call_status.get('error')}")
            
            # Timeout reached
            logger.warning(f"Lead {lead.id}: Call monitoring timeout reached")
            self._update_lead_status(updated_lead, LeadStatus.CALL_FAILED, db, error="Call monitoring timeout")
            db.commit()
            
        except Exception as e:
            logger.error(f"Lead {lead.id}: Error monitoring call: {e}")
            self._update_lead_status(updated_lead, LeadStatus.CALL_FAILED, db, error=f"Monitoring error: {str(e)}")
            db.commit()
        finally:
            db.close()

    async def _process_call_completion(self, lead: Lead, call_status: Dict[str, Any], db: Session):
        """Process completed call and extract results"""
        logger.info(f"Lead {lead.id}: Processing call completion")
        
        try:
            # Update call log with completion data
            call_log = db.query(CallLog).filter(
                CallLog.lead_id == lead.id,
                CallLog.call_sid == call_status.get("data", {}).get("id")
            ).first()
            
            if call_log:
                call_log.call_status = call_status.get("status", "completed")
                call_log.ended_at = datetime.utcnow()
                call_log.call_duration = call_status.get("duration")
                call_log.recording_url = call_status.get("recording_url")
                call_log.vapi_call_data = call_status
                
            # Update lead with call completion data
            lead.call_ended_at = datetime.utcnow()
            lead.call_duration = call_status.get("duration", 0)
            lead.call_recording_url = call_status.get("recording_url")
            
            # Extract confirmed data from call analysis
            confirmed_data = await self._extract_confirmed_data(call_status)
            
            if confirmed_data.get("interested") and confirmed_data.get("tcpa_consent"):
                # Lead confirmed and consented
                lead.tcpa_opt_in = True
                lead.confirmed_email = confirmed_data.get("email")
                lead.confirmed_phone = confirmed_data.get("phone")
                lead.confirmed_address = confirmed_data.get("address")
                lead.area_of_interest = confirmed_data.get("area_of_interest")
                
                self._update_lead_status(lead, LeadStatus.CONFIRMED, db)
                logger.info(f"Lead {lead.id}: Marked as CONFIRMED")
                
            elif confirmed_data.get("interested") is False:
                # Lead explicitly not interested
                self._update_lead_status(lead, LeadStatus.NOT_INTERESTED, db)
                logger.info(f"Lead {lead.id}: Marked as NOT_INTERESTED")
                
            else:
                # Call completed but unclear outcome - mark as failed for retry
                self._update_lead_status(lead, LeadStatus.CALL_FAILED, db, 
                                       error="Call completed but unclear outcome")
                logger.info(f"Lead {lead.id}: Marked as CALL_FAILED (unclear outcome)")
            
            db.commit()
            
        except Exception as e:
            logger.error(f"Lead {lead.id}: Error processing call completion: {e}")
            self._update_lead_status(lead, LeadStatus.CALL_FAILED, db, error=str(e))
            db.commit()

    async def _extract_confirmed_data(self, call_status: Dict[str, Any]) -> Dict[str, Any]:
        """Extract confirmed data from call analysis"""
        try:
            analysis = call_status.get("analysis", {})
            transcript = call_status.get("transcript", "")
            
            # Default extraction logic (can be enhanced with better AI analysis)
            return {
                "interested": analysis.get("interested", True),  # Default to True if unclear
                "tcpa_consent": analysis.get("tcpa_consent", False),
                "email": analysis.get("confirmed_email"),
                "phone": analysis.get("confirmed_phone"),
                "address": analysis.get("confirmed_address"),
                "area_of_interest": analysis.get("area_of_interest")
            }
            
        except Exception as e:
            logger.error(f"Error extracting confirmed data: {e}")
            return {
                "interested": False,
                "tcpa_consent": False
            }

    def _update_lead_status(self, lead: Lead, status: LeadStatus, db: Session, error: Optional[str] = None):
        """Update lead status with proper logging"""
        old_status = lead.status
        lead.status = status
        lead.updated_at = datetime.utcnow()
        
        if error:
            # Store error in lead's error_messages field
            if not lead.error_messages:
                lead.error_messages = []
            lead.error_messages.append({
                "timestamp": datetime.utcnow().isoformat(),
                "error": error
            })
            
        logger.info(f"Lead {lead.id}: Status updated from {old_status} to {status}")
        if error:
            logger.error(f"Lead {lead.id}: Error - {error}")

    def get_statistics(self) -> Dict[str, Any]:
        """Get current call statistics"""
        return {
            **self.call_statistics,
            "success_rate": (
                self.call_statistics["successful_vapi_calls"] / 
                max(self.call_statistics["total_attempts"], 1) * 100
            )
        }

# Singleton instance
voice_agent = VoiceAgent() 