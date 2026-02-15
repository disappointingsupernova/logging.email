from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from sqlalchemy import func
from lib.database import get_db
from lib.utils.auth_helpers import get_current_admin
from lib.services.audit import log_audit
from lib.services.session import revoke_all_sessions
from lib.utils.cache import invalidate_user_cache, invalidate_tier_cache, cache_delete_pattern
from models.models import User, Organization, EmailAddress, Message, Subscription, AuditLog, TierLimit, RefreshToken

router = APIRouter()

@router.get("/admin/users")
def list_all_users(admin_uuid: str = Depends(get_current_admin), req: Request = None):
    """List all users (admin only)"""
    db = next(get_db())
    admin = db.query(User).filter(User.uuid == admin_uuid).first()
    
    users = db.query(
        User.id,
        User.uuid,
        User.email,
        User.role,
        User.created_at,
        Organization.tier
    ).join(Organization).order_by(User.created_at.desc()).all()
    
    result = []
    for u in users:
        address_count = db.query(func.count(EmailAddress.id)).filter(
            EmailAddress.organization_id == u.id
        ).scalar()
        
        message_count = db.query(func.count(Message.id)).join(
            EmailAddress
        ).filter(EmailAddress.organization_id == u.id).scalar()
        
        result.append({
            "id": u.id,
            "uuid": u.uuid,
            "email": u.email,
            "tier": u.tier,
            "role": u.role,
            "created_at": u.created_at,
            "address_count": address_count,
            "message_count": message_count
        })
    
    log_audit(
        user_id=admin.id,
        action="admin_list_users",
        resource_type="user",
        ip_address=req.client.host if req and req.client else None,
        user_agent=req.headers.get("user-agent") if req else None
    )
    
    return {"users": result}

@router.get("/admin/users/{user_uuid}")
def get_user_details(user_uuid: str, admin_uuid: str = Depends(get_current_admin), req: Request = None):
    """Get user details (admin only)"""
    db = next(get_db())
    admin = db.query(User).filter(User.uuid == admin_uuid).first()
    
    user = db.query(User, Organization.tier, Organization.stripe_customer_id).join(
        Organization
    ).filter(User.uuid == user_uuid).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    subscription = db.query(Subscription).filter(
        Subscription.organization_id == user[0].organization_id,
        Subscription.status == 'active'
    ).first()
    
    addresses = db.query(EmailAddress).filter(
        EmailAddress.organization_id == user[0].organization_id
    ).all()
    
    result = {
        **user[0].__dict__,
        "tier": user[1],
        "stripe_customer_id": user[2],
        "subscription_id": subscription.stripe_subscription_id if subscription else None,
        "subscription_status": subscription.status if subscription else None,
        "addresses": [{"id": a.id, "address": a.address, "is_active": a.is_active, "created_at": a.created_at} for a in addresses]
    }
    result.pop('_sa_instance_state', None)
    result.pop('password_hash', None)
    
    log_audit(
        user_id=admin.id,
        action="admin_view_user",
        resource_type="user",
        resource_id=user_uuid,
        ip_address=req.client.host if req and req.client else None,
        user_agent=req.headers.get("user-agent") if req else None
    )
    
    return result

@router.patch("/admin/organizations/{org_uuid}/tier")
def update_org_tier(org_uuid: str, tier: str, admin_uuid: str = Depends(get_current_admin), req: Request = None):
    """Update organization tier (admin only)"""
    db = next(get_db())
    admin = db.query(User).filter(User.uuid == admin_uuid).first()
    
    if not db.query(TierLimit).filter(TierLimit.tier == tier).first():
        raise HTTPException(status_code=400, detail="Invalid tier")
    
    org = db.query(Organization).filter(Organization.uuid == org_uuid).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    org.tier = tier
    db.commit()
    
    invalidate_tier_cache(org.id)
    
    log_audit(
        user_id=admin.id,
        action="admin_update_tier",
        resource_type="organization",
        resource_id=org_uuid,
        ip_address=req.client.host if req and req.client else None,
        user_agent=req.headers.get("user-agent") if req else None,
        details={"new_tier": tier}
    )
    
    return {"status": "updated", "tier": tier}

@router.delete("/admin/users/{user_uuid}")
def delete_user(user_uuid: str, admin_uuid: str = Depends(get_current_admin), req: Request = None):
    """Delete user account (admin only)"""
    db = next(get_db())
    admin = db.query(User).filter(User.uuid == admin_uuid).first()
    
    user = db.query(User).filter(User.uuid == user_uuid).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    log_audit(
        user_id=admin.id,
        action="admin_delete_user",
        resource_type="user",
        resource_id=user_uuid,
        ip_address=req.client.host if req and req.client else None,
        user_agent=req.headers.get("user-agent") if req else None,
        details={"email": user.email}
    )
    
    invalidate_user_cache(user.id)
    cache_delete_pattern(f"*:{user.id}*")
    
    db.delete(user)
    db.commit()
    
    return {"status": "deleted"}

