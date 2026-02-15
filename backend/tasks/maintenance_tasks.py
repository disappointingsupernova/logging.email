from celery_app import celery_app
from lib.database import SessionLocal
from lib.services.health import check_all_services
from models.models import OutboundEmail
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

@celery_app.task
def check_service_health():
    """Check health of all services (scheduled task)"""
    try:
        result = check_all_services()
        logger.info(f"Service health check: {result['status']}")
        
        # Send alert if any service is down
        if result['status'] == 'down':
            from lib.services.email import send_alert
            db = SessionLocal()
            try:
                down_services = [name for name, status in result['services'].items() if status['status'] == 'down']
                send_alert(db, 
                    recipient="admin@logging.email",
                    template_data={
                        "alert_type": "Service Down",
                        "message": f"Services down: {', '.join(down_services)}",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
            finally:
                db.close()
        
        return result
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "error", "error": str(e)}

@celery_app.task
def cleanup_expired_emails():
    """Clean up expired emails (scheduled task)"""
    db = SessionLocal()
    try:
        deleted = db.query(OutboundEmail).filter(
            OutboundEmail.status == 'expired',
            OutboundEmail.expires_at < datetime.utcnow()
        ).delete()
        
        db.commit()
        logger.info(f"Cleaned up {deleted} expired emails")
        return {"deleted": deleted}
    finally:
        db.close()

@celery_app.task
def cleanup_old_sessions():
    """Clean up old revoked sessions (scheduled task)"""
    db = SessionLocal()
    try:
        from models.models import Session as SessionModel
        from datetime import timedelta
        
        cutoff = datetime.utcnow() - timedelta(days=90)
        deleted = db.query(SessionModel).filter(
            SessionModel.revoked_at < cutoff
        ).delete()
        
        db.commit()
        logger.info(f"Cleaned up {deleted} old sessions")
        return {"deleted": deleted}
    finally:
        db.close()
