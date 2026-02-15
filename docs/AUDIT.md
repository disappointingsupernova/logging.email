# Audit System

## Overview

All user actions in logging.email are logged to the `audit_log` table for security, compliance, and debugging purposes.

## What is Logged

### Authentication Events
- `register` - New customer registration
- `login` - Successful login
- `login_failed` - Failed login attempt

### Message Events
- `list_messages` - Viewing message list
- `view_message` - Viewing specific message

### Address Events
- `list_addresses` - Viewing address list
- `create_address` - Creating new email address
- `delete_address` - Deleting email address

### Billing Events
- `create_checkout` - Starting Stripe checkout
- `upgrade_to_paid` - Successful upgrade to paid tier
- `downgrade_to_free` - Downgrade to free tier
- `view_billing_status` - Viewing billing status

### Audit Events
- `view_audit_log` - Viewing own audit log

## Data Captured

Each audit log entry contains:

- **customer_id**: Customer who performed action (NULL for failed logins)
- **action**: Action performed (see above)
- **resource_type**: Type of resource (customer, message, email_address, billing, audit)
- **resource_id**: ID of specific resource (if applicable)
- **ip_address**: Client IP address
- **user_agent**: Browser/client user agent
- **details**: JSON object with additional context
- **created_at**: Timestamp of action

## Security Benefits

1. **Intrusion Detection**: Identify suspicious patterns (multiple failed logins, unusual access times)
2. **Compliance**: GDPR audit trail for data access
3. **Debugging**: Trace customer actions when troubleshooting
4. **Accountability**: Prove who did what and when

## Accessing Audit Logs

### Customer View
Customers can view their own audit log:

```http
GET /audit
Authorization: Bearer <token>
```

Returns last 100 audit events for the authenticated customer.

### Admin View
Database query for admin investigation:

```sql
-- Recent failed logins
SELECT * FROM audit_log 
WHERE action = 'login_failed' 
ORDER BY created_at DESC 
LIMIT 50;

-- Customer activity
SELECT * FROM audit_log 
WHERE customer_id = 123 
ORDER BY created_at DESC;

-- Suspicious patterns (multiple IPs)
SELECT customer_id, COUNT(DISTINCT ip_address) as ip_count
FROM audit_log
WHERE created_at > DATE_SUB(NOW(), INTERVAL 1 DAY)
GROUP BY customer_id
HAVING ip_count > 5;
```

## Retention

Audit logs are retained indefinitely for security and compliance purposes. They are NOT subject to tier retention policies.

## Privacy Considerations

- Passwords are NEVER logged
- Email content is NEVER logged
- Only metadata and actions are logged
- IP addresses are logged for security (legitimate interest under GDPR)

## Example Audit Log Entry

```json
{
  "id": 12345,
  "customer_id": 42,
  "action": "view_message",
  "resource_type": "message",
  "resource_id": "789",
  "ip_address": "203.0.113.42",
  "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)...",
  "details": null,
  "created_at": "2024-01-15T10:30:00"
}
```

## Monitoring Alerts

Set up alerts for:

- Multiple failed logins from same IP
- Account access from new country/IP
- Unusual number of API calls
- Bulk message deletion
- Rapid address creation/deletion

## Implementation

Audit logging is implemented in `backend/audit.py` and called from all API endpoints that perform user actions.

```python
from audit import log_audit

log_audit(
    customer_id=customer_id,
    action="view_message",
    resource_type="message",
    resource_id=str(message_id),
    ip_address=req.client.host,
    user_agent=req.headers.get("user-agent")
)
```

## Future Enhancements

- Real-time alerting for suspicious activity
- Export audit log to SIEM
- Anomaly detection (ML-based)
- Audit log search and filtering in UI
- Webhook notifications for critical events
