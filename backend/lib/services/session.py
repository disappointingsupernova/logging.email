import hashlib
import secrets
import uuid
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException
from models.models import Session as SessionModel, RefreshToken, SecurityEvent, User
from lib.utils.cache import cache_get, cache_set, cache_delete
from user_agents import parse
from config import settings

# Constants
MAX_RISK = 100
ROTATE_REFRESH_RISK = 40
REAUTH_RISK = 70
SESSION_IDLE_LIMIT = timedelta(days=settings.session_idle_limit_days)
SESSION_ABSOLUTE_LIMIT = timedelta(days=settings.session_absolute_limit_days)
ACCESS_TOKEN_LIFETIME = timedelta(minutes=settings.access_token_lifetime_minutes)
REFRESH_TOKEN_LIFETIME = timedelta(days=settings.refresh_token_lifetime_days)

def hash_token(token: str) -> str:
    """Hash token for storage"""
    return hashlib.sha256(token.encode()).hexdigest()

def parse_user_agent(ua_string: str) -> dict:
    """Parse user agent string"""
    try:
        ua = parse(ua_string)
        return {
            "os_family": ua.os.family[:63] if ua.os.family else None,
            "browser_family": ua.browser.family[:63] if ua.browser.family else None,
            "hash": hash_token(ua_string)[:64]
        }
    except:
        return {"os_family": None, "browser_family": None, "hash": hash_token(ua_string)[:64]}

def get_geo_info(ip: str) -> dict:
    """Get geo info from IP (stub for MaxMind integration)"""
    # TODO: Integrate MaxMind GeoIP2
    return {"asn": None, "country": None}

def calculate_risk(session: SessionModel, request_data: dict) -> int:
    """Calculate risk score for request"""
    risk = 0
    
    # Device identity
    if request_data.get("device_id") and request_data["device_id"] != session.device_id:
        risk += 40
    
    # Client type
    if request_data.get("client_id") and request_data["client_id"] != session.client_id:
        risk += 30
    
    # User-Agent change
    if request_data.get("user_agent_hash") and request_data["user_agent_hash"] != session.user_agent_hash:
        if request_data.get("browser_family") == session.browser_family:
            risk += 5  # Browser auto-update
        else:
            risk += 20
    
    # IP change
    if request_data.get("ip") and request_data["ip"] != session.last_ip:
        if request_data.get("asn") and request_data["asn"] == session.last_asn:
            risk += 2  # Same ISP (WiFi ↔ 4G)
        elif request_data.get("country") and request_data["country"] == session.last_country:
            risk += 8  # Same country
        else:
            risk += 25  # Geo jump
    
    return risk

def create_session(db: Session, user_id: int, request_data: dict) -> tuple:
    """Create new session and refresh token"""
    session_id = str(uuid.uuid4())
    ua_info = parse_user_agent(request_data.get("user_agent", ""))
    geo_info = get_geo_info(request_data.get("ip", ""))
    
    session = SessionModel(
        id=session_id,
        user_id=user_id,
        expires_at=datetime.utcnow() + SESSION_ABSOLUTE_LIMIT,
        device_id=request_data.get("device_id"),
        client_id=request_data.get("client_id", "web"),
        user_agent_hash=ua_info["hash"],
        os_family=ua_info["os_family"],
        browser_family=ua_info["browser_family"],
        last_ip=request_data.get("ip"),
        last_asn=geo_info["asn"],
        last_country=geo_info["country"],
        risk_score=0
    )
    db.add(session)
    
    refresh_token = secrets.token_urlsafe(32)
    refresh_token_record = RefreshToken(
        id=str(uuid.uuid4()),
        session_id=session_id,
        token_hash=hash_token(refresh_token),
        expires_at=datetime.utcnow() + REFRESH_TOKEN_LIFETIME
    )
    db.add(refresh_token_record)
    
    log_security_event(db, user_id, session_id, "session_created", request_data)
    
    db.commit()
    cache_session(session)
    
    return session, refresh_token

def load_session(db: Session, session_id: str) -> SessionModel:
    """Load session from cache or DB"""
    cache_key = f"session:{session_id}"
    cached = cache_get(cache_key)
    
    if cached:
        return cached
    
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if session and not session.revoked_at and session.expires_at > datetime.utcnow():
        cache_session(session)
    
    return session

def cache_session(session: SessionModel):
    """Cache session in Redis"""
    ttl = int((session.expires_at - datetime.utcnow()).total_seconds())
    if ttl > 0:
        cache_set(f"session:{session.id}", session, ttl=ttl)

def authenticate_request(db: Session, session_id: str, request_data: dict) -> SessionModel:
    """Authenticate request and update session"""
    session = load_session(db, session_id)
    
    if not session or session.revoked_at:
        raise HTTPException(status_code=401, detail="Session invalid")
    
    if session.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Session expired")
    
    risk = calculate_risk(session, request_data)
    session.risk_score += risk
    session.last_seen_at = datetime.utcnow()
    
    if session.risk_score >= REAUTH_RISK:
        revoke_session(db, session, "High risk detected")
        log_security_event(db, session.user_id, session.id, "session_revoked_risk", request_data)
        raise HTTPException(status_code=401, detail="Reauthentication required")
    
    # Update session context
    if request_data.get("ip"):
        session.last_ip = request_data["ip"]
        geo = get_geo_info(request_data["ip"])
        session.last_asn = geo["asn"]
        session.last_country = geo["country"]
    
    db.commit()
    cache_session(session)
    
    return session

def refresh_access_token(db: Session, refresh_token: str, request_data: dict) -> tuple:
    """Refresh access token with rotation"""
    token_hash = hash_token(refresh_token)
    token_record = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
    
    if not token_record:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
    session = load_session(db, token_record.session_id)
    
    if not session or session.revoked_at:
        raise HTTPException(status_code=401, detail="Session invalid")
    
    # Reuse detection
    if token_record.revoked_at:
        revoke_session(db, session, "Refresh token reuse detected")
        log_security_event(db, session.user_id, session.id, "token_reuse_detected", request_data)
        raise HTTPException(status_code=401, detail="Refresh token reuse detected")
    
    if token_record.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Refresh token expired")
    
    # Calculate risk
    risk = calculate_risk(session, request_data)
    
    if risk >= REAUTH_RISK:
        revoke_session(db, session, "Suspicious activity")
        log_security_event(db, session.user_id, session.id, "session_revoked_suspicious", request_data)
        raise HTTPException(status_code=401, detail="Suspicious activity detected")
    
    # Always rotate refresh token
    token_record.revoked_at = datetime.utcnow()
    
    new_refresh_token = secrets.token_urlsafe(32)
    new_token_record = RefreshToken(
        id=str(uuid.uuid4()),
        session_id=session.id,
        token_hash=hash_token(new_refresh_token),
        expires_at=datetime.utcnow() + REFRESH_TOKEN_LIFETIME
    )
    token_record.replaced_by = new_token_record.id
    db.add(new_token_record)
    
    # Update session
    session.last_seen_at = datetime.utcnow()
    session.risk_score += risk
    
    if request_data.get("ip"):
        session.last_ip = request_data["ip"]
        geo = get_geo_info(request_data["ip"])
        session.last_asn = geo["asn"]
        session.last_country = geo["country"]
    
    db.commit()
    cache_session(session)
    
    return session, new_refresh_token

def revoke_session(db: Session, session: SessionModel, reason: str = None):
    """Revoke session and all refresh tokens"""
    session.revoked_at = datetime.utcnow()
    
    db.query(RefreshToken).filter(
        RefreshToken.session_id == session.id,
        RefreshToken.revoked_at == None
    ).update({"revoked_at": datetime.utcnow()})
    
    db.commit()
    cache_delete(f"session:{session.id}")

def revoke_all_sessions(db: Session, user_id: int):
    """Revoke all sessions for user"""
    sessions = db.query(SessionModel).filter(
        SessionModel.user_id == user_id,
        SessionModel.revoked_at == None
    ).all()
    
    for session in sessions:
        revoke_session(db, session, "Logout all")
    
    log_security_event(db, user_id, None, "logout_all", {})

def log_security_event(db: Session, user_id: int, session_id: str, event_type: str, request_data: dict):
    """Log security event"""
    event = SecurityEvent(
        user_id=user_id,
        session_id=session_id,
        event_type=event_type,
        ip_address=request_data.get("ip"),
        user_agent=request_data.get("user_agent"),
        details=request_data.get("details")
    )
    db.add(event)
    db.commit()
