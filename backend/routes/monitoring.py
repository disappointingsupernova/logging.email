from fastapi import APIRouter, Depends, Request, Query
from lib.utils.auth_helpers import get_current_admin
from lib.database import get_db
from lib.services.health import check_all_services, get_service_health_history
from lib.services.email import process_pending_emails
from lib.services.audit import log_audit
from models.models import User, OutboundEmail, ServiceHealth
from sqlalchemy import func, desc
from datetime import datetime, timedelta

router = APIRouter()

@router.get("/admin/health")
def get_health_status(admin_uuid: str = Depends(get_current_admin), req: Request = None):
    """Get current health status of all services"""
    db = next(get_db())
    admin = db.query(User).filter(User.uuid == admin_uuid).first()
    
    status = check_all_services()
    
    log_audit(
        user_id=admin.id,
        action="admin_view_health",
        resource_type="health",
        ip_address=req.client.host if req and req.client else None,
        user_agent=req.headers.get("user-agent") if req else None
    )
    
    return status

@router.get("/admin/health/history")
def get_health_history(
    service: str = None,
    hours: int = Query(24, ge=1, le=168),
    admin_uuid: str = Depends(get_current_admin),
    req: Request = None
):
    """Get service health history"""
    db = next(get_db())
    admin = db.query(User).filter(User.uuid == admin_uuid).first()
    
    history = get_service_health_history(service, hours)
    
    log_audit(
        user_id=admin.id,
        action="admin_view_health_history",
        resource_type="health",
        ip_address=req.client.host if req and req.client else None,
        user_agent=req.headers.get("user-agent") if req else None,
        details={"service": service, "hours": hours}
    )
    
    return {
        "service": service,
        "hours": hours,
        "history": [{
            "status": h.status,
            "response_time_ms": h.response_time_ms,
            "error_message": h.error_message,
            "checked_at": h.checked_at
        } for h in history]
    }

@router.get("/admin/emails")
def list_outbound_emails(
    status: str = None,
    email_type: str = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    admin_uuid: str = Depends(get_current_admin),
    req: Request = None
):
    """List outbound emails with pagination"""
    db = next(get_db())
    admin = db.query(User).filter(User.uuid == admin_uuid).first()
    
    query = db.query(OutboundEmail)
    
    if status:
        query = query.filter(OutboundEmail.status == status)
    if email_type:
        query = query.filter(OutboundEmail.email_type == email_type)
    
    total = query.count()
    emails = query.order_by(desc(OutboundEmail.created_at)).offset(
        (page - 1) * per_page
    ).limit(per_page).all()
    
    log_audit(
        user_id=admin.id,
        action="admin_list_emails",
        resource_type="outbound_email",
        ip_address=req.client.host if req and req.client else None,
        user_agent=req.headers.get("user-agent") if req else None,
        details={"status": status, "email_type": email_type, "page": page}
    )
    
    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
        "emails": [{
            "id": e.id,
            "recipient": e.recipient,
            "subject": e.subject,
            "email_type": e.email_type,
            "status": e.status,
            "attempts": e.attempts,
            "max_attempts": e.max_attempts,
            "smtp_code": e.smtp_code,
            "created_at": e.created_at,
            "sent_at": e.sent_at,
            "next_retry_at": e.next_retry_at
        } for e in emails]
    }

@router.get("/admin/emails/{email_id}")
def get_outbound_email(
    email_id: int,
    admin_uuid: str = Depends(get_current_admin),
    req: Request = None
):
    """Get outbound email details"""
    db = next(get_db())
    admin = db.query(User).filter(User.uuid == admin_uuid).first()
    
    email = db.query(OutboundEmail).filter(OutboundEmail.id == email_id).first()
    if not email:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Email not found")
    
    log_audit(
        user_id=admin.id,
        action="admin_view_email",
        resource_type="outbound_email",
        resource_id=str(email_id),
        ip_address=req.client.host if req and req.client else None,
        user_agent=req.headers.get("user-agent") if req else None
    )
    
    return {
        "id": email.id,
        "recipient": email.recipient,
        "subject": email.subject,
        "body_text": email.body_text,
        "body_html": email.body_html,
        "email_type": email.email_type,
        "status": email.status,
        "smtp_response": email.smtp_response,
        "smtp_code": email.smtp_code,
        "attempts": email.attempts,
        "max_attempts": email.max_attempts,
        "next_retry_at": email.next_retry_at,
        "last_attempt_at": email.last_attempt_at,
        "sent_at": email.sent_at,
        "expires_at": email.expires_at,
        "created_at": email.created_at,
        "updated_at": email.updated_at
    }

