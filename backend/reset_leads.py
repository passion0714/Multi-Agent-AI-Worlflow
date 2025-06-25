#!/usr/bin/env python3
"""
Reset Leads Script
This script resets all leads to pending status and clears call logs for fresh testing
"""
import os
import sys
from datetime import datetime

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.database import get_db_session
from database.models import Lead, CallLog, LeadStatus

def reset_leads_to_pending():
    """Reset all leads to pending status and clear call logs"""
    print("🔄 Resetting all leads to PENDING status...")
    
    db = get_db_session()
    try:
        # Get current lead status counts
        total_leads = db.query(Lead).count()
        print(f"📊 Total leads in database: {total_leads}")
        
        status_counts = {}
        for status in LeadStatus:
            count = db.query(Lead).filter(Lead.status == status).count()
            status_counts[status.value] = count
            if count > 0:
                print(f"   {status.value}: {count}")
        
        # Get call log count
        total_call_logs = db.query(CallLog).count()
        print(f"📞 Total call logs: {total_call_logs}")
        
        # Confirm reset
        print("\n⚠️  This will:")
        print("   - Set all leads to PENDING status")
        print("   - Clear all call logs")
        print("   - Reset call-related fields on leads")
        print("   - Allow fresh calling attempts")
        
        confirm = input("\nDo you want to proceed? (yes/no): ").lower().strip()
        
        if confirm not in ['yes', 'y']:
            print("❌ Reset cancelled.")
            return False
        
        print("\n🚀 Starting reset process...")
        
        # Clear all call logs
        if total_call_logs > 0:
            deleted_logs = db.query(CallLog).delete()
            print(f"🗑️  Deleted {deleted_logs} call logs")
        
        # Reset all leads to pending
        updated_leads = 0
        for lead in db.query(Lead).all():
            # Reset status
            lead.status = LeadStatus.PENDING
            
            # Clear call-related fields
            lead.call_sid = None
            lead.call_started_at = None
            lead.call_ended_at = None
            lead.call_duration = None
            lead.call_recording_url = None
            
            # Clear confirmed data fields
            lead.confirmed_email = None
            lead.confirmed_phone = None
            lead.confirmed_address = None
            lead.tcpa_opt_in = False
            lead.area_of_interest = None
            
            # Clear error messages
            lead.error_messages = None
            
            # Update timestamp
            lead.updated_at = datetime.utcnow()
            
            updated_leads += 1
        
        # Commit changes
        db.commit()
        
        print(f"✅ Successfully reset {updated_leads} leads to PENDING status")
        print(f"✅ System is ready for fresh call processing")
        
        # Verify reset
        pending_count = db.query(Lead).filter(Lead.status == LeadStatus.PENDING).count()
        remaining_logs = db.query(CallLog).count()
        
        print(f"\n📊 Post-reset verification:")
        print(f"   Pending leads: {pending_count}")
        print(f"   Remaining call logs: {remaining_logs}")
        
        if pending_count == total_leads and remaining_logs == 0:
            print("🎉 Reset completed successfully!")
        else:
            print("⚠️  Reset may not have completed fully")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during reset: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def reset_specific_status_leads(from_status: LeadStatus, to_status: LeadStatus = LeadStatus.PENDING):
    """Reset leads from specific status to another status"""
    print(f"🔄 Resetting leads from {from_status.value} to {to_status.value}...")
    
    db = get_db_session()
    try:
        # Get leads with specific status
        leads_to_reset = db.query(Lead).filter(Lead.status == from_status).all()
        
        if not leads_to_reset:
            print(f"📊 No leads found with status {from_status.value}")
            return True
        
        print(f"📊 Found {len(leads_to_reset)} leads with status {from_status.value}")
        
        # Confirm reset
        confirm = input(f"\nReset {len(leads_to_reset)} leads from {from_status.value} to {to_status.value}? (yes/no): ").lower().strip()
        
        if confirm not in ['yes', 'y']:
            print("❌ Reset cancelled.")
            return False
        
        # Reset leads
        updated_count = 0
        for lead in leads_to_reset:
            lead.status = to_status
            lead.updated_at = datetime.utcnow()
            updated_count += 1
        
        db.commit()
        
        print(f"✅ Successfully reset {updated_count} leads to {to_status.value}")
        return True
        
    except Exception as e:
        print(f"❌ Error during specific reset: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def show_lead_stats():
    """Show current lead statistics"""
    print("📊 Current Lead Statistics:")
    
    db = get_db_session()
    try:
        total_leads = db.query(Lead).count()
        print(f"   Total leads: {total_leads}")
        
        for status in LeadStatus:
            count = db.query(Lead).filter(Lead.status == status).count()
            if count > 0:
                percentage = (count / total_leads * 100) if total_leads > 0 else 0
                print(f"   {status.value}: {count} ({percentage:.1f}%)")
        
        # Recent call logs
        total_call_logs = db.query(CallLog).count()
        print(f"\n📞 Total call logs: {total_call_logs}")
        
    except Exception as e:
        print(f"❌ Error getting stats: {e}")
    finally:
        db.close()

def main():
    """Main function with menu options"""
    print("🔧 Lead Reset Utility")
    print("=" * 30)
    
    while True:
        print("\nOptions:")
        print("1. Show current lead statistics")
        print("2. Reset ALL leads to PENDING (full reset)")
        print("3. Reset CALL_FAILED leads to PENDING")
        print("4. Reset NO_CONTACT leads to PENDING")
        print("5. Reset CALLING leads to PENDING")
        print("6. Exit")
        
        choice = input("\nSelect option (1-6): ").strip()
        
        if choice == "1":
            show_lead_stats()
        elif choice == "2":
            reset_leads_to_pending()
        elif choice == "3":
            reset_specific_status_leads(LeadStatus.CALL_FAILED, LeadStatus.PENDING)
        elif choice == "4":
            reset_specific_status_leads(LeadStatus.NO_CONTACT, LeadStatus.PENDING)
        elif choice == "5":
            reset_specific_status_leads(LeadStatus.CALLING, LeadStatus.PENDING)
        elif choice == "6":
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid option. Please choose 1-6.")

if __name__ == "__main__":
    main() 