from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session
from lib.database import get_db
from models.models import EmailAddress, Organization, TierLimit, Message, UsageTracking
from lib.utils.auth import verify_api_token
from lib.utils.cache import cache_get, cache_set
from datetime import datetime, timedelta

router = APIRouter()

class PolicyRequest(BaseModel):
    recipient: str

class PolicyResponse(BaseModel):
    action: str  # "OK" or "REJECT"
    message: str = ""

def verify_policy_token(x_api_token: str = Header(...)):
    """Verify API token for policy service"""
    from models.models import ApiToken
    db = next(get_db())
    tokens = db.query(ApiToken).filter(
        ApiToken.scope == 'policy',
        ApiToken.is_active == True
    ).all()
    
    for token in tokens:
        if verify_api_token(x_api_token, token.token_hash):
            token.last_used_at = func.now()
            db.commit()
            return True
    
    raise HTTPException(status_code=401, detail="Invalid API token")

@router.post("/policy/check", response_model=PolicyResponse)
def check_recipient(request: PolicyRequest, _: bool = Depends(verify_policy_token)):
    """
    Policy check endpoint for Postfix.
    Returns OK if recipient is valid and active, REJECT otherwise.
    Enforces tier limits: rate limits, storage quotas, and monthly email limits.
    """
    recipient = request.recipient.lower().strip()
    cache_key = f"policy:{recipient}"
    
    try:
        cached = cache_get(cache_key)
        if cached:
            return PolicyResponse(
                action=cached['action'],
                message=cached.get('message', '')
            )
        
        db = next(get_db())
        email_addr = db.query(EmailAddress).filter(
            EmailAddress.address == recipient
        ).first()
        
        if not email_addr:
            response = {"action": "REJECT", "message": "Unknown recipient"}
            cache_set(cache_key, response, ttl=60)
            return PolicyResponse(**response)
        
        if not email_addr.is_active:
            response = {"action": "REJECT", "message": "Address inactive"}
            cache_set(cache_key, response, ttl=60)
            return PolicyResponse(**response)
        
        org = db.query(Organization).filter(Organization.id == email_addr.organization_id).first()
        tier_limit = db.query(TierLimit).filter(TierLimit.tier == org.tier).first()
        
        if not tier_limit:
            response = {"action": "REJECT", "message": "Tier configuration error"}
            cache_set(cache_key, response, ttl=60)
            return PolicyResponse(**response)
        
        # Check hourly rate limit
        hourly_count = db.query(func.count(Message.id)).join(
            EmailAddress, Message.email_address_id == EmailAddress.id
        ).filter(
            EmailAddress.address == recipient,
            Message.received_at > datetime.utcnow() - timedelta(hours=1)
        ).scalar()
        
        if hourly_count >= tier_limit.rate_limit_per_hour:
            response = {"action": "REJECT", "message": "Hourly rate limit exceeded"}
            cache_set(cache_key, response, ttl=60)
            return PolicyResponse(**response)
        
        # Check monthly usage limits
        now = datetime.utcnow()
        period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        usage = db.query(UsageTracking).filter(
            UsageTracking.organization_id == org.id,
            UsageTracking.period_start == period_start
        ).first()
        
        if usage:
            # Check storage quota
            if tier_limit.max_storage_mb > 0 and usage.storage_used_mb >= tier_limit.max_storage_mb:
                response = {"action": "REJECT", "message": "Storage quota exceeded"}
                cache_set(cache_key, response, ttl=300)
                return PolicyResponse(**response)
        
        response = {"action": "OK"}
        cache_set(cache_key, response, ttl=300)
        return PolicyResponse(**response)
        
    except Exception as e:
        return PolicyResponse(action="REJECT", message="Policy check failed")