@router.post("/admin/emails/{email_id}/retry")
def retry_outbound_email(
    email_id: int,
    admin_uuid: str = Depends(get_current_admin),
    req: Request = None
):
    """Manually retry sending an email"""
    db = next(get_db())
    admin = db.query(User).filter(User.uuid == admin_uuid).first()
    
    email = db.query(OutboundEmail).filter(OutboundEmail.id == email_id).first()
    if not email:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Email not found")
    
    if email.status == 'sent':
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Email already sent")
    
    # Reset for immediate retry
    email.next_retry_at = datetime.utcnow()
    email.status = 'pending'
    db.commit()
    
    from lib.services.email import attempt_send
    success = attempt_send(db, email)
    
    log_audit(
        user_id=admin.id,
        action="admin_retry_email",
        resource_type="outbound_email",
        resource_id=str(email_id),
        ip_address=req.client.host if req and req.client else None,
        user_agent=req.headers.get("user-agent") if req else None,
        details={"success": success}
    )
    
    return {"status": "retried", "success": success}

@router.post("/admin/emails/process")
def process_emails(
    limit: int = Query(100, ge=1, le=1000),
    admin_uuid: str = Depends(get_current_admin),
    req: Request = None
):
    """Manually trigger email processing"""
    db = next(get_db())
    admin = db.query(User).filter(User.uuid == admin_uuid).first()
    
    result = process_pending_emails(db, limit)
    
    log_audit(
        user_id=admin.id,
        action="admin_process_emails",
        resource_type="outbound_email",
        ip_address=req.client.host if req and req.client else None,
        user_agent=req.headers.get("user-agent") if req else None,
        details=result
    )
    
    return result

@router.get("/admin/emails/stats")
def get_email_stats(
    hours: int = Query(24, ge=1, le=168),
    admin_uuid: str = Depends(get_current_admin),
    req: Request = None
):
    """Get email statistics"""
    db = next(get_db())
    admin = db.query(User).filter(User.uuid == admin_uuid).first()
    
    since = datetime.utcnow() - timedelta(hours=hours)
    
    total = db.query(func.count(OutboundEmail.id)).filter(
        OutboundEmail.created_at > since
    ).scalar()
    
    sent = db.query(func.count(OutboundEmail.id)).filter(
        OutboundEmail.created_at > since,
        OutboundEmail.status == 'sent'
    ).scalar()
    
    pending = db.query(func.count(OutboundEmail.id)).filter(
        OutboundEmail.status == 'pending'
    ).scalar()
    
    failed = db.query(func.count(OutboundEmail.id)).filter(
        OutboundEmail.status == 'failed'
    ).scalar()
    
    expired = db.query(func.count(OutboundEmail.id)).filter(
        OutboundEmail.status == 'expired'
    ).scalar()
    
    by_type = db.query(
        OutboundEmail.email_type,
        func.count(OutboundEmail.id).label('count')
    ).filter(
        OutboundEmail.created_at > since
    ).group_by(OutboundEmail.email_type).all()
    
    log_audit(
        user_id=admin.id,
        action="admin_view_email_stats",
        resource_type="outbound_email",
        ip_address=req.client.host if req and req.client else None,
        user_agent=req.headers.get("user-agent") if req else None
    )
    
    return {
        "hours": hours,
        "total": total,
        "sent": sent,
        "pending": pending,
        "failed": failed,
        "expired": expired,
        "by_type": {t: c for t, c in by_type}
    }
