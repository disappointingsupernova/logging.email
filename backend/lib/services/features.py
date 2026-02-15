from sqlalchemy import func
from sqlalchemy.orm import Session
from fastapi import HTTPException
from models.models import Organization, TierLimit, UsageTracking, EmailAddress
from datetime import datetime, timedelta
from lib.utils.cache import cache_get, cache_set

def get_tier_limits(db: Session, org_id: int) -> TierLimit:
    """Get tier limits for organization with caching"""
    cache_key = f"tier_limits:{org_id}"
    cached = cache_get(cache_key)
    if cached:
        return cached
    
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    limits = db.query(TierLimit).filter(TierLimit.tier == org.tier).first()
    if not limits:
        raise HTTPException(status_code=500, detail="Tier configuration not found")
    
    cache_set(cache_key, limits, ttl=300)
    return limits

def check_feature_enabled(db: Session, org_id: int, feature: str) -> bool:
    """Check if feature is enabled for organization's tier"""
    limits = get_tier_limits(db, org_id)
    return getattr(limits, f"{feature}_enabled", False)

def enforce_feature(db: Session, org_id: int, feature: str):
    """Raise exception if feature not enabled"""
    if not check_feature_enabled(db, org_id, feature):
        raise HTTPException(status_code=403, detail=f"Feature '{feature}' not available in your tier")

def check_address_limit(db: Session, org_id: int) -> bool:
    """Check if organization can create more addresses"""
    limits = get_tier_limits(db, org_id)
    current = db.query(func.count(EmailAddress.id)).filter(
        EmailAddress.organization_id == org_id
    ).scalar()
    return current < limits.max_addresses

def enforce_address_limit(db: Session, org_id: int):
    """Raise exception if address limit reached"""
    if not check_address_limit(db, org_id):
        raise HTTPException(status_code=403, detail="Address limit reached for your tier")

def get_current_usage(db: Session, org_id: int) -> dict:
    """Get current period usage for organization"""
    now = datetime.utcnow()
    period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    usage = db.query(UsageTracking).filter(
        UsageTracking.organization_id == org_id,
        UsageTracking.period_start == period_start
    ).first()
    
    if not usage:
        usage = UsageTracking(
            organization_id=org_id,
            period_start=period_start,
            period_end=period_start + timedelta(days=32)
        )
        db.add(usage)
        db.commit()
        db.refresh(usage)
    
    return {
        "emails_received": usage.emails_received,
        "storage_used_mb": usage.storage_used_mb,
        "api_calls": usage.api_calls
    }

def track_email_received(db: Session, org_id: int, size_mb: float = 0):
    """Increment email received counter and storage usage"""
    now = datetime.utcnow()
    period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    usage = db.query(UsageTracking).filter(
        UsageTracking.organization_id == org_id,
        UsageTracking.period_start == period_start
    ).first()
    
    if usage:
        usage.emails_received += 1
        usage.storage_used_mb += int(size_mb)
        db.commit()

def track_api_call(db: Session, org_id: int):
    """Increment API call counter"""
    now = datetime.utcnow()
    period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    usage = db.query(UsageTracking).filter(
        UsageTracking.organization_id == org_id,
        UsageTracking.period_start == period_start
    ).first()
    
    if usage:
        usage.api_calls += 1
        db.commit()