@router.get("/admin/audit")
def get_all_audit_logs(admin_uuid: str = Depends(get_current_admin), req: Request = None, limit: int = 100):
    """Get all audit logs (admin only)"""
    db = next(get_db())
    admin = db.query(User).filter(User.uuid == admin_uuid).first()
    
    logs = db.query(
        AuditLog,
        User.email.label('user_email')
    ).outerjoin(
        User, AuditLog.user_id == User.id
    ).order_by(AuditLog.created_at.desc()).limit(limit).all()
    
    log_audit(
        user_id=admin.id,
        action="admin_view_audit_log",
        resource_type="audit",
        ip_address=req.client.host if req and req.client else None,
        user_agent=req.headers.get("user-agent") if req else None
    )
    
    return {"audit_log": [{**l[0].__dict__, "user_email": l[1]} for l in logs]}

@router.get("/admin/stats")
def get_platform_stats(admin_uuid: str = Depends(get_current_admin), req: Request = None):
    """Get platform statistics (admin only)"""
    db = next(get_db())
    admin = db.query(User).filter(User.uuid == admin_uuid).first()
    
    from datetime import datetime, timedelta
    
    total_orgs = db.query(func.count(Organization.id)).scalar()
    
    free_orgs = db.query(func.count(Organization.id)).filter(
        Organization.tier == 'free'
    ).scalar()
    
    paid_orgs = db.query(func.count(Organization.id)).filter(
        Organization.tier == 'paid'
    ).scalar()
    
    total_messages = db.query(func.count(Message.id)).scalar()
    total_addresses = db.query(func.count(EmailAddress.id)).scalar()
    
    messages_24h = db.query(func.count(Message.id)).filter(
        Message.received_at > datetime.utcnow() - timedelta(hours=24)
    ).scalar()
    
    log_audit(
        user_id=admin.id,
        action="admin_view_stats",
        resource_type="platform",
        ip_address=req.client.host if req and req.client else None,
        user_agent=req.headers.get("user-agent") if req else None
    )
    
    return {
        "total_organizations": total_orgs,
        "free_organizations": free_orgs,
        "paid_organizations": paid_orgs,
        "total_messages": total_messages,
        "total_addresses": total_addresses,
        "messages_24h": messages_24h
    }

@router.post("/admin/sessions/revoke-user/{user_uuid}")
def admin_revoke_user_sessions(user_uuid: str, admin_uuid: str = Depends(get_current_admin), req: Request = None):
    """Revoke all sessions for a specific user (admin only)"""
    db = next(get_db())
    admin = db.query(User).filter(User.uuid == admin_uuid).first()
    
    user = db.query(User).filter(User.uuid == user_uuid).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    revoke_all_sessions(db, user.id)
    
    log_audit(
        user_id=admin.id,
        action="admin_revoke_user_sessions",
        resource_type="session",
        resource_id=user_uuid,
        ip_address=req.client.host if req and req.client else None,
        user_agent=req.headers.get("user-agent") if req else None,
        details={"target_user": user.email}
    )
    
    return {"status": "revoked", "user": user.email}

@router.post("/admin/sessions/revoke-organization/{org_uuid}")
def admin_revoke_org_sessions(org_uuid: str, admin_uuid: str = Depends(get_current_admin), req: Request = None):
    """Revoke all sessions for all users in an organization (admin only)"""
    db = next(get_db())
    admin = db.query(User).filter(User.uuid == admin_uuid).first()
    
    org = db.query(Organization).filter(Organization.uuid == org_uuid).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    users = db.query(User).filter(User.organization_id == org.id).all()
    count = 0
    
    for user in users:
        revoke_all_sessions(db, user.id)
        count += 1
    
    log_audit(
        user_id=admin.id,
        action="admin_revoke_org_sessions",
        resource_type="session",
        resource_id=org_uuid,
        ip_address=req.client.host if req and req.client else None,
        user_agent=req.headers.get("user-agent") if req else None,
        details={"organization": org.name, "users_affected": count}
    )
    
    return {"status": "revoked", "organization": org.name, "users_affected": count}

@router.post("/admin/sessions/revoke-all")
def admin_revoke_all_sessions(admin_uuid: str = Depends(get_current_admin), req: Request = None):
    """Revoke all sessions for all users (admin only - emergency use)"""
    db = next(get_db())
    admin = db.query(User).filter(User.uuid == admin_uuid).first()
    
    from models.models import Session as SessionModel
    count = db.query(SessionModel).filter(
        SessionModel.revoked_at == None
    ).update({"revoked_at": func.now()})
    
    db.query(RefreshToken).filter(
        RefreshToken.revoked_at == None
    ).update({"revoked_at": func.now()})
    
    db.commit()
    
    # Clear all session cache
    from lib.utils.cache import cache_delete_pattern
    cache_delete_pattern("session:*")
    
    log_audit(
        user_id=admin.id,
        action="admin_revoke_all_sessions",
        resource_type="session",
        ip_address=req.client.host if req and req.client else None,
        user_agent=req.headers.get("user-agent") if req else None,
        details={"sessions_revoked": count}
    )
    
    return {"status": "revoked", "sessions_affected": count}
