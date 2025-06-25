#!/usr/bin/env python3
"""
System Debug Script
This script performs comprehensive testing of all system components
"""
import asyncio
import os
import sys
from datetime import datetime, timedelta
from loguru import logger

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.database import get_db_session
from database.models import Lead, CallLog, LeadStatus
from services.vapi_service import VAPIService
from services.s3_service import S3Service
from config.call_settings import get_call_settings_summary, validate_call_settings

async def test_database():
    """Test database connectivity and basic operations"""
    print("\n🔍 Testing Database...")
    
    try:
        db = get_db_session()
        
        # Test basic query
        total_leads = db.query(Lead).count()
        print(f"✅ Database connected - Total leads: {total_leads}")
        
        # Test lead status distribution
        status_counts = {}
        for status in LeadStatus:
            count = db.query(Lead).filter(Lead.status == status).count()
            status_counts[status.value] = count
        
        print(f"📊 Lead status distribution:")
        for status, count in status_counts.items():
            print(f"   {status}: {count}")
        
        # Test recent call logs
        yesterday = datetime.utcnow() - timedelta(days=1)
        recent_calls = db.query(CallLog).filter(CallLog.started_at >= yesterday).count()
        print(f"📞 Call logs (last 24h): {recent_calls}")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

async def test_vapi_service():
    """Test VAPI service connectivity and configuration"""
    print("\n🔍 Testing VAPI Service...")
    
    try:
        vapi_service = VAPIService()
        
        # Test basic configuration
        print(f"🔧 VAPI Configuration:")
        print(f"   Base URL: {vapi_service.base_url}")
        print(f"   Assistant ID: {vapi_service.assistant_id}")
        print(f"   API Key configured: {bool(vapi_service.api_key)}")
        
        # Test connection
        connection_test = await vapi_service.test_connection()
        if connection_test.get("success"):
            print(f"✅ VAPI connection successful")
            print(f"   Assistant: {connection_test.get('assistant', 'Unknown')}")
        else:
            print(f"❌ VAPI connection failed: {connection_test.get('error')}")
            return False
        
        # Test assistant info
        assistant_info = await vapi_service.get_assistant_info()
        if assistant_info.get("success"):
            assistant_data = assistant_info.get("data", {})
            print(f"🤖 Assistant Info:")
            print(f"   Name: {assistant_data.get('name', 'Unknown')}")
            print(f"   Model: {assistant_data.get('model', {}).get('model', 'Unknown')}")
        else:
            print(f"⚠️  Could not get assistant info: {assistant_info.get('error')}")
        
        # Test phone number formatting
        test_phones = ["5551234567", "15551234567", "+15551234567", "555-123-4567"]
        print(f"📱 Phone number formatting tests:")
        for phone in test_phones:
            formatted = vapi_service._format_phone_number(phone)
            print(f"   {phone} -> {formatted}")
        
        return True
        
    except Exception as e:
        print(f"❌ VAPI service error: {e}")
        return False

async def test_s3_service():
    """Test S3 service connectivity and configuration"""
    print("\n🔍 Testing S3 Service...")
    
    try:
        s3_service = S3Service()
        
        # Test basic configuration
        bucket_info = s3_service.get_bucket_info()
        print(f"🔧 S3 Configuration:")
        print(f"   Bucket: {bucket_info['bucket_name']}")
        print(f"   Region: {bucket_info['region']}")
        print(f"   Client configured: {bucket_info['client_configured']}")
        print(f"   Credentials configured: {bucket_info['credentials_configured']}")
        
        if not bucket_info['client_configured']:
            print("⚠️  S3 client not configured - S3 operations disabled")
            return True  # Not an error, just not configured
        
        # Test connection
        connection_test = await s3_service.test_connection()
        if connection_test.get("success"):
            print(f"✅ S3 connection successful")
            print(f"   Message: {connection_test.get('message')}")
        else:
            print(f"❌ S3 connection failed: {connection_test.get('error')}")
            error_code = connection_test.get('error_code')
            if error_code == 'AccessDenied':
                print("💡 Suggestion: Check S3 bucket permissions and credentials")
            elif error_code == 'NoSuchBucket':
                print("💡 Suggestion: Create the S3 bucket or update S3_BUCKET_NAME")
            return False
        
        # Test listing recordings
        recordings = await s3_service.list_recordings(max_keys=5)
        print(f"📁 Recent recordings: {len(recordings)} found")
        
        return True
        
    except Exception as e:
        print(f"❌ S3 service error: {e}")
        return False

