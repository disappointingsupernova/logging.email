from fastapi import APIRouter, Depends, Request, HTTPException, Query
from pydantic import BaseModel
from lib.utils.auth_helpers import get_current_admin
from lib.utils.auth import hash_password
from lib.database import get_db
from lib.services.audit import log_audit
from models.models import User, ApiToken
from sqlalchemy import func, desc
from datetime import datetime
import secrets
import hashlib
from config import settings

router = APIRouter()

class TokenCreate(BaseModel):
    description: str
    scope: str  # policy, worker, admin

def hash_api_token(token: str) -> str:
    """Hash API token with salt"""
    return hashlib.sha256(f"{token}{settings.api_token_salt}".encode()).hexdigest()

@router.get("/admin/tokens")
def list_tokens(
    scope: str = None,
    is_active: bool = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    admin_uuid: str = Depends(get_current_admin),
    req: Request = None
):
    """List API tokens with pagination"""
    db = next(get_db())
    admin = db.query(User).filter(User.uuid == admin_uuid).first()
    
    query = db.query(ApiToken)
    
    if scope:
        query = query.filter(ApiToken.scope == scope)
    if is_active is not None:
        query = query.filter(ApiToken.is_active == is_active)
    
    total = query.count()
    tokens = query.order_by(desc(ApiToken.created_at)).offset(
        (page - 1) * per_page
    ).limit(per_page).all()
    
    log_audit(
        user_id=admin.id,
        action="admin_list_tokens",
        resource_type="api_token",
        ip_address=req.client.host if req and req.client else None,
        user_agent=req.headers.get("user-agent") if req else None,
        details={"scope": scope, "is_active": is_active, "page": page}
    )
    
    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
        "tokens": [{
            "id": t.id,
            "description": t.description,
            "scope": t.scope,
            "is_active": t.is_active,
            "created_at": t.created_at,
            "last_used_at": t.last_used_at
        } for t in tokens]
    }

@router.get("/admin/tokens/{token_id}")
def get_token(
    token_id: int,
    admin_uuid: str = Depends(get_current_admin),
    req: Request = None
):
    """Get token details"""
    db = next(get_db())
    admin = db.query(User).filter(User.uuid == admin_uuid).first()
    
    token = db.query(ApiToken).filter(ApiToken.id == token_id).first()
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")
    
    log_audit(
        user_id=admin.id,
        action="admin_view_token",
        resource_type="api_token",
        resource_id=str(token_id),
        ip_address=req.client.host if req and req.client else None,
        user_agent=req.headers.get("user-agent") if req else None
    )
    
    return {
        "id": token.id,
        "description": token.description,
        "scope": token.scope,
        "is_active": token.is_active,
        "created_at": token.created_at,
        "last_used_at": token.last_used_at,
        "token_hash": token.token_hash[:16] + "..."  # Show partial hash
    }

@router.post("/admin/tokens")
def create_token(
    data: TokenCreate,
    admin_uuid: str = Depends(get_current_admin),
    req: Request = None
):
    """Generate new API token"""
    db = next(get_db())
    admin = db.query(User).filter(User.uuid == admin_uuid).first()
    
    if data.scope not in ['policy', 'worker', 'admin']:
        raise HTTPException(status_code=400, detail="Invalid scope")
    
    # Generate token
    token = secrets.token_urlsafe(32)
    token_hash = hash_api_token(token)
    
    # Store in database
    api_token = ApiToken(
        token_hash=token_hash,
        description=data.description,
        scope=data.scope,
        is_active=True
    )
    db.add(api_token)
    db.commit()
    db.refresh(api_token)
    
    log_audit(
        user_id=admin.id,
        action="admin_create_token",
        resource_type="api_token",
        resource_id=str(api_token.id),
        ip_address=req.client.host if req and req.client else None,
        user_agent=req.headers.get("user-agent") if req else None,
        details={"description": data.description, "scope": data.scope}
    )
    
    return {
        "id": api_token.id,
        "token": token,  # Only shown once!
        "description": data.description,
        "scope": data.scope,
        "warning": "Save this token now. It will not be shown again."
    }

@router.patch("/admin/tokens/{token_id}/deactivate")
def deactivate_token(
    token_id: int,
    admin_uuid: str = Depends(get_current_admin),
    req: Request = None
):
    """Deactivate API token"""
    db = next(get_db())
    admin = db.query(User).filter(User.uuid == admin_uuid).first()
    
    token = db.query(ApiToken).filter(ApiToken.id == token_id).first()
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")
    
    token.is_active = False
    db.commit()
    
    log_audit(
        user_id=admin.id,
        action="admin_deactivate_token",
        resource_type="api_token",
        resource_id=str(token_id),
        ip_address=req.client.host if req and req.client else None,
        user_agent=req.headers.get("user-agent") if req else None,
        details={"description": token.description}
    )
    
    return {"status": "deactivated"}

@router.patch("/admin/tokens/{token_id}/activate")
def activate_token(
    token_id: int,
    admin_uuid: str = Depends(get_current_admin),
    req: Request = None
):
    """Activate API token"""
    db = next(get_db())
    admin = db.query(User).filter(User.uuid == admin_uuid).first()
    
    token = db.query(ApiToken).filter(ApiToken.id == token_id).first()
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")
    
    token.is_active = True
    db.commit()
    
    log_audit(
        user_id=admin.id,
        action="admin_activate_token",
        resource_type="api_token",
        resource_id=str(token_id),
        ip_address=req.client.host if req and req.client else None,
        user_agent=req.headers.get("user-agent") if req else None,
        details={"description": token.description}
    )
    
    return {"status": "activated"}

@router.delete("/admin/tokens/{token_id}")
def delete_token(
    token_id: int,
    admin_uuid: str = Depends(get_current_admin),
    req: Request = None
):
    """Delete API token"""
    db = next(get_db())
    admin = db.query(User).filter(User.uuid == admin_uuid).first()
    
    token = db.query(ApiToken).filter(ApiToken.id == token_id).first()
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")
    
    description = token.description
    db.delete(token)
    db.commit()
    
    log_audit(
        user_id=admin.id,
        action="admin_delete_token",
        resource_type="api_token",
        resource_id=str(token_id),
        ip_address=req.client.host if req and req.client else None,
        user_agent=req.headers.get("user-agent") if req else None,
        details={"description": description}
    )
    
    return {"status": "deleted"}

@router.get("/admin/tokens/{token_id}/usage")
def get_token_usage(
    token_id: int,
    hours: int = Query(24, ge=1, le=168),
    admin_uuid: str = Depends(get_current_admin),
    req: Request = None
):
    """Get token usage statistics from audit log"""
    db = next(get_db())
    admin = db.query(User).filter(User.uuid == admin_uuid).first()
    
    token = db.query(ApiToken).filter(ApiToken.id == token_id).first()
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")
    
    # Note: This is a simplified version. In production, you'd track token usage separately
    # For now, we show when it was last used
    
    log_audit(
        user_id=admin.id,
        action="admin_view_token_usage",
        resource_type="api_token",
        resource_id=str(token_id),
        ip_address=req.client.host if req and req.client else None,
        user_agent=req.headers.get("user-agent") if req else None
    )
    
    return {
        "token_id": token_id,
        "description": token.description,
        "scope": token.scope,
        "last_used_at": token.last_used_at,
        "is_active": token.is_active,
        "note": "Detailed usage tracking requires additional logging implementation"
    }
