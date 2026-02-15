from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy import func
from lib.database import get_db
from lib.utils.auth_helpers import get_current_user, get_user_id
from lib.services.audit import log_audit
from lib.utils.cache import cache_get, cache_set, invalidate_tier_cache, invalidate_user_cache
from models.models import User, Organization, Subscription
from config import settings
import stripe

stripe.api_key = settings.stripe_secret_key
router = APIRouter()

@router.post("/billing/create-checkout")
def create_checkout_session(user_uuid: str = Depends(get_current_user), req: Request = None):
    """Create Stripe checkout session for upgrading to paid"""
    db = next(get_db())
    user = db.query(User).filter(User.uuid == user_uuid).first()
    org = db.query(Organization).filter(Organization.id == user.organization_id).first()
    
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    if org.tier == 'paid':
        raise HTTPException(status_code=400, detail="Already on paid tier")
    
    if org.stripe_customer_id:
        stripe_customer_id = org.stripe_customer_id
    else:
        stripe_customer = stripe.Customer.create(email=user.email)
        stripe_customer_id = stripe_customer.id
        org.stripe_customer_id = stripe_customer_id
        db.commit()
    
    session = stripe.checkout.Session.create(
        customer=stripe_customer_id,
        payment_method_types=['card'],
        line_items=[{
            'price': settings.stripe_price_id,
            'quantity': 1,
        }],
        mode='subscription',
        success_url=f"{settings.frontend_url}/billing/success",
        cancel_url=f"{settings.frontend_url}/billing/cancel",
        metadata={'organization_uuid': org.uuid}
    )
    
    log_audit(
        user_id=user.id,
        action="create_checkout",
        resource_type="billing",
        ip_address=req.client.host if req and req.client else None,
        user_agent=req.headers.get("user-agent") if req else None
    )
    
    return {"checkout_url": session.url}

@router.post("/billing/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhooks"""
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    db = next(get_db())
    
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        org_uuid = session['metadata']['organization_uuid']
        
        org = db.query(Organization).filter(Organization.uuid == org_uuid).first()
        if org:
            org.tier = 'paid'
            
            subscription = stripe.Subscription.retrieve(session['subscription'])
            new_sub = Subscription(
                organization_id=org.id,
                stripe_subscription_id=subscription.id,
                status=subscription.status,
                current_period_end=func.from_unixtime(subscription.current_period_end)
            )
            db.add(new_sub)
            db.commit()
            
            invalidate_tier_cache(org.id)
            
            log_audit(
                user_id=None,
                action="upgrade_to_paid",
                resource_type="billing",
                details={"subscription_id": subscription.id, "organization_id": org.id}
            )
    
    elif event['type'] == 'customer.subscription.updated':
        subscription = event['data']['object']
        sub = db.query(Subscription).filter(
            Subscription.stripe_subscription_id == subscription.id
        ).first()
        if sub:
            sub.status = subscription.status
            sub.current_period_end = func.from_unixtime(subscription.current_period_end)
            db.commit()
    
    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        sub = db.query(Subscription).filter(
            Subscription.stripe_subscription_id == subscription.id
        ).first()
        if sub:
            org = db.query(Organization).filter(Organization.id == sub.organization_id).first()
            if org:
                org.tier = 'free'
            
            sub.status = 'cancelled'
            db.commit()
            
            invalidate_tier_cache(sub.organization_id)
            
            log_audit(
                user_id=None,
                action="downgrade_to_free",
                resource_type="billing",
                details={"subscription_id": subscription.id, "organization_id": sub.organization_id}
            )
    
    return {"status": "success"}

@router.get("/billing/status")
def billing_status(user_uuid: str = Depends(get_current_user), req: Request = None):
    """Get user billing status"""
    db = next(get_db())
    user = db.query(User).filter(User.uuid == user_uuid).first()
    cache_key = f"billing:{user.id}"
    
    cached = cache_get(cache_key)
    if cached:
        return cached
    
    result = db.query(
        Organization.tier,
        Subscription.status,
        Subscription.current_period_end
    ).outerjoin(
        Subscription,
        (Subscription.organization_id == Organization.id) & (Subscription.status == 'active')
    ).filter(Organization.id == user.organization_id).first()
    
    if not result:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    response = {
        "tier": result[0],
        "status": result[1],
        "current_period_end": result[2]
    }
    
    cache_set(cache_key, response, ttl=300)
    
    log_audit(
        user_id=user.id,
        action="view_billing_status",
        resource_type="billing",
        ip_address=req.client.host if req and req.client else None,
        user_agent=req.headers.get("user-agent") if req else None
    )
    
    return response
