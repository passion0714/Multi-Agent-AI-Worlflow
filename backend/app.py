# Voice Agent instance
voice_agent_instance = None

# Health endpoints
@app.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.get("/health/system")
async def get_system_health():
    """Get comprehensive system health information"""
    from agents.voice_agent import voice_agent_instance
    from services.vapi_service import VAPIService
    from config.call_settings import get_call_settings_summary, validate_call_settings
    from database.database import get_db_session
    from database.models import Lead, CallLog, LeadStatus
    from datetime import datetime, timedelta
    
    db = get_db_session()
    try:
        # Basic system info
        system_info = {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "operational"
        }
        
        # Database statistics
        total_leads = db.query(Lead).count()
        leads_by_status = {}
        for status in LeadStatus:
            count = db.query(Lead).filter(Lead.status == status).count()
            leads_by_status[status.value] = count
        
        # Call statistics (last 24 hours)
        yesterday = datetime.utcnow() - timedelta(days=1)
        recent_calls = db.query(CallLog).filter(CallLog.started_at >= yesterday).count()
        
        # Voice agent statistics
        voice_agent_stats = {}
        if voice_agent_instance:
            voice_agent_stats = voice_agent_instance.get_statistics()
            voice_agent_stats["running"] = voice_agent_instance.running
        
        # VAPI connection test
        vapi_service = VAPIService()
        vapi_test = await vapi_service.test_connection()
        
        # Call settings validation
        call_settings_errors = validate_call_settings()
        call_settings = get_call_settings_summary()
        
        return {
            "system": system_info,
            "database": {
                "total_leads": total_leads,
                "leads_by_status": leads_by_status,
                "recent_calls_24h": recent_calls
            },
            "voice_agent": voice_agent_stats,
            "vapi": vapi_test,
            "call_settings": {
                "configuration": call_settings,
                "validation_errors": call_settings_errors
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting system health: {e}")
        return {
            "system": {
                "timestamp": datetime.utcnow().isoformat(),
                "status": "error",
                "error": str(e)
            }
        }
    finally:
        db.close()

@app.get("/health/calls")
async def get_call_health():
    """Get detailed call processing health information"""
    from database.database import get_db_session
    from database.models import Lead, CallLog, LeadStatus
    from datetime import datetime, timedelta
    
    db = get_db_session()
    try:
        # Get calls from last 24 hours with detailed breakdown
        yesterday = datetime.utcnow() - timedelta(days=1)
        
        # Call logs analysis
        recent_call_logs = db.query(CallLog).filter(CallLog.started_at >= yesterday).all()
        
        call_status_breakdown = {}
        successful_vapi_calls = 0
        failed_vapi_calls = 0
        
        for call_log in recent_call_logs:
            status = call_log.call_status or "unknown"
            call_status_breakdown[status] = call_status_breakdown.get(status, 0) + 1
            
            if call_log.call_sid and call_log.call_status in ["initiated", "completed"]:
                successful_vapi_calls += 1
            else:
                failed_vapi_calls += 1
        
        # Lead status changes in last 24 hours
        recently_updated_leads = db.query(Lead).filter(Lead.updated_at >= yesterday).all()
        
        status_transitions = {}
        for lead in recently_updated_leads:
            status = lead.status.value if lead.status else "unknown"
            status_transitions[status] = status_transitions.get(status, 0) + 1
        
        # Pending leads ready for calling
        pending_leads = db.query(Lead).filter(Lead.status == LeadStatus.PENDING).count()
        
        # Call success rate
        total_call_attempts = len(recent_call_logs)
        success_rate = (successful_vapi_calls / total_call_attempts * 100) if total_call_attempts > 0 else 0
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "call_logs_24h": {
                "total_attempts": total_call_attempts,
                "successful_vapi_calls": successful_vapi_calls,
                "failed_vapi_calls": failed_vapi_calls,
                "success_rate_percent": round(success_rate, 2),
                "status_breakdown": call_status_breakdown
            },
            "lead_updates_24h": {
                "total_updated": len(recently_updated_leads),
                "status_transitions": status_transitions
            },
            "current_queue": {
                "pending_leads": pending_leads
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting call health: {e}")
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }
    finally:
        db.close()

@app.get("/health/vapi")
async def get_vapi_health():
    """Get detailed VAPI service health information"""
    from services.vapi_service import VAPIService
    
    try:
        vapi_service = VAPIService()
        
        # Test connection
        connection_test = await vapi_service.test_connection()
        
        # Get assistant information
        assistant_info = await vapi_service.get_assistant_info()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "connection": connection_test,
            "assistant": assistant_info,
            "configuration": {
                "base_url": vapi_service.base_url,
                "assistant_id": vapi_service.assistant_id,
                "api_key_configured": bool(vapi_service.api_key)
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting VAPI health: {e}")
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        } 