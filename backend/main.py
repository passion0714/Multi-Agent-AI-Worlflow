from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import pandas as pd
import asyncio
import os
from datetime import datetime

from database.database import get_db, create_tables
from database.models import Lead, LeadStatus, CallLog, DataEntryLog
from agents.voice_agent import voice_agent
from agents.data_entry_agent import data_entry_agent
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

@app.on_event("startup")
async def startup_event():
    """Initialize database and services on startup"""
    create_tables()
    
    # Verify services
    try:
        s3_service = S3Service()
        s3_service.verify_bucket_access()
    except Exception as e:
        print(f"Warning: S3 service initialization failed: {e}")

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
    
    agents_running = True
    
    # Start agents in background
    background_tasks.add_task(voice_agent.start)
    background_tasks.add_task(data_entry_agent.start)
    
    return {"message": "Agents started successfully"}

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
    return {
        "voice_agent_running": voice_agent.running,
        "data_entry_agent_running": data_entry_agent.running,
        "agents_running": agents_running
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
        if event_type == "call-ended":
            # Process call completion
            call_data = webhook_data.get("call", {})
            lead.call_ended_at = datetime.utcnow()
            lead.call_duration = call_data.get("duration", 0)
            lead.call_recording_url = call_data.get("recordingUrl")
            
            # Extract analysis data if available
            analysis = call_data.get("analysis", {})
            if analysis:
                lead.confirmed_email = analysis.get("confirmed_email", lead.email)
                lead.confirmed_phone = analysis.get("confirmed_phone", lead.phone)
                lead.confirmed_address = analysis.get("confirmed_address", lead.address)
                lead.tcpa_opt_in = analysis.get("tcpa_consent", False)
                lead.area_of_interest = analysis.get("area_of_interest")
                
                if analysis.get("interested", False) and lead.tcpa_opt_in:
                    lead.status = LeadStatus.CONFIRMED
                else:
                    lead.status = LeadStatus.NOT_INTERESTED
            else:
                lead.status = LeadStatus.CALL_FAILED
        
        db.commit()
        return {"status": "processed"}
        
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 