from celery_app import celery_app
from lib.database import SessionLocal
from lib.services.email import attempt_send, process_pending_emails
from models.models import OutboundEmail
import logging

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, max_retries=3)
def send_email_task(self, email_id: int):
    """Send a single email"""
    db = SessionLocal()
    try:
        email = db.query(OutboundEmail).filter(OutboundEmail.id == email_id).first()
        if not email:
            logger.error(f"Email {email_id} not found")
            return
        
        success = attempt_send(db, email)
        
        if not success and email.status == 'failed' and email.attempts < email.max_attempts:
            # Retry with exponential backoff
            retry_delay = email.next_retry_at.timestamp() - email.last_attempt_at.timestamp()
            raise self.retry(countdown=int(retry_delay))
        
        return {"email_id": email_id, "status": email.status, "attempts": email.attempts}
    
    except Exception as e:
        logger.error(f"Error sending email {email_id}: {e}")
        raise
    finally:
        db.close()

@celery_app.task
def process_pending_emails_task():
    """Process all pending emails (scheduled task)"""
    db = SessionLocal()
    try:
        result = process_pending_emails(db, limit=100)
        logger.info(f"Processed pending emails: {result}")
        return result
    finally:
        db.close()

@celery_app.task
def retry_failed_email(email_id: int):
    """Manually retry a failed email"""
    db = SessionLocal()
    try:
        email = db.query(OutboundEmail).filter(OutboundEmail.id == email_id).first()
        if not email:
            return {"error": "Email not found"}
        
        from datetime import datetime
        email.next_retry_at = datetime.utcnow()
        email.status = 'pending'
        db.commit()
        
        # Trigger send task
        send_email_task.delay(email_id)
        
        return {"email_id": email_id, "status": "queued"}
    finally:
        db.close()
