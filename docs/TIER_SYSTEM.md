# Enhanced Tier System

## Overview
The tier system now supports:
- Dynamic tier definitions (not hardcoded)
- Feature flags per tier
- Usage tracking per organization
- Automatic enforcement

## Models Added/Modified

### Organization
- `tier`: Changed from Enum to String(63) to support dynamic tiers

### TierLimit (Enhanced)
- `tier`: String(63) primary key
- `max_addresses`: Max email addresses
- `retention_days`: Email retention period
- `rate_limit_per_hour`: Rate limit
- `max_storage_mb`: Storage quota
- `api_enabled`: API access flag
- `webhook_enabled`: Webhook support flag
- `priority_support`: Priority support flag

### UsageTracking (New)
- `organization_id`: FK to organizations
- `period_start`: Billing period start
- `period_end`: Billing period end
- `emails_received`: Count of emails
- `storage_used_mb`: Storage used
- `api_calls`: API call count

## Feature Service

Location: `lib/services/features.py`

### Functions
- `get_tier_limits(db, org_id)`: Get tier limits with caching
- `check_feature_enabled(db, org_id, feature)`: Check if feature enabled
- `enforce_feature(db, org_id, feature)`: Raise 403 if not enabled
- `check_address_limit(db, org_id)`: Check address limit
- `enforce_address_limit(db, org_id)`: Raise 403 if limit reached
- `get_current_usage(db, org_id)`: Get current period usage
- `track_email_received(db, org_id)`: Increment email counter
- `track_api_call(db, org_id)`: Increment API counter

## Usage Examples

### Enforce Feature
```python
from lib.services.features import enforce_feature

@router.post("/webhook")
def create_webhook(user_uuid: str = Depends(get_current_user)):
    db = next(get_db())
    user = db.query(User).filter(User.uuid == user_uuid).first()
    enforce_feature(db, user.organization_id, "webhook")
    # Create webhook...
```

### Check Limit
```python
from lib.services.features import enforce_address_limit

enforce_address_limit(db, org_id)
```

### Track Usage
```python
from lib.services.features import track_email_received, track_api_call

track_email_received(db, org_id)
track_api_call(db, org_id)
```

## API Endpoints

### GET /usage
Returns organization limits and current usage:
```json
{
  "limits": {
    "max_addresses": 50,
    "retention_days": 90,
    "rate_limit_per_hour": 1000,
    "max_storage_mb": 5000,
    "api_enabled": true,
    "webhook_enabled": true,
    "priority_support": true
  },
  "usage": {
    "emails_received": 245,
    "storage_used_mb": 1250,
    "api_calls": 3421
  }
}
```

## Example Tier Definitions

```sql
-- Free tier
INSERT INTO tier_limits VALUES ('free', 3, 7, 100, 100, FALSE, FALSE, FALSE);

-- Paid tier
INSERT INTO tier_limits VALUES ('paid', 50, 90, 1000, 5000, TRUE, TRUE, TRUE);

-- Enterprise tier
INSERT INTO tier_limits VALUES ('enterprise', 500, 365, 10000, 50000, TRUE, TRUE, TRUE);
```
