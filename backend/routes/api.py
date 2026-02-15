from fastapi import APIRouter, HTTPException, Depends, Header, Request, Response
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from lib.database import get_db
from lib.utils.auth import hash_password, verify_password, create_access_token
from lib.utils.auth_helpers import get_current_user
from lib.services.audit import log_audit
from lib.services.session import create_session, refresh_access_token, revoke_session, revoke_all_sessions, load_session, REFRESH_TOKEN_LIFETIME
from lib.utils.cache import cache_get, cache_set, invalidate_user_cache, invalidate_address_cache
from models.models import User, Organization, EmailAddress, Message, Attachment
from jose import jwt, JWTError
from config import settings
import uuid

router = APIRouter()

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    device_id: str = None
    client_id: str = "web"

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

@router.post("/auth/register", response_model=TokenResponse)
def register(request: RegisterRequest, req: Request):
    """Register new user with auto-created organization"""
    db = next(get_db())
    
    if db.query(User).filter(User.email == request.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create organization
    org = Organization(
        uuid=str(uuid.uuid4()),
        name=request.email.split('@')[0] + "'s Organization",
        tier='free'
    )
    db.add(org)
    db.flush()
    
    # Create user as owner
    user = User(
        organization_id=org.id,
        uuid=str(uuid.uuid4()),
        email=request.email,
        password_hash=hash_password(request.password),
        role='owner'
    )
    db.add(user)
    db.flush()
    
    # Create default email address
    address = EmailAddress(
        organization_id=org.id,
        address=f"{org.uuid}@{settings.domain}",
        is_active=True
    )
    db.add(address)
    db.commit()
    
    log_audit(
        user_id=user.id,
        action="register",
        resource_type="user",
        resource_id=user.uuid,
        ip_address=req.client.host if req.client else None,
        user_agent=req.headers.get("user-agent"),
        details={"organization_id": org.id}
    )
    
    token = create_access_token({"sub": user.uuid})
    return TokenResponse(access_token=token)

@router.post("/auth/login", response_model=TokenResponse)
def login(request: LoginRequest, req: Request, response: Response):
    """Authenticate user and create session"""
    db = next(get_db())
    user = db.query(User).filter(User.email == request.email).first()
    
    if not user or not verify_password(request.password, user.password_hash):
        log_audit(
            user_id=None,
            action="login_failed",
            resource_type="user",
            ip_address=req.client.host if req.client else None,
            user_agent=req.headers.get("user-agent"),
            details={"email": request.email}
        )
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    request_data = {
        "ip": req.client.host if req.client else None,
        "user_agent": req.headers.get("user-agent"),
        "device_id": request.device_id,
        "client_id": request.client_id
    }
    
    session, refresh_token = create_session(db, user.id, request_data)
    
    log_audit(
        user_id=user.id,
        action="login",
        resource_type="user",
        resource_id=user.uuid,
        ip_address=req.client.host if req.client else None,
        user_agent=req.headers.get("user-agent")
    )
    
    access_token = create_access_token({"sub": user.uuid, "sid": session.id})
    
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=int(REFRESH_TOKEN_LIFETIME.total_seconds())
    )
    
    return TokenResponse(access_token=access_token)

@router.get("/messages")
def list_messages(user_uuid: str = Depends(get_current_user), req: Request = None):
    """List messages for user's organization"""
    db = next(get_db())
    user = db.query(User).filter(User.uuid == user_uuid).first()
    
    messages = db.query(
        Message.id,
        Message.from_address,
        Message.subject,
        Message.received_at,
        Message.has_attachments,
        EmailAddress.address.label('recipient')
    ).join(
        EmailAddress, Message.email_address_id == EmailAddress.id
    ).filter(
        EmailAddress.organization_id == user.organization_id,
        Message.is_processed == True
    ).order_by(
        Message.received_at.desc()
    ).limit(100).all()
    
    log_audit(
        user_id=user.id,
        action="list_messages",
        resource_type="message",
        ip_address=req.client.host if req and req.client else None,
        user_agent=req.headers.get("user-agent") if req else None
    )
    
    return {"messages": [dict(m._mapping) for m in messages]}

