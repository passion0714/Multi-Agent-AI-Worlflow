import os
import sys
# Set up paths properly
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
backend_dir = os.path.join(current_dir, 'backend')

# Add paths to sys.path if not already there
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import pandas as pd
import asyncio
import os
from datetime import datetime
from pydantic import BaseModel

from database.database import get_db, create_tables
from database.models import Lead, LeadStatus, CallLog, DataEntryLog
from agents.voice_agent import voice_agent
from agents.data_entry_agent import DataEntryAgent
from services.vapi_service import VAPIService
from services.s3_service import S3Service
from schemas import LeadCreate, LeadResponse, LeadUpdate, CallLogResponse, DataEntryLogResponse

# Initialize FastAPI app
app = FastAPI(
    title="MERGE AI Multi-Agent Workflow",
    description="Multi-agent AI system for lead processing with voice calls and data entry automation",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables for agent management
agents_running = False

# Initialize data_entry_agent
data_entry_agent = DataEntryAgent()

# Add this class for status update validation
class StatusUpdate(BaseModel):
    status: str

@app.on_event("startup")
async def startup_event():
    """Initialize database and services on startup"""
    global agents_running
    create_tables()
    
    # Verify services
    try:
        s3_service = S3Service()
        s3_service.verify_bucket_access()
    except Exception as e:
        print(f"Warning: S3 service initialization failed: {e}")
    
    # Auto-start agents on application startup
    try:
        background_tasks = BackgroundTasks()
        background_tasks.add_task(voice_agent.start)
        background_tasks.add_task(data_entry_agent.start)
        agents_running = True
        print("Agents auto-started during application startup")
    except Exception as e:
        print(f"Warning: Failed to auto-start agents: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global agents_running
    if agents_running:
        voice_agent.stop()
        data_entry_agent.stop()

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}

# Lead management endpoints
@app.post("/leads/", response_model=LeadResponse)
async def create_lead(lead: LeadCreate, db: Session = Depends(get_db)):
    """Create a new lead"""
    db_lead = Lead(**lead.dict())
    db.add(db_lead)
    db.commit()
    db.refresh(db_lead)
    return db_lead

@app.get("/leads/", response_model=List[LeadResponse])
async def get_leads(
    skip: int = 0, 
    limit: int = 100, 
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get leads with optional filtering"""
    query = db.query(Lead)
    if status:
        query = query.filter(Lead.status == status)
    leads = query.offset(skip).limit(limit).all()
    return leads

@app.get("/leads/{lead_id}", response_model=LeadResponse)
async def get_lead(lead_id: int, db: Session = Depends(get_db)):
    """Get a specific lead by ID"""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead

@app.put("/leads/{lead_id}", response_model=LeadResponse)
async def update_lead(lead_id: int, lead_update: LeadUpdate, db: Session = Depends(get_db)):
    """Update a lead"""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    for field, value in lead_update.dict(exclude_unset=True).items():
        setattr(lead, field, value)
    
    lead.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(lead)
    return lead

@app.delete("/leads/{lead_id}")
async def delete_lead(lead_id: int, db: Session = Depends(get_db)):
    """Delete a lead"""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    db.delete(lead)
    db.commit()
    return {"message": "Lead deleted successfully"}

@app.post("/leads/{lead_id}/status")
async def update_lead_status(lead_id: int, status_update: StatusUpdate, db: Session = Depends(get_db)):
    """Update a lead's status"""
    print(f"Status update endpoint called for lead ID: {lead_id}")
    print(f"Received status_update data: {status_update.dict()}")
    
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        print(f"Lead not found with ID: {lead_id}")
        raise HTTPException(status_code=404, detail="Lead not found")
    
    print(f"Found lead: {lead.id}, current status: {lead.status}")
    
    # Get new status value
    new_status = status_update.status
    print(f"Setting new status: {new_status}")
    
    lead.status = new_status
    lead.updated_at = datetime.utcnow()
    
    try:
        db.commit()
        print(f"Database commit successful, status updated to: {lead.status}")
    except Exception as e:
        print(f"Error during database commit: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    return {"message": "Status updated successfully", "status": lead.status}

# CSV import endpoint
@app.post("/leads/import-csv/")
async def import_leads_from_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Import leads from CSV file (GHL format)"""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    try:
        # Read CSV file
        contents = await file.read()
        df = pd.read_csv(pd.io.common.StringIO(contents.decode('utf-8')))
        
        # Map CSV columns to Lead model fields (exact match from your header)
        column_mapping = {
            'Firstname': 'first_name',
            'Lastname': 'last_name', 
            'Email': 'email',
            'Phone1': 'phone1',
            'Test': 'test',
            'Address': 'address',
            'Address2': 'address2',
            'City': 'city',
            'State': 'state',
            'Zip': 'zip_code',
            'Gender': 'gender',
            'Dob': 'dob',
            'Ip': 'ip',
            'Subid 2': 'subid2',
            'Signup Url': 'signup_url',
            'Consent Url': 'consent_url',
            'Education': 'education',
            'Grad Year': 'grad_year',
            'Start Date': 'start_date',
            'Military Type': 'military_type',
            'Campus Type': 'campus_type',
            'Area Of Study': 'area_of_study',
            'Level Of Interest': 'level_of_interest',
            'Computer Usage': 'computer_usage',
            'US Citizen': 'us_citizen',
            'Registered To Vote': 'registered_to_vote',
            'Teaching Interest': 'teaching_interest',
            'Enrollment Status': 'enrollment_status'
        }
        
        # Rename columns
        df = df.rename(columns=column_mapping)
        
        # Helper function to parse dates safely
        def parse_date(date_str):
            if pd.isna(date_str) or date_str == '' or date_str is None:
                return None
            try:
                return pd.to_datetime(date_str).date()
            except:
                return None
        
        # Create leads
        leads_created = 0
        errors = []
        
        for index, row in df.iterrows():
            try:
                lead_data = {
                    # Basic contact information
                    'first_name': str(row.get('first_name', '')).strip() if pd.notna(row.get('first_name')) else None,
                    'last_name': str(row.get('last_name', '')).strip() if pd.notna(row.get('last_name')) else None,
                    'email': str(row.get('email', '')).strip() if pd.notna(row.get('email')) else None,
                    'phone1': str(row.get('phone1', '')).strip() if pd.notna(row.get('phone1')) else None,
                    'test': str(row.get('test', '')).strip() if pd.notna(row.get('test')) else None,
                    'address': str(row.get('address', '')).strip() if pd.notna(row.get('address')) else None,
                    'address2': str(row.get('address2', '')).strip() if pd.notna(row.get('address2')) else None,
                    'city': str(row.get('city', '')).strip() if pd.notna(row.get('city')) else None,
                    'state': str(row.get('state', '')).strip() if pd.notna(row.get('state')) else None,
                    'zip_code': str(row.get('zip_code', '')).strip() if pd.notna(row.get('zip_code')) else None,
                    'gender': str(row.get('gender', '')).strip() if pd.notna(row.get('gender')) else None,
                    'dob': parse_date(row.get('dob')),
                    'ip': str(row.get('ip', '')).strip() if pd.notna(row.get('ip')) else None,
                    
                    # Additional CSV fields
                    'subid2': str(row.get('subid2', '')).strip() if pd.notna(row.get('subid2')) else None,
                    'signup_url': str(row.get('signup_url', '')).strip() if pd.notna(row.get('signup_url')) else None,
                    'consent_url': str(row.get('consent_url', '')).strip() if pd.notna(row.get('consent_url')) else None,
                    'education': str(row.get('education', '')).strip() if pd.notna(row.get('education')) else None,
                    'grad_year': str(row.get('grad_year', '')).strip() if pd.notna(row.get('grad_year')) else None,
                    'start_date': parse_date(row.get('start_date')),
                    'military_type': str(row.get('military_type', '')).strip() if pd.notna(row.get('military_type')) else None,
                    'campus_type': str(row.get('campus_type', '')).strip() if pd.notna(row.get('campus_type')) else None,
                    'area_of_study': str(row.get('area_of_study', '')).strip() if pd.notna(row.get('area_of_study')) else None,
                    'level_of_interest': str(row.get('level_of_interest', '')).strip() if pd.notna(row.get('level_of_interest')) else None,
                    'computer_usage': str(row.get('computer_usage', '')).strip() if pd.notna(row.get('computer_usage')) else None,
                    'us_citizen': str(row.get('us_citizen', '')).strip() if pd.notna(row.get('us_citizen')) else None,
                    'registered_to_vote': str(row.get('registered_to_vote', '')).strip() if pd.notna(row.get('registered_to_vote')) else None,
                    'teaching_interest': str(row.get('teaching_interest', '')).strip() if pd.notna(row.get('teaching_interest')) else None,
                    'enrollment_status': str(row.get('enrollment_status', '')).strip() if pd.notna(row.get('enrollment_status')) else None,
                    
                    # Processing status
                    'status': LeadStatus.PENDING
                }
                
                # Skip if missing critical fields (phone is most important for calling)
                if not lead_data['phone1'] or lead_data['phone1'] == '':
                    errors.append(f"Row {index + 1}: Missing phone number")
                    continue
                
                # Clean empty strings to None for optional fields
                for key, value in lead_data.items():
                    if value == '' or value == 'nan':
                        lead_data[key] = None
                
                db_lead = Lead(**lead_data)
                db.add(db_lead)
                leads_created += 1
                
            except Exception as e:
                errors.append(f"Row {index + 1}: {str(e)}")
                continue
        
        db.commit()
        
        result = {
            "message": f"Successfully imported {leads_created} leads",
            "leads_created": leads_created
        }
        
        if errors:
            result["errors"] = errors[:10]  # Limit to first 10 errors
            if len(errors) > 10:
                result["errors"].append(f"... and {len(errors) - 10} more errors")
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing CSV: {str(e)}")

# Agent management endpoints
@app.post("/agents/start")
async def start_agents(background_tasks: BackgroundTasks):
    """Start both voice and data entry agents"""
    global agents_running
    if agents_running:
        return {"message": "Agents are already running"}
    
    # Check actual agent status
    print("\n==== AGENT STATUS CHECK ====")
    print(f"Current global agents_running flag: {agents_running}")
    print(f"Voice agent running flag: {voice_agent.running}")
    print(f"Data entry agent running flag: {data_entry_agent.running}")
    print(f"Data entry agent object exists: {data_entry_agent is not None}")
    print("============================\n")
    
    if voice_agent.running or data_entry_agent.running:
        print("Agent status mismatch. Forcing restart.")
        try:
            if voice_agent.running:
                print("Stopping voice agent...")
                voice_agent.stop()
                print("Voice agent stopped.")
            
            if data_entry_agent.running:
                print("Stopping data entry agent...")
                data_entry_agent.stop()
                print("Data entry agent stopped.")
            
            # Wait a bit for cleanup
            await asyncio.sleep(2)
        except Exception as e:
            print(f"Error stopping agents: {e}")
    
    # Set the global flag before starting agents
    agents_running = True
    
    # Start both agents with manual async tasks
    async def start_both_agents():
        try:
            # Start voice agent first
            print("Starting voice agent...")
            voice_agent_task = asyncio.create_task(voice_agent.start())
            print("Voice agent task created")
            
            # Give the voice agent a moment to start
            await asyncio.sleep(1)
            
            # Start data entry agent
            print("Starting data entry agent directly...")
            data_entry_task = asyncio.create_task(data_entry_agent.start())
            print("Data entry agent task created")
            
            # Return immediately, letting both tasks run in the background
            return True
        except Exception as e:
            print(f"Error starting agents: {e}")
            # Set the global flag back to false if there was an error
            global agents_running
            agents_running = False
            return False
    
    # Run the agent start function
    start_result = await start_both_agents()
    
    if start_result:
        print("Agent start tasks created successfully")
        return {"message": "Agents started successfully", "success": True}
    else:
        return {"message": "Failed to start agents", "success": False}

@app.post("/agents/stop")
async def stop_agents():
    """Stop both agents"""
    global agents_running
    if not agents_running:
        return {"message": "Agents are not running"}
    
    voice_agent.stop()
    data_entry_agent.stop()
    agents_running = False
    
    return {"message": "Agents stopped successfully"}

@app.get("/agents/status")
async def get_agent_status():
    """Get the status of both agents"""
    # Print detailed agent information for debugging
    print(f"Global agents_running flag: {agents_running}")
    print(f"Voice agent running flag: {voice_agent.running}")
    print(f"Data entry agent running flag: {data_entry_agent.running}")
    print(f"Data entry agent initialized: {data_entry_agent is not None}")
    
    # Additional debug info to console
    try:
        data_entry_class = type(data_entry_agent).__name__
        print(f"Data entry agent class: {data_entry_class}")
    except Exception as e:
        print(f"Error getting data entry agent info: {e}")
    
    return {
        "voice_agent_running": voice_agent.running,
        "data_entry_agent_running": data_entry_agent.running,
        "agents_running": agents_running,
        "timestamp": datetime.utcnow().isoformat()
    }

# Call logs endpoints
@app.get("/call-logs/", response_model=List[CallLogResponse])
async def get_call_logs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get call logs"""
    call_logs = db.query(CallLog).offset(skip).limit(limit).all()
    return call_logs

@app.get("/call-logs/lead/{lead_id}", response_model=List[CallLogResponse])
async def get_call_logs_for_lead(lead_id: int, db: Session = Depends(get_db)):
    """Get call logs for a specific lead"""
    call_logs = db.query(CallLog).filter(CallLog.lead_id == lead_id).all()
    return call_logs

# Data entry logs endpoints
@app.get("/data-entry-logs/", response_model=List[DataEntryLogResponse])
async def get_data_entry_logs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get data entry logs"""
    entry_logs = db.query(DataEntryLog).offset(skip).limit(limit).all()
    return entry_logs

@app.get("/data-entry-logs/lead/{lead_id}", response_model=List[DataEntryLogResponse])
async def get_data_entry_logs_for_lead(lead_id: int, db: Session = Depends(get_db)):
    """Get data entry logs for a specific lead"""
    entry_logs = db.query(DataEntryLog).filter(DataEntryLog.lead_id == lead_id).all()
    return entry_logs

# Statistics endpoints
@app.get("/stats/dashboard")
async def get_dashboard_stats(db: Session = Depends(get_db)):
    """Get dashboard statistics"""
    total_leads = db.query(Lead).count()
    pending_leads = db.query(Lead).filter(Lead.status == LeadStatus.PENDING).count()
    calling_leads = db.query(Lead).filter(Lead.status == LeadStatus.CALLING).count()
    confirmed_leads = db.query(Lead).filter(Lead.status == LeadStatus.CONFIRMED).count()
    entered_leads = db.query(Lead).filter(Lead.status == LeadStatus.ENTERED).count()
    failed_leads = db.query(Lead).filter(Lead.status.in_([LeadStatus.CALL_FAILED, LeadStatus.ENTRY_FAILED])).count()
    
    return {
        "total_leads": total_leads,
        "pending_leads": pending_leads,
        "calling_leads": calling_leads,
        "confirmed_leads": confirmed_leads,
        "entered_leads": entered_leads,
        "failed_leads": failed_leads,
        "success_rate": (entered_leads / total_leads * 100) if total_leads > 0 else 0
    }

@app.get("/stats/status-breakdown")
async def get_status_breakdown(db: Session = Depends(get_db)):
    """Get breakdown of leads by status"""
    status_counts = {}
    for status in LeadStatus:
        count = db.query(Lead).filter(Lead.status == status).count()
        status_counts[status.value] = count
    
    return status_counts

# Manual operations endpoints
@app.post("/leads/{lead_id}/retry-call")
async def retry_call(lead_id: int, db: Session = Depends(get_db)):
    """Manually retry a call for a specific lead"""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Reset status to pending for retry
    lead.status = LeadStatus.PENDING
    lead.updated_at = datetime.utcnow()
    db.commit()
    
    return {"message": f"Lead {lead_id} marked for call retry"}

@app.post("/leads/{lead_id}/retry-entry")
async def retry_entry(lead_id: int, db: Session = Depends(get_db)):
    """Manually retry data entry for a specific lead"""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Reset status to confirmed for retry
    if lead.status in [LeadStatus.ENTRY_FAILED, LeadStatus.ENTRY_IN_PROGRESS]:
        lead.status = LeadStatus.CONFIRMED
        lead.updated_at = datetime.utcnow()
        db.commit()
        return {"message": f"Lead {lead_id} marked for data entry retry"}
    else:
        raise HTTPException(status_code=400, detail="Lead is not in a state that allows data entry retry")

@app.post("/leads/{lead_id}/mark-confirmed")
async def mark_lead_confirmed(lead_id: int, db: Session = Depends(get_db)):
    """Manually mark a lead as confirmed (skip voice call)"""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    lead.status = LeadStatus.CONFIRMED
    lead.tcpa_opt_in = True  # Assume consent for manual confirmation
    lead.updated_at = datetime.utcnow()
    db.commit()
    
    return {"message": f"Lead {lead_id} manually marked as confirmed"}

# VAPI webhook endpoint
@app.post("/webhooks/vapi")
async def vapi_webhook(webhook_data: dict, db: Session = Depends(get_db)):
    """Handle VAPI webhooks for call status updates"""
    try:
        call_id = webhook_data.get("call", {}).get("id")
        event_type = webhook_data.get("message", {}).get("type")
        
        if not call_id:
            return {"status": "ignored", "reason": "No call ID"}
        
        # Find the lead associated with this call
        lead = db.query(Lead).filter(Lead.call_sid == call_id).first()
        if not lead:
            return {"status": "ignored", "reason": "Lead not found"}
        
        # Update call log
        call_log = db.query(CallLog).filter(CallLog.call_sid == call_id).first()
        if call_log:
            call_log.vapi_call_data = webhook_data
            call_log.call_status = webhook_data.get("call", {}).get("status", "unknown")
        
        # Handle different event types
        if event_type == "call-ended" or event_type == "call.ended":
            # Process call completion
            call_data = webhook_data.get("call", {})
            lead.call_ended_at = datetime.utcnow()
            
            # Handle duration calculation safely
            try:
                duration = call_data.get("duration", 0)
                if isinstance(duration, (int, float)):
                    lead.call_duration = duration
                else:
                    # If duration is not a number, try to calculate it from timestamps
                    started_at = call_data.get("startedAt")
                    ended_at = call_data.get("endedAt")
                    if started_at and ended_at:
                        try:
                            lead.call_duration = (int(ended_at) - int(started_at)) // 1000
                        except:
                            lead.call_duration = 0
            except Exception as e:
                print(f"Error calculating call duration: {e}")
            
            lead.call_recording_url = call_data.get("recordingUrl")
            
            # Extract analysis data if available
            analysis = call_data.get("analysis", {})
            
            # Even with limited or no analysis, mark as confirmed if call completed
            if call_data.get("status") == "completed":
                # Default values for confirmed data
                lead.confirmed_email = analysis.get("confirmed_email", lead.email)
                lead.confirmed_phone = analysis.get("confirmed_phone", lead.phone1)
                lead.confirmed_address = analysis.get("confirmed_address", lead.address)
                
                # Assume basic interest and consent if call completed successfully
                if not analysis:
                    print(f"No analysis data available for call {call_id}. Setting default values.")
                    lead.tcpa_opt_in = True
                    lead.status = LeadStatus.CONFIRMED
                else:
                    lead.tcpa_opt_in = analysis.get("tcpa_consent", True)
                    lead.area_of_interest = analysis.get("area_of_interest")
                    
                    if analysis.get("interested", True) and lead.tcpa_opt_in:
                        lead.status = LeadStatus.CONFIRMED
                    else:
                        lead.status = LeadStatus.NOT_INTERESTED
            else:
                # Call failed, didn't complete, etc.
                lead.status = LeadStatus.CALL_FAILED
                print(f"Call did not complete successfully. Status: {call_data.get('status')}")
        
        db.commit()
        return {"status": "processed"}
        
    except Exception as e:
        print(f"Error processing VAPI webhook: {e}")
        return {"status": "error", "message": str(e)}

# Manual test endpoints
@app.post("/test/force-next-step/{lead_id}")
async def force_next_step(lead_id: int, db: Session = Depends(get_db)):
    """Manually force a lead to the next stage in the workflow (for testing)"""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Determine next status based on current status
    if lead.status == LeadStatus.PENDING:
        lead.status = LeadStatus.CALLING
        message = "Lead moved to CALLING status"
    elif lead.status == LeadStatus.CALLING:
        lead.status = LeadStatus.CONFIRMED
        lead.tcpa_opt_in = True
        message = "Lead moved to CONFIRMED status"
    elif lead.status == LeadStatus.CONFIRMED:
        lead.status = LeadStatus.ENTRY_IN_PROGRESS
        message = "Lead moved to ENTRY_IN_PROGRESS status"
    elif lead.status == LeadStatus.ENTRY_IN_PROGRESS:
        lead.status = LeadStatus.ENTERED
        message = "Lead moved to ENTERED status"
    else:
        # Reset failed leads back to PENDING
        if lead.status in [LeadStatus.CALL_FAILED, LeadStatus.ENTRY_FAILED, LeadStatus.NOT_INTERESTED]:
            lead.status = LeadStatus.PENDING
            message = "Failed lead reset to PENDING status"
        else:
            message = "No status change needed"
    
    lead.updated_at = datetime.utcnow()
    db.commit()
    
    return {"message": message, "lead_id": lead_id, "status": lead.status}

@app.post("/test/set-status/{lead_id}")
async def set_lead_status(lead_id: int, status: str, db: Session = Depends(get_db)):
    """Manually set a lead's status (for testing)"""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    try:
        lead.status = status
        lead.updated_at = datetime.utcnow()
        
        if status == LeadStatus.CONFIRMED:
            lead.tcpa_opt_in = True
        
        db.commit()
        return {"message": f"Lead status set to {status}", "lead_id": lead_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid status: {str(e)}")

@app.post("/test/make-call")
async def test_make_call(phone_number: str, db: Session = Depends(get_db)):
    """Test making a direct call to a phone number and debug VAPI errors"""
    try:
        # Create a test lead for this call
        test_lead = Lead(
            first_name="Test",
            last_name="User",
            email="test@example.com",
            phone1=phone_number,
            address="123 Test St",
            city="Test City",
            state="TX",
            zip_code="12345",
            status=LeadStatus.PENDING
        )
        db.add(test_lead)
        db.commit()
        
        # Create VAPI service
        vapi_service = VAPIService()
        
        # Format phone number
        formatted_phone = vapi_service._format_phone_number(phone_number)
        
        # Check call time restrictions
        is_valid_time = await vapi_service.is_valid_call_time(phone_number)
        
        # Prepare call data
        call_data = {
            "assistant_id": vapi_service.assistant_id,
            "customer": {
                "number": formatted_phone
            },
            "lead_data": {
                "first_name": "Test",
                "last_name": "User",
                "email": "test@example.com",
                "phone": phone_number,
                "address": "123 Test St",
                "city": "Test City",
                "state": "TX",
                "zip_code": "12345"
            }
        }
        
        # Log the info
        print(f"Making test call to {phone_number}")
        print(f"Formatted phone: {formatted_phone}")
        print(f"Is valid time: {is_valid_time}")
        print(f"Call data: {call_data}")
        
        if not is_valid_time:
            return {
                "success": False,
                "message": "Outside allowed calling hours",
                "formatted_phone": formatted_phone,
                "time_check": {
                    "is_valid": is_valid_time
                }
            }
        
        # Make the test call
        call_result = await vapi_service.make_outbound_call(call_data)
        
        # Update the test lead with call info if successful
        if call_result.get("success"):
            test_lead.call_sid = call_result.get("call_id")
            test_lead.call_started_at = datetime.utcnow()
            test_lead.status = LeadStatus.CALLING
            
            # Log the call
            call_log = CallLog(
                lead_id=test_lead.id,
                call_sid=call_result.get("call_id"),
                phone_number=phone_number,
                call_status="initiated",
                vapi_call_data=call_result,
                started_at=datetime.utcnow()
            )
            db.add(call_log)
            db.commit()
        
        return {
            "success": call_result.get("success", False),
            "message": "Call initiated successfully" if call_result.get("success") else call_result.get("error"),
            "call_data": call_result,
            "formatted_phone": formatted_phone,
            "phone_number": phone_number,
            "test_lead_id": test_lead.id,
            "time_check": {
                "is_valid": is_valid_time
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@app.post("/agents/test-data-entry")
async def test_data_entry_agent():
    """Test the data entry agent specifically"""
    try:
        # Create a new instance for testing
        test_agent = DataEntryAgent()
        
        # Initialize the browser only
        print("Testing data entry agent initialization...")
        try:
            await test_agent._initialize_browser()
            browser_init_success = True
            print("Browser initialization successful")
        except Exception as e:
            browser_init_success = False
            print(f"Browser initialization failed: {e}")
        
        # Clean up
        try:
            await test_agent._cleanup_browser()
            print("Browser cleanup successful")
        except Exception as e:
            print(f"Browser cleanup failed: {e}")
        
        return {
            "success": browser_init_success,
            "message": "Data entry agent test completed",
            "agent_initialized": test_agent is not None,
            "browser_initialized": browser_init_success
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Data entry agent test failed: {str(e)}"
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 