from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from enum import Enum

class LeadStatusEnum(str, Enum):
    PENDING = "pending"
    CALLING = "calling"
    CONFIRMED = "confirmed"
    CALL_FAILED = "call_failed"
    NOT_INTERESTED = "not_interested"
    ENTRY_IN_PROGRESS = "entry_in_progress"
    ENTERED = "entered"
    ENTRY_FAILED = "entry_failed"

class LeadBase(BaseModel):
    # Basic contact information
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None  # Changed from EmailStr to allow invalid emails from CSV
    phone1: Optional[str] = None
    test: Optional[str] = None
    address: Optional[str] = None
    address2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    gender: Optional[str] = None
    dob: Optional[date] = None
    ip: Optional[str] = None
    
    # Additional CSV fields
    subid2: Optional[str] = None
    signup_url: Optional[str] = None
    consent_url: Optional[str] = None
    education: Optional[str] = None
    grad_year: Optional[str] = None
    start_date: Optional[date] = None
    military_type: Optional[str] = None
    campus_type: Optional[str] = None
    area_of_study: Optional[str] = None
    level_of_interest: Optional[str] = None
    computer_usage: Optional[str] = None
    us_citizen: Optional[str] = None
    registered_to_vote: Optional[str] = None
    teaching_interest: Optional[str] = None
    enrollment_status: Optional[str] = None

class LeadCreate(LeadBase):
    pass

class LeadUpdate(BaseModel):
    # Basic contact information
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone1: Optional[str] = None
    test: Optional[str] = None
    address: Optional[str] = None
    address2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    gender: Optional[str] = None
    dob: Optional[date] = None
    ip: Optional[str] = None
    
    # Additional CSV fields
    subid2: Optional[str] = None
    signup_url: Optional[str] = None
    consent_url: Optional[str] = None
    education: Optional[str] = None
    grad_year: Optional[str] = None
    start_date: Optional[date] = None
    military_type: Optional[str] = None
    campus_type: Optional[str] = None
    area_of_study: Optional[str] = None
    level_of_interest: Optional[str] = None
    computer_usage: Optional[str] = None
    us_citizen: Optional[str] = None
    registered_to_vote: Optional[str] = None
    teaching_interest: Optional[str] = None
    enrollment_status: Optional[str] = None
    
    # Processing fields
    status: Optional[LeadStatusEnum] = None
    confirmed_email: Optional[str] = None
    confirmed_phone: Optional[str] = None
    confirmed_address: Optional[str] = None
    tcpa_opt_in: Optional[bool] = None
    area_of_interest: Optional[str] = None
    notes: Optional[str] = None

class LeadResponse(LeadBase):
    id: int
    status: str
    
    # Voice agent collected/confirmed data
    confirmed_email: Optional[str] = None
    confirmed_phone: Optional[str] = None
    confirmed_address: Optional[str] = None
    tcpa_opt_in: bool = False
    area_of_interest: Optional[str] = None
    
    # Call information
    call_sid: Optional[str] = None
    call_duration: Optional[int] = None
    call_recording_url: Optional[str] = None
    call_started_at: Optional[datetime] = None
    call_ended_at: Optional[datetime] = None
    
    # Data entry information
    leadhoop_entry_attempts: int = 0
    leadhoop_entry_success: bool = False
    leadhoop_lead_id: Optional[str] = None
    
    # Metadata
    source: Optional[str] = None
    notes: Optional[str] = None
    error_messages: Optional[List[Dict[str, Any]]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class CallLogResponse(BaseModel):
    id: int
    lead_id: int
    call_sid: Optional[str] = None
    phone_number: Optional[str] = None
    call_status: Optional[str] = None
    call_duration: Optional[int] = None
    recording_url: Optional[str] = None
    recording_s3_key: Optional[str] = None
    vapi_call_data: Optional[Dict[str, Any]] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

class DataEntryLogResponse(BaseModel):
    id: int
    lead_id: int
    attempt_number: int
    success: bool = False
    error_message: Optional[str] = None
    screenshot_path: Optional[str] = None
    leadhoop_response: Optional[Dict[str, Any]] = None
    leadhoop_lead_id: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

class AgentStatus(BaseModel):
    voice_agent_running: bool
    data_entry_agent_running: bool
    agents_running: bool

class DashboardStats(BaseModel):
    total_leads: int
    pending_leads: int
    calling_leads: int
    confirmed_leads: int
    entered_leads: int
    failed_leads: int
    success_rate: float

class StatusBreakdown(BaseModel):
    pending: int
    calling: int
    confirmed: int
    call_failed: int
    not_interested: int
    entry_in_progress: int
    entered: int
    entry_failed: int

class VAPIWebhookData(BaseModel):
    call: Dict[str, Any]
    message: Dict[str, Any]

class ImportResult(BaseModel):
    message: str
    leads_created: Optional[int] = None
    errors: Optional[List[str]] = None 