def test_call_settings():
    """Test call settings configuration"""
    print("\n🔍 Testing Call Settings...")
    
    try:
        # Get settings summary
        settings_summary = get_call_settings_summary()
        print(f"⚙️  Call Settings Summary:")
        print(f"   Total possible attempts: {settings_summary['total_attempts_possible']}")
        print(f"   Max days: {settings_summary['max_days']}")
        print(f"   Rate limit: {settings_summary['rate_limit_per_minute']} calls/min")
        print(f"   Call hours: {settings_summary['call_hours']}")
        print(f"   Allowed days: {settings_summary['allowed_days']} days/week")
        
        # Validate settings
        validation_errors = validate_call_settings()
        if validation_errors:
            print(f"❌ Call settings validation errors:")
            for error in validation_errors:
                print(f"   - {error}")
            return False
        else:
            print(f"✅ Call settings validation passed")
        
        # Display schedule
        print(f"📅 Call attempt schedule:")
        for day, config in settings_summary['schedule'].items():
            print(f"   Day {day}: {config['max_attempts']} attempts, {config['min_interval_minutes']}min intervals")
        
        return True
        
    except Exception as e:
        print(f"❌ Call settings error: {e}")
        return False

async def test_environment():
    """Test environment variables and configuration"""
    print("\n🔍 Testing Environment Configuration...")
    
    required_vars = [
        "DATABASE_URL",
        "VAPI_API_KEY",
        "VAPI_ASSISTANT_ID"
    ]
    
    optional_vars = [
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "S3_BUCKET_NAME",
        "AWS_REGION"
    ]
    
    print("🔧 Required Environment Variables:")
    missing_required = []
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            display_value = value[:8] + "..." if len(value) > 8 else value
            if "KEY" in var or "SECRET" in var:
                display_value = "*" * min(len(value), 8) + "..."
            print(f"   ✅ {var}: {display_value}")
        else:
            print(f"   ❌ {var}: Not set")
            missing_required.append(var)
    
    print("🔧 Optional Environment Variables:")
    for var in optional_vars:
        value = os.getenv(var)
        if value:
            display_value = value[:8] + "..." if len(value) > 8 else value
            if "KEY" in var or "SECRET" in var:
                display_value = "*" * min(len(value), 8) + "..."
            print(f"   ✅ {var}: {display_value}")
        else:
            print(f"   ⚠️  {var}: Not set")
    
    if missing_required:
        print(f"\n❌ Missing required environment variables: {missing_required}")
        return False
    else:
        print(f"\n✅ All required environment variables configured")
        return True

async def test_sample_lead():
    """Test processing a sample lead (without actually making calls)"""
    print("\n🔍 Testing Sample Lead Processing...")
    
    try:
        db = get_db_session()
        
        # Find a pending lead for testing
        pending_lead = db.query(Lead).filter(Lead.status == LeadStatus.PENDING).first()
        
        if not pending_lead:
            print("⚠️  No pending leads found for testing")
            db.close()
            return True
        
        print(f"📋 Testing with lead {pending_lead.id}:")
        print(f"   Name: {pending_lead.first_name} {pending_lead.last_name}")
        print(f"   Phone: {pending_lead.phone1}")
        print(f"   Status: {pending_lead.status.value}")
        
        # Test phone number formatting
        if pending_lead.phone1:
            vapi_service = VAPIService()
            formatted_phone = vapi_service._format_phone_number(pending_lead.phone1)
            print(f"   Formatted phone: {formatted_phone}")
            
            # Test call time validation
            is_valid_time = await vapi_service.is_valid_call_time(pending_lead.phone1)
            print(f"   Valid call time: {is_valid_time}")
        
        # Test call attempt validation (simulate)
        from agents.voice_agent import VoiceAgent
        voice_agent = VoiceAgent()
        should_call, reason = await voice_agent._should_attempt_call(pending_lead, db)
        print(f"   Should attempt call: {should_call}")
        if not should_call:
            print(f"   Reason: {reason}")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ Sample lead test error: {e}")
        return False

async def run_full_system_test():
    """Run comprehensive system test"""
    print("🚀 Starting Comprehensive System Test")
    print("=" * 50)
    
    test_results = {}
    
    # Run all tests
    test_results['environment'] = await test_environment()
    test_results['database'] = await test_database()
    test_results['call_settings'] = test_call_settings()
    test_results['vapi'] = await test_vapi_service()
    test_results['s3'] = await test_s3_service()
    test_results['sample_lead'] = await test_sample_lead()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name.title()}: {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall Score: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! System is ready for operation.")
    else:
        print("⚠️  Some tests failed. Please address the issues above.")
        print("\n💡 Common fixes:")
        print("   - Check environment variables in .env file")
        print("   - Verify VAPI API key and assistant ID")
        print("   - Check AWS credentials and S3 bucket access")
        print("   - Ensure database is accessible")
    
    return passed == total

if __name__ == "__main__":
    asyncio.run(run_full_system_test()) 