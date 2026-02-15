import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from models.models import OutboundEmail
from config import settings
import logging

logger = logging.getLogger(__name__)

def send_smtp(host: str, port: int, user: str, password: str, from_email: str, 
              to_email: str, subject: str, body_text: str = None, body_html: str = None) -> dict:
    """Send email via SMTP"""
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"{settings.smtp_from_name} <{from_email}>"
        msg['To'] = to_email
        
        if body_text:
            msg.attach(MIMEText(body_text, 'plain'))
        if body_html:
            msg.attach(MIMEText(body_html, 'html'))
        
        with smtplib.SMTP(host, port, timeout=30) as server:
            if settings.smtp_use_tls:
                server.starttls()
            if user and password:
                server.login(user, password)
            
            result = server.send_message(msg)
            
        return {"success": True, "code": 250, "response": "Message sent"}
    
    except smtplib.SMTPException as e:
        code = getattr(e, 'smtp_code', None)
        return {"success": False, "code": code, "response": str(e)}
    except Exception as e:
        return {"success": False, "code": None, "response": str(e)}

def send_email(db: Session, recipient: str, subject: str = None, body_text: str = None, 
               body_html: str = None, email_type: str = "notification", 
               user_id: int = None, organization_id: int = None,
               template_id: int = None, template_data: dict = None) -> OutboundEmail:
    """Queue email for sending with retry logic"""
    
    # If template_data provided, render from template
    if template_data:
        from lib.services.templates import render_email
        rendered = render_email(db, email_type, template_data, template_id)
        subject = rendered["subject"]
        body_text = rendered["body_text"]
        body_html = rendered["body_html"]
    
    email = OutboundEmail(
        recipient=recipient,
        subject=subject,
        body_text=body_text,
        body_html=body_html,
        email_type=email_type,
        user_id=user_id,
        organization_id=organization_id,
        template_id=template_id,
        template_data=template_data,
        max_attempts=settings.email_max_attempts,
        expires_at=datetime.utcnow() + timedelta(hours=settings.email_expiry_hours),
        next_retry_at=datetime.utcnow()
    )
    
    db.add(email)
    db.commit()
    db.refresh(email)
    
    logger.info(f"Queued email {email.id} to {recipient}: {subject}")
    
    # Trigger async task
    from tasks.email_tasks import send_email_task
    send_email_task.delay(email.id)
    
    return email

def attempt_send(db: Session, email: OutboundEmail) -> bool:
    """Attempt to send email with failover"""
    
    if email.attempts >= email.max_attempts:
        email.status = 'expired'
        db.commit()
        logger.warning(f"Email {email.id} expired after {email.attempts} attempts")
        return False
    
    if datetime.utcnow() < email.next_retry_at:
        return False
    
    email.attempts += 1
    email.last_attempt_at = datetime.utcnow()
    
    # Try primary SMTP
    result = send_smtp(
        settings.smtp_host,
        settings.smtp_port,
        settings.smtp_user,
        settings.smtp_password,
        settings.smtp_from_email,
        email.recipient,
        email.subject,
        email.body_text,
        email.body_html
    )
    
    # Try backup SMTP if primary fails
    if not result["success"] and settings.smtp_backup_host:
        logger.warning(f"Primary SMTP failed for email {email.id}, trying backup")
        result = send_smtp(
            settings.smtp_backup_host,
            settings.smtp_backup_port,
            settings.smtp_backup_user,
            settings.smtp_backup_password,
            settings.smtp_backup_from_email or settings.smtp_from_email,
            email.recipient,
            email.subject,
            email.body_text,
            email.body_html
        )
    
    email.smtp_code = result["code"]
    email.smtp_response = result["response"]
    
    if result["success"]:
        email.status = 'sent'
        email.sent_at = datetime.utcnow()
        logger.info(f"Email {email.id} sent successfully")
    else:
        email.status = 'failed'
        # Exponential backoff: 60s, 120s, 240s, 480s, 960s
        delay = settings.email_retry_base_delay * (2 ** (email.attempts - 1))
        email.next_retry_at = datetime.utcnow() + timedelta(seconds=delay)
        logger.error(f"Email {email.id} failed (attempt {email.attempts}): {result['response']}")
    
    db.commit()
    return result["success"]

def process_pending_emails(db: Session, limit: int = 100) -> dict:
    """Process pending emails (call from worker/cron)"""
    
    pending = db.query(OutboundEmail).filter(
        OutboundEmail.status.in_(['pending', 'failed']),
        OutboundEmail.next_retry_at <= datetime.utcnow(),
        OutboundEmail.expires_at > datetime.utcnow(),
        OutboundEmail.attempts < OutboundEmail.max_attempts
    ).limit(limit).all()
    
    sent = 0
    failed = 0
    
    for email in pending:
        if attempt_send(db, email):
            sent += 1
        else:
            failed += 1
    
    logger.info(f"Processed {len(pending)} emails: {sent} sent, {failed} failed")
    
    return {"processed": len(pending), "sent": sent, "failed": failed}

def send_notification(db: Session, user_id: int, template_data: dict, template_id: int = None):
    """Send notification email to user using template"""
    from models.models import User
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        return send_email(
            db, user.email, email_type="notification", 
            user_id=user_id, template_id=template_id, template_data=template_data
        )

def send_alert(db: Session, recipient: str, template_data: dict, template_id: int = None):
    """Send alert email using template"""
    return send_email(
        db, recipient, email_type="alert",
        template_id=template_id, template_data=template_data
    )