@router.get("/messages/{message_id}")
def get_message(message_id: int, user_uuid: str = Depends(get_current_user), req: Request = None):
    """Get full message details"""
    db = next(get_db())
    user = db.query(User).filter(User.uuid == user_uuid).first()
    
    message = db.query(Message, EmailAddress.address.label('recipient')).join(
        EmailAddress, Message.email_address_id == EmailAddress.id
    ).filter(
        Message.id == message_id,
        EmailAddress.organization_id == user.organization_id
    ).first()
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    msg_dict = {**message[0].__dict__, 'recipient': message[1]}
    msg_dict.pop('_sa_instance_state', None)
    
    # Get email content from MongoDB
    from lib.services.mongodb import get_email_content
    content = get_email_content(message_id)
    if content:
        msg_dict['text_body'] = content.get('text_body')
        msg_dict['sanitised_html'] = content.get('sanitised_html')
    
    # Get attachments
    attachments = db.query(Attachment).filter(Attachment.message_id == message_id).all()
    msg_dict['attachments'] = [{"id": a.id, "filename": a.filename, "content_type": a.content_type, "size_bytes": a.size_bytes, "mongodb_id": a.mongodb_id} for a in attachments]
    
    log_audit(
        user_id=user.id,
        action="view_message",
        resource_type="message",
        resource_id=str(message_id),
        ip_address=req.client.host if req and req.client else None,
        user_agent=req.headers.get("user-agent") if req else None
    )
    
    return msg_dict

@router.get("/addresses")
def list_addresses(user_uuid: str = Depends(get_current_user), req: Request = None):
    """List organization's email addresses"""
    db = next(get_db())
    user = db.query(User).filter(User.uuid == user_uuid).first()
    cache_key = f"addresses:{user.id}"
    
    cached = cache_get(cache_key)
    if cached:
        return {"addresses": cached}
    
    addresses = db.query(EmailAddress).filter(
        EmailAddress.organization_id == user.organization_id
    ).order_by(EmailAddress.created_at.desc()).all()
    
    result = [{"id": a.id, "address": a.address, "is_active": a.is_active, "created_at": a.created_at} for a in addresses]
    cache_set(cache_key, result, ttl=300)
    
    log_audit(
        user_id=user.id,
        action="list_addresses",
        resource_type="email_address",
        ip_address=req.client.host if req and req.client else None,
        user_agent=req.headers.get("user-agent") if req else None
    )
    
    return {"addresses": result}

@router.post("/addresses")
def create_address(address: str, user_uuid: str = Depends(get_current_user), req: Request = None):
    """Create new email address for organization"""
    db = next(get_db())
    user = db.query(User).filter(User.uuid == user_uuid).first()
    
    from lib.services.features import enforce_address_limit
    enforce_address_limit(db, user.organization_id)
    
    new_address = EmailAddress(
        organization_id=user.organization_id,
        address=address,
        is_active=True
    )
    db.add(new_address)
    db.commit()
    
    invalidate_user_cache(user.id)
    
    log_audit(
        user_id=user.id,
        action="create_address",
        resource_type="email_address",
        resource_id=str(new_address.id),
        ip_address=req.client.host if req and req.client else None,
        user_agent=req.headers.get("user-agent") if req else None,
        details={"address": address}
    )
    
    return {"id": new_address.id, "address": address}

@router.delete("/addresses/{address_id}")
def delete_address(address_id: int, user_uuid: str = Depends(get_current_user), req: Request = None):
    """Delete email address"""
    db = next(get_db())
    user = db.query(User).filter(User.uuid == user_uuid).first()
    
    address = db.query(EmailAddress).filter(
        EmailAddress.id == address_id,
        EmailAddress.organization_id == user.organization_id
    ).first()
    
    if not address:
        raise HTTPException(status_code=404, detail="Address not found")
    
    address_str = address.address
    db.delete(address)
    db.commit()
    
    invalidate_user_cache(user.id)
    invalidate_address_cache(address_str)
    
    log_audit(
        user_id=user.id,
        action="delete_address",
        resource_type="email_address",
        resource_id=str(address_id),
        ip_address=req.client.host if req and req.client else None,
        user_agent=req.headers.get("user-agent") if req else None,
        details={"address": address_str}
    )
    
    return {"status": "deleted"}

@router.get("/audit")
def get_audit_log(user_uuid: str = Depends(get_current_user), req: Request = None):
    """Get user's audit log"""
    db = next(get_db())
    user = db.query(User).filter(User.uuid == user_uuid).first()
    
    from models.models import AuditLog
    logs = db.query(AuditLog).filter(
        AuditLog.user_id == user.id
    ).order_by(AuditLog.created_at.desc()).limit(100).all()
    
    log_audit(
        user_id=user.id,
        action="view_audit_log",
        resource_type="audit",
        ip_address=req.client.host if req and req.client else None,
        user_agent=req.headers.get("user-agent") if req else None
    )
    
    return {"audit_log": [{"action": l.action, "resource_type": l.resource_type, "resource_id": l.resource_id, "ip_address": l.ip_address, "created_at": l.created_at, "details": l.details} for l in logs]}

