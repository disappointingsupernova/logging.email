# API Documentation

Base URL: `https://api.logging.email`

## Authentication

### Register
```http
POST /auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "secure_password"
}
```

Response:
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer"
}
```

### Login
```http
POST /auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "secure_password"
}
```

Response: Same as register

## Messages

### List Messages
```http
GET /messages
Authorization: Bearer <token>
```

Response:
```json
{
  "messages": [
    {
      "id": 123,
      "from_address": "sender@example.com",
      "subject": "Test Email",
      "received_at": "2024-01-15T10:30:00",
      "has_attachments": false,
      "recipient": "uuid@logging.email"
    }
  ]
}
```

### Get Message
```http
GET /messages/{id}
Authorization: Bearer <token>
```

Response:
```json
{
  "id": 123,
  "from_address": "sender@example.com",
  "subject": "Test Email",
  "received_at": "2024-01-15T10:30:00",
  "recipient": "uuid@logging.email",
  "text_body": "Plain text content",
  "sanitised_html": "<p>HTML content</p>",
  "attachments": [
    {
      "id": 1,
      "filename": "document.pdf",
      "content_type": "application/pdf",
      "size_bytes": 12345
    }
  ]
}
```

## Email Addresses

### List Addresses
```http
GET /addresses
Authorization: Bearer <token>
```

Response:
```json
{
  "addresses": [
    {
      "id": 1,
      "address": "uuid@logging.email",
      "is_active": true,
      "created_at": "2024-01-01T00:00:00"
    }
  ]
}
```

### Create Address
```http
POST /addresses?address=custom@logging.email
Authorization: Bearer <token>
```

Response:
```json
{
  "id": 2,
  "address": "custom@logging.email"
}
```

### Delete Address
```http
DELETE /addresses/{id}
Authorization: Bearer <token>
```

Response:
```json
{
  "status": "deleted"
}
```

## Audit Log

### Get Audit Log
```http
GET /audit
Authorization: Bearer <token>
```

Response:
```json
{
  "audit_log": [
    {
      "action": "view_message",
      "resource_type": "message",
      "resource_id": "123",
      "ip_address": "203.0.113.42",
      "created_at": "2024-01-15T10:30:00",
      "details": null
    }
  ]
}
```

## Billing

### Create Checkout Session
```http
POST /billing/create-checkout
Authorization: Bearer <token>
```

Response:
```json
{
  "checkout_url": "https://checkout.stripe.com/..."
}
```

### Get Billing Status
```http
GET /billing/status
Authorization: Bearer <token>
```

Response:
```json
{
  "tier": "paid",
  "status": "active",
  "current_period_end": "2024-02-15T00:00:00"
}
```

### Stripe Webhook
```http
POST /billing/webhook
Stripe-Signature: <signature>

<stripe event payload>
```

## Policy Service (Internal)

### Check Recipient
```http
POST /policy/check
X-API-Token: <policy_token>
Content-Type: application/json

{
  "recipient": "uuid@logging.email"
}
```

Response:
```json
{
  "action": "OK",
  "message": ""
}
```

Or:
```json
{
  "action": "REJECT",
  "message": "Unknown recipient"
}
```

## Ingestion (Internal)

### Ingest Email
```http
POST /ingest
X-API-Token: <worker_token>
Content-Type: multipart/form-data

recipient: uuid@logging.email
sender: sender@example.com
size: 1234
raw_email: <file>
```

Response:
```json
{
  "status": "queued",
  "message_id": 123
}
```

## Error Responses

All endpoints may return:

```json
{
  "detail": "Error message"
}
```

Status codes:
- 400: Bad request
- 401: Unauthorised
- 403: Forbidden (admin access required)
- 404: Not found
- 500: Internal server error

## Admin Endpoints

Require admin role. Returns 403 if not admin.

### List All Customers
```http
GET /admin/customers
Authorization: Bearer <admin_token>
```

### Get Customer Details
```http
GET /admin/customers/{uuid}
Authorization: Bearer <admin_token>
```

### Update Customer Tier
```http
PATCH /admin/customers/{uuid}/tier?tier=paid
Authorization: Bearer <admin_token>
```

### Delete Customer
```http
DELETE /admin/customers/{uuid}
Authorization: Bearer <admin_token>
```

### View All Audit Logs
```http
GET /admin/audit?limit=100
Authorization: Bearer <admin_token>
```

### Platform Statistics
```http
GET /admin/stats
Authorization: Bearer <admin_token>
```

See [ADMIN.md](ADMIN.md) for full admin documentation.
