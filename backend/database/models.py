from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from enum import Enum

Base = declarative_base()

class LeadStatus(str, Enum):
    PENDING = "pending"
    CALLING = "calling"
    CONFIRMED = "confirmed"
    CALL_FAILED = "call_failed"
    NOT_INTERESTED = "not_interested"
    ENTRY_IN_PROGRESS = "entry_in_progress"
    ENTERED = "entered"
    ENTRY_FAILED = "entry_failed"

class Lead(Base):
    __tablename__ = "leads"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Basic contact information from CSV
    first_name = Column(String(100))
    last_name = Column(String(100))
    email = Column(String(255))
    phone1 = Column(String(20), index=True)  # Primary phone
    test = Column(String(255))  # Test field from CSV
    address = Column(Text)
    address2 = Column(Text)  # Secondary address
    city = Column(String(100))
    state = Column(String(50))
    zip_code = Column(String(20))
    gender = Column(String(20))
    dob = Column(Date)  # Date of birth
    ip = Column(String(45))  # IP address
    
    # Additional fields from CSV
    subid2 = Column(String(100))
    signup_url = Column(String(500))
    consent_url = Column(String(500))
    education = Column(String(100))
    grad_year = Column(String(10))
    start_date = Column(Date)
    military_type = Column(String(100))
    campus_type = Column(String(100))
    area_of_study = Column(String(255))
    level_of_interest = Column(String(100))
    computer_usage = Column(String(100))
    us_citizen = Column(String(10))
    registered_to_vote = Column(String(10))
    teaching_interest = Column(String(10))
    enrollment_status = Column(String(100))
    
    # Lead processing status
    status = Column(String(50), default=LeadStatus.PENDING, index=True)
    
    # Voice agent collected/confirmed data
    confirmed_email = Column(String(255))
    confirmed_phone = Column(String(20))
    confirmed_address = Column(Text)
    tcpa_opt_in = Column(Boolean, default=False)
    area_of_interest = Column(String(255))
    
    # Call information
    call_sid = Column(String(100))  # VAPI call ID
    call_duration = Column(Integer)  # in seconds
    call_recording_url = Column(String(500))
    call_started_at = Column(DateTime)
    call_ended_at = Column(DateTime)
    
    # Data entry information
    leadhoop_entry_attempts = Column(Integer, default=0)
    leadhoop_entry_success = Column(Boolean, default=False)
    leadhoop_lead_id = Column(String(100))
    
    # Additional metadata
    source = Column(String(100), default="GHL")  # Go High Level
    notes = Column(Text)
    error_messages = Column(JSON)  # Store any error messages as JSON
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<Lead(id={self.id}, phone={self.phone1}, status={self.status})>"

class CallLog(Base):
    __tablename__ = "call_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, index=True)
    call_sid = Column(String(100), index=True)
    
    # Call details
    phone_number = Column(String(20))
    call_status = Column(String(50))  # initiated, ringing, answered, completed, failed
    call_duration = Column(Integer)
    recording_url = Column(String(500))
    recording_s3_key = Column(String(500))  # S3 key for uploaded recording
    
    # VAPI specific data
    vapi_call_data = Column(JSON)  # Store full VAPI response
    
    # Timestamps
    started_at = Column(DateTime)
    ended_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())

class DataEntryLog(Base):
    __tablename__ = "data_entry_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, index=True)
    
    # Entry attempt details
    attempt_number = Column(Integer)
    success = Column(Boolean, default=False)
    error_message = Column(Text)
    screenshot_path = Column(String(500))  # Path to screenshot if error occurred
    
    # LeadHoop specific data
    leadhoop_response = Column(JSON)
    leadhoop_lead_id = Column(String(100))
    
    # Timestamps
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now()) 