@router.get("/usage")
def get_usage(user_uuid: str = Depends(get_current_user), req: Request = None, org_uuid: str = None):
    """Get organization usage and limits (admins can view any org)"""
    db = next(get_db())
    user = db.query(User).filter(User.uuid == user_uuid).first()
    
    if org_uuid and user.is_platform_admin:
        org = db.query(Organization).filter(Organization.uuid == org_uuid).first()
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")
        org_id = org.id
    else:
        org_id = user.organization_id
    
    from lib.services.features import get_tier_limits, get_current_usage
    limits = get_tier_limits(db, org_id)
    usage = get_current_usage(db, org_id)
    
    log_audit(
        user_id=user.id,
        action="view_usage",
        resource_type="usage",
        ip_address=req.client.host if req and req.client else None,
        user_agent=req.headers.get("user-agent") if req else None,
        details={"org_id": org_id} if org_uuid else None
    )
    
    return {
        "limits": {
            "max_addresses": limits.max_addresses,
            "retention_days": limits.retention_days,
            "rate_limit_per_hour": limits.rate_limit_per_hour,
            "max_storage_mb": limits.max_storage_mb,
            "api_enabled": limits.api_enabled,
            "webhook_enabled": limits.webhook_enabled,
            "priority_support": limits.priority_support
        },
        "usage": usage
    }

@router.post("/auth/refresh", response_model=TokenResponse)
def refresh(req: Request, response: Response, refresh_token: str = None):
    """Refresh access token"""
    if not refresh_token:
        refresh_token = req.cookies.get("refresh_token")
    
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token required")
    
    db = next(get_db())
    request_data = {
        "ip": req.client.host if req.client else None,
        "user_agent": req.headers.get("user-agent"),
        "device_id": req.headers.get("x-device-id"),
        "client_id": req.headers.get("x-client-id", "web")
    }
    
    session, new_refresh_token = refresh_access_token(db, refresh_token, request_data)
    
    user = db.query(User).filter(User.id == session.user_id).first()
    access_token = create_access_token({"sub": user.uuid, "sid": session.id})
    
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=int(REFRESH_TOKEN_LIFETIME.total_seconds())
    )
    
    return TokenResponse(access_token=access_token)

@router.post("/auth/logout")
def logout(user_uuid: str = Depends(get_current_user), req: Request = None, response: Response = None):
    """Logout current session"""
    db = next(get_db())
    
    try:
        auth_header = req.headers.get("authorization")
        token = auth_header.split()[1]
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        session_id = payload.get("sid")
        
        if session_id:
            session = load_session(db, session_id)
            if session:
                revoke_session(db, session, "User logout")
    except:
        pass
    
    response.delete_cookie("refresh_token")
    
    log_audit(
        user_id=db.query(User).filter(User.uuid == user_uuid).first().id,
        action="logout",
        resource_type="session",
        ip_address=req.client.host if req and req.client else None,
        user_agent=req.headers.get("user-agent") if req else None
    )
    
    return {"status": "logged_out"}

@router.post("/auth/logout-all")
def logout_all(user_uuid: str = Depends(get_current_user), req: Request = None, response: Response = None):
    """Logout all sessions"""
    db = next(get_db())
    user = db.query(User).filter(User.uuid == user_uuid).first()
    
    revoke_all_sessions(db, user.id)
    response.delete_cookie("refresh_token")
    
    log_audit(
        user_id=user.id,
        action="logout_all",
        resource_type="session",
        ip_address=req.client.host if req and req.client else None,
        user_agent=req.headers.get("user-agent") if req else None
    )
    
    return {"status": "all_sessions_revoked"}

@router.get("/auth/sessions")
def list_sessions(user_uuid: str = Depends(get_current_user), req: Request = None):
    """List active sessions"""
    db = next(get_db())
    user = db.query(User).filter(User.uuid == user_uuid).first()
    
    from models.models import Session as SessionModel
    sessions = db.query(SessionModel).filter(
        SessionModel.user_id == user.id,
        SessionModel.revoked_at == None,
        SessionModel.expires_at > func.now()
    ).order_by(SessionModel.last_seen_at.desc()).all()
    
    return {"sessions": [{
        "id": s.id,
        "created_at": s.created_at,
        "last_seen_at": s.last_seen_at,
        "client_id": s.client_id,
        "os_family": s.os_family,
        "browser_family": s.browser_family,
        "last_ip": s.last_ip,
        "last_country": s.last_country
    } for s in sessions]}
