# Admin Access

## Overview

Admin users have elevated privileges to manage the platform, view all customers, and access comprehensive audit logs.

## Role-Based Access Control

### Roles
- **customer**: Standard user (default)
- **admin**: Platform administrator

### Creating Admin Users

Admins must be created directly in the database:

```sql
-- Create admin account
INSERT INTO customers (uuid, email, password_hash, tier, role)
VALUES (
    UUID(),
    'admin@logging.email',
    '<argon2_hash>',
    'paid',
    'admin'
);

-- Or upgrade existing customer to admin
UPDATE customers SET role = 'admin' WHERE email = 'user@example.com';
```

Generate password hash:
```python
from argon2 import PasswordHasher
ph = PasswordHasher()
print(ph.hash('your_secure_password'))
```

## Admin Endpoints

All admin endpoints require `Authorization: Bearer <token>` header with admin JWT.

### List All Customers
```http
GET /admin/customers
Authorization: Bearer <admin_token>
```

Returns all customers with statistics.

### Get Customer Details
```http
GET /admin/customers/{uuid}
Authorization: Bearer <admin_token>
```

Returns full customer details including addresses and subscription.

### Update Customer Tier
```http
PATCH /admin/customers/{uuid}/tier?tier=paid
Authorization: Bearer <admin_token>
```

Manually change customer tier (free/paid).

### Delete Customer
```http
DELETE /admin/customers/{uuid}
Authorization: Bearer <admin_token>
```

Permanently delete customer account (cascades to addresses, messages, attachments).

### View All Audit Logs
```http
GET /admin/audit?limit=100
Authorization: Bearer <admin_token>
```

View all audit logs across all customers.

### Platform Statistics
```http
GET /admin/stats
Authorization: Bearer <admin_token>
```

Returns platform-wide statistics.

## Audit Logging

### Customer Actions
Logged with `customer_id` only:
- register, login, login_failed
- list_messages, view_message
- list_addresses, create_address, delete_address
- create_checkout, view_billing_status
- view_audit_log

### Admin Actions
Logged with `admin_id` only:
- admin_list_customers
- admin_view_customer
- admin_update_tier
- admin_delete_customer
- admin_view_audit_log
- admin_view_stats

### Querying Admin Actions

```sql
-- All admin actions
SELECT * FROM audit_log 
WHERE admin_id IS NOT NULL 
ORDER BY created_at DESC;

-- Admin actions on specific customer
SELECT * FROM audit_log 
WHERE admin_id IS NOT NULL 
AND customer_id = 123 
ORDER BY created_at DESC;

-- Which admin performed action
SELECT al.*, a.email as admin_email
FROM audit_log al
JOIN customers a ON al.admin_id = a.id
WHERE al.action LIKE 'admin_%'
ORDER BY al.created_at DESC;
```

## Security Considerations

### Admin Authentication
- Admins authenticate with same JWT system
- JWT contains customer UUID (admin's UUID)
- `get_current_admin()` dependency checks role
- Returns 403 if not admin

### Admin Privileges
- View all customer data
- Modify customer tiers
- Delete customer accounts
- View all audit logs
- View platform statistics

### Audit Trail
- All admin actions logged with admin_id
- Customer actions logged with customer_id
- Separate columns prevent confusion
- Full accountability for admin actions

### Best Practices
1. **Minimal admins**: Only create necessary admin accounts
2. **Strong passwords**: Enforce strong passwords for admins
3. **2FA**: Implement 2FA for admin accounts (future)
4. **Regular audits**: Review admin actions regularly
5. **Separate accounts**: Admins should have separate admin accounts, not use customer accounts

## Example Usage

### Admin Login
```bash
# Login as admin (same endpoint as customers)
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@logging.email","password":"admin_password"}' \
  | jq -r '.access_token')
```

### List Customers
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/admin/customers
```

### View Customer Details
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/admin/customers/<uuid>
```

### Update Customer Tier
```bash
curl -X PATCH -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/admin/customers/<uuid>/tier?tier=paid"
```

### View Platform Stats
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/admin/stats
```

### View All Audit Logs
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/admin/audit?limit=50"
```

## Monitoring Admin Activity

### Daily Admin Report
```sql
SELECT 
    a.email as admin,
    al.action,
    COUNT(*) as count
FROM audit_log al
JOIN customers a ON al.admin_id = a.id
WHERE al.created_at > DATE_SUB(NOW(), INTERVAL 1 DAY)
GROUP BY a.email, al.action
ORDER BY count DESC;
```

### Suspicious Admin Activity
```sql
-- Admin deleting many customers
SELECT admin_id, COUNT(*) as deletions
FROM audit_log
WHERE action = 'admin_delete_customer'
AND created_at > DATE_SUB(NOW(), INTERVAL 1 HOUR)
GROUP BY admin_id
HAVING deletions > 5;

-- Admin accessing many customer accounts
SELECT admin_id, COUNT(DISTINCT customer_id) as customers_accessed
FROM audit_log
WHERE action = 'admin_view_customer'
AND created_at > DATE_SUB(NOW(), INTERVAL 1 HOUR)
GROUP BY admin_id
HAVING customers_accessed > 20;
```

## Future Enhancements

- Two-factor authentication for admins
- Admin action approval workflow
- Time-limited admin sessions
- Admin activity alerts
- Role-based permissions (read-only admin, support admin, etc.)
- Admin UI dashboard
