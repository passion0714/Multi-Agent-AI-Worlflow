#!/usr/bin/env python3
"""
Check Calling Status Script
Check why leads are stuck in calling status
"""
import sys
import os
from datetime import datetime, timedelta

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.database import get_db_session
from database.models import Lead, CallLog, LeadStatus

def check_calling_status():
    """Check leads stuck in calling status"""
    print("🔍 Checking Leads in CALLING Status")
    print("=" * 40)
    
    db = get_db_session()
    try:
        # Check current lead statuses
        print("📊 Current Lead Status Distribution:")
        for status in LeadStatus:
            count = db.query(Lead).filter(Lead.status == status).count()
            if count > 0:
                print(f"   {status.value}: {count}")
        
        # Get leads in calling status
        calling_leads = db.query(Lead).filter(Lead.status == LeadStatus.CALLING).all()
        
        if calling_leads:
            print(f"\n🚨 Found {len(calling_leads)} leads stuck in CALLING status:")
            
            for lead in calling_leads:
                print(f"\n📋 Lead {lead.id}: {lead.first_name} {lead.last_name}")
                print(f"   Phone: {lead.phone1}")
                print(f"   Call SID: {lead.call_sid}")
                print(f"   Call started: {lead.call_started_at}")
                print(f"   Updated: {lead.updated_at}")
                
                # Check how long they've been in calling status
                if lead.call_started_at:
                    time_since_call = datetime.utcnow() - lead.call_started_at
                    print(f"   ⏰ Time since call started: {time_since_call}")
                    
                    # If more than 10 minutes, it's likely stuck
                    if time_since_call > timedelta(minutes=10):
                        print(f"   ⚠️  STUCK: Call has been running for {time_since_call}")
                
                # Check call logs
                call_logs = db.query(CallLog).filter(CallLog.lead_id == lead.id).order_by(CallLog.started_at.desc()).limit(3).all()
                print(f"   📞 Recent call logs ({len(call_logs)}):")
                for log in call_logs:
                    print(f"     - {log.started_at}: {log.call_status} (SID: {log.call_sid})")
                    if log.error_message:
                        print(f"       Error: {log.error_message}")
        
        else:
            print("\n✅ No leads stuck in CALLING status")
            
    except Exception as e:
        print(f"❌ Error checking calling status: {e}")
    finally:
        db.close()

def fix_stuck_calls():
    """Fix leads stuck in calling status"""
    print("\n🔧 Fixing Stuck Calls")
    print("=" * 20)
    
    db = get_db_session()
    try:
        # Get leads stuck in calling for more than 10 minutes
        stuck_leads = []
        calling_leads = db.query(Lead).filter(Lead.status == LeadStatus.CALLING).all()
        
        for lead in calling_leads:
            if lead.call_started_at:
                time_since_call = datetime.utcnow() - lead.call_started_at
                if time_since_call > timedelta(minutes=10):
                    stuck_leads.append(lead)
        
        if stuck_leads:
            print(f"Found {len(stuck_leads)} stuck leads. Fixing...")
            
            for lead in stuck_leads:
                print(f"   Fixing Lead {lead.id}: {lead.first_name} {lead.last_name}")
                
                # Reset to CALL_FAILED so they can be retried
                lead.status = LeadStatus.CALL_FAILED
                lead.updated_at = datetime.utcnow()
                
                # Clear call fields
                lead.call_sid = None
                lead.call_started_at = None
                
            db.commit()
            print(f"✅ Fixed {len(stuck_leads)} stuck leads")
        else:
            print("✅ No stuck leads found")
            
    except Exception as e:
        print(f"❌ Error fixing stuck calls: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    check_calling_status()
    
    # Ask if user wants to fix stuck calls
    if input("\nDo you want to fix stuck calls? (y/n): ").lower().strip() in ['y', 'yes']:
        fix_stuck_calls()
    else:
        print("Skipping fix.") 