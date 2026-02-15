from fastapi import Header, HTTPException, Request
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from lib.database import get_db
from lib.services.session import authenticate_request
from models.models import User
from config import settings

def get_current_user(authorization: str = Header(...), req: Request = None):
    """Extract and verify JWT token with session validation"""
    try:
        scheme, token = authorization.split()
        if scheme.lower() != 'bearer':
            raise HTTPException(status_code=401, detail="Invalid authentication scheme")
        
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        user_uuid = payload.get("sub")
        session_id = payload.get("sid")
        
        if not user_uuid or not session_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        db = next(get_db())
        request_data = {
            "ip": req.client.host if req and req.client else None,
            "user_agent": req.headers.get("user-agent") if req else None,
            "device_id": req.headers.get("x-device-id") if req else None,
            "client_id": req.headers.get("x-client-id") if req else "web"
        }
        
        authenticate_request(db, session_id, request_data)
        
        return user_uuid
    except (ValueError, JWTError):
        raise HTTPException(status_code=401, detail="Invalid token")

def get_current_admin(authorization: str = Header(...), req: Request = None):
    """Extract and verify JWT token for platform admin"""
    user_uuid = get_current_user(authorization, req)
    db = next(get_db())
    user = db.query(User).filter(User.uuid == user_uuid).first()
    
    if not user or not user.is_platform_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return user_uuid

def get_user_id(user_uuid: str, db: Session) -> int:
    """Get user ID from UUID"""
    user = db.query(User).filter(User.uuid == user_uuid).first()
    return user.id if user else None
