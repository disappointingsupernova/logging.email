# logging.email Backend

**Secure, scalable email logging and inspection platform backend.**

## Overview

FastAPI-based backend for logging.email - a hosted inbound email service for developers. Provides REST API, SMTP policy enforcement, email ingestion, webhook processing, service monitoring, and notification system.

## Architecture

```
┌─────────────┐
│   Postfix   │ ──→ Policy Service ──→ Ingest API
└─────────────┘           ↓                ↓
                    MySQL/Redis      RabbitMQ Queue
                                           ↓
                                      Workers
                                           ↓
                                    MongoDB + MySQL
                                           ↓
                                      REST API
                                           ↓
                                      Frontend
```

## Tech Stack

- **Framework**: FastAPI 0.109
- **Database**: MySQL (structured data), MongoDB (email content/attachments)
- **Cache**: Redis (sessions, policy checks)
- **Queue**: RabbitMQ (email processing)
- **Auth**: JWT + DB-backed refresh tokens with risk-based session management
- **Payments**: Stripe
- **ORM**: SQLAlchemy 2.0
- **Email**: SMTP with failover and retry logic

## Features

### Authentication & Security
- ✅ JWT access tokens (15 min, configurable)
- ✅ Refresh token rotation with reuse detection
- ✅ Risk-based session management (WiFi↔4G safe, device change requires re-auth)
- ✅ Platform admin role system
- ✅ Security event audit trail
- ✅ Session revocation (single, all, admin-controlled)

### Tier System & Limits
- ✅ Dynamic tier definitions (not hardcoded)
- ✅ Feature flags per tier (API, webhooks, priority support)
- ✅ Usage tracking (emails, storage, API calls)
- ✅ Automatic enforcement at policy level
- ✅ Real-time quota checking

### Email Processing
- ✅ SMTP policy enforcement (rate limits, storage quotas)
- ✅ Email ingestion with RabbitMQ queuing
- ✅ HTML sanitization (XSS prevention)
- ✅ Attachment isolation (MongoDB)
- ✅ Message retention by tier

### API Features
- ✅ Organization-based multi-tenancy
- ✅ Email address management
- ✅ Message viewing with content retrieval
- ✅ Usage and limits dashboard
- ✅ Audit log access
- ✅ Stripe billing integration

### Admin Features
- ✅ User and organization management
- ✅ Tier assignment
- ✅ Platform statistics
- ✅ Session revocation (user/org/platform-wide)
- ✅ Audit log viewing
- ✅ Service health monitoring
- ✅ Outbound email tracking and retry management

### System Features
- ✅ Service health monitoring (MySQL, Redis, RabbitMQ, MongoDB)
- ✅ Outbound email system with SMTP failover
- ✅ Email retry with exponential backoff
- ✅ Comprehensive email delivery tracking
- ✅ Notification system for users and admins

## Project Structure

```
backend/
├── lib/
│   ├── services/
│   │   ├── audit.py          # Audit logging
│   │   ├── email.py          # Outbound email with retry
│   │   ├── features.py       # Tier limits & feature enforcement
│   │   ├── health.py         # Service health checks
│   │   ├── mongodb.py        # MongoDB operations
│   │   ├── queue.py          # RabbitMQ operations
│   │   └── session.py        # Session & auth management
│   ├── utils/
│   │   ├── auth.py           # Password hashing, JWT creation
│   │   ├── auth_helpers.py   # Auth dependencies
│   │   └── cache.py          # Redis cache operations
│   └── database.py           # SQLAlchemy setup
├── models/
│   └── models.py             # SQLAlchemy models
├── routes/
│   ├── admin.py              # Admin endpoints
│   ├── api.py                # User-facing API
│   ├── billing.py            # Stripe integration
│   ├── ingest.py             # Email ingestion
│   ├── monitoring.py         # Health & email monitoring
│   └── policy.py             # SMTP policy checks
├── config.py                 # Configuration management
├── email_worker.py           # Email processing worker
├── main.py                   # FastAPI application
├── requirements.txt          # Python dependencies
└── .env.example              # Environment template
```

## Database Models

### Core Models
- **Organization** - Multi-tenant organization
- **User** - User accounts with roles (owner/admin/member)
- **EmailAddress** - Email addresses per organization
- **Message** - Email metadata
- **Attachment** - Attachment metadata (content in MongoDB)

### Auth & Security
- **Session** - User sessions with device fingerprinting
- **RefreshToken** - Rotating refresh tokens
- **SecurityEvent** - Security audit trail
- **AuditLog** - User action audit trail

### Billing & Limits
- **Subscription** - Stripe subscription tracking
- **TierLimit** - Tier definitions with feature flags
- **UsageTracking** - Monthly usage metrics

### System
- **ApiToken** - Service-to-service authentication
- **OutboundEmail** - Outbound email tracking with retry
- **ServiceHealth** - Service health check history

## Installation

### Prerequisites
- Python 3.10+
- MySQL 8.0+
- MongoDB 5.0+
- Redis 7.0+
- RabbitMQ 3.12+

### Setup

1. **Clone and navigate:**
```bash
cd backend
```

2. **Create virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Configure environment:**
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. **Initialize database:**
```bash
python -c "from models import Base, engine; Base.metadata.create_all(bind=engine)"
```

6. **Create admin user:**
```bash
python create_admin.py
```

7. **Generate API tokens:**
```bash
python generate_tokens.py
```

8. **Start email worker (separate terminal):**
```bash
python email_worker.py
# Or add to cron: */5 * * * * cd /path/to/backend && python email_worker.py
```

## Configuration

### Environment Variables

**Database:**
- `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`
- `MONGODB_URL`, `MONGODB_DATABASE`

**Services:**
- `REDIS_URL`, `REDIS_CACHE_TTL`
- `RABBITMQ_URL`, `RABBITMQ_QUEUE`

**SMTP (Outbound):**
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`
- `SMTP_FROM_EMAIL`, `SMTP_FROM_NAME`, `SMTP_USE_TLS`
- `SMTP_BACKUP_HOST`, `SMTP_BACKUP_PORT` (optional failover)
- `EMAIL_MAX_ATTEMPTS` (default: 5)
- `EMAIL_RETRY_BASE_DELAY` (default: 60 seconds)
- `EMAIL_EXPIRY_HOURS` (default: 48)

**Security:**
- `JWT_SECRET` - JWT signing key
- `API_TOKEN_SALT` - API token hashing salt
- `ACCESS_TOKEN_LIFETIME_MINUTES` (default: 15)
- `REFRESH_TOKEN_LIFETIME_DAYS` (default: 30)
- `SESSION_ABSOLUTE_LIMIT_DAYS` (default: 90)
- `SESSION_IDLE_LIMIT_DAYS` (default: 30)

**Stripe:**
- `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_ID`

**Application:**
- `DOMAIN`, `BACKEND_URL`, `FRONTEND_URL`

## Running

### Development
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Production
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### With Gunicorn
```bash
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## API Endpoints

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - Login (returns access token + refresh cookie)
- `POST /auth/refresh` - Refresh access token
- `POST /auth/logout` - Logout current session
- `POST /auth/logout-all` - Logout all sessions
- `GET /auth/sessions` - List active sessions

### Messages
- `GET /messages` - List messages
- `GET /messages/{id}` - Get message details

### Email Addresses
- `GET /addresses` - List addresses
- `POST /addresses` - Create address (enforces tier limits)
- `DELETE /addresses/{id}` - Delete address

### Usage & Limits
- `GET /usage` - Get usage and tier limits (admins can view any org with `?org_uuid=`)

### Audit
- `GET /audit` - Get audit log

### Admin
- `GET /admin/users` - List all users
- `GET /admin/users/{uuid}` - Get user details
- `PATCH /admin/organizations/{uuid}/tier` - Update organization tier
- `DELETE /admin/users/{uuid}` - Delete user
- `GET /admin/audit` - Get all audit logs
- `GET /admin/stats` - Platform statistics
- `POST /admin/sessions/revoke-user/{uuid}` - Revoke user sessions
- `POST /admin/sessions/revoke-organization/{uuid}` - Revoke org sessions
- `POST /admin/sessions/revoke-all` - Emergency: revoke all sessions

### Monitoring (Admin)
- `GET /admin/health` - Current service health status
- `GET /admin/health/history` - Service health history (paginated)
- `GET /admin/emails` - List outbound emails (paginated)
- `GET /admin/emails/{id}` - Get email details
- `POST /admin/emails/{id}/retry` - Manually retry email
- `POST /admin/emails/process` - Trigger email processing
- `GET /admin/emails/stats` - Email statistics

### Billing
- `POST /billing/create-checkout` - Create Stripe checkout
- `POST /billing/webhook` - Stripe webhook handler
- `GET /billing/status` - Get billing status

### Policy (Internal)
- `POST /policy/check` - SMTP policy check (enforces rate limits, storage quotas)

### Ingestion (Internal)
- `POST /ingest` - Receive email from Postfix

### Health
- `GET /health` - Basic health check
- `GET /health/detailed` - Detailed service health check

## Outbound Email System

### Sending Emails

```python
from lib.services.email import send_notification, send_alert

# Send notification to user
send_notification(db, user_id=123, 
    subject="Welcome!", 
    body_text="Welcome to logging.email",
    body_html="<h1>Welcome!</h1>")

# Send alert to admin
send_alert(db, recipient="admin@example.com",
    subject="Service Alert",
    body_text="Redis is down")
```

### Email Retry Logic

- Emails queued in database with status tracking
- Automatic retry with exponential backoff: 60s, 120s, 240s, 480s, 960s
- Primary SMTP with automatic failover to backup
- Max attempts configurable (default: 5)
- Emails expire after 48 hours (configurable)
- Detailed logging of all attempts

### Email Worker

Run as cron job or systemd service:
```bash
# Cron (every 5 minutes)
*/5 * * * * cd /path/to/backend && /path/to/venv/bin/python email_worker.py

# Or run continuously
while true; do python email_worker.py; sleep 300; done
```

## Service Health Monitoring

### Health Checks

System monitors:
- **MySQL**: Connection and query response time
- **Redis**: Connection and ping response time
- **RabbitMQ**: Connection test
- **MongoDB**: Connection and server info

### Health Status
- `healthy` - All services operational
- `degraded` - Some services slow or unavailable
- `down` - Critical services unavailable

### Accessing Health Data

```bash
# Basic check
curl http://localhost:8000/health

# Detailed check with service status
curl http://localhost:8000/health/detailed

# Admin: View health history
curl -H "Authorization: Bearer TOKEN" \
  "http://localhost:8000/admin/health/history?service=mysql&hours=24"
```

## Monitoring

### Health Check
```bash
curl http://localhost:8000/health
```

### Service Health History
```sql
SELECT * FROM service_health 
WHERE service_name = 'mysql' 
AND checked_at > NOW() - INTERVAL 24 HOUR
ORDER BY checked_at DESC;
```

### Outbound Email Stats
```sql
SELECT status, COUNT(*) as count 
FROM outbound_emails 
WHERE created_at > NOW() - INTERVAL 24 HOUR
GROUP BY status;
```

### Metrics
- Session count: `SELECT COUNT(*) FROM sessions WHERE revoked_at IS NULL`
- Active users: `SELECT COUNT(DISTINCT user_id) FROM sessions WHERE last_seen_at > NOW() - INTERVAL 1 DAY`
- Usage: `SELECT * FROM usage_tracking WHERE period_start = DATE_FORMAT(NOW(), '%Y-%m-01')`

## Troubleshooting

### Service Health Issues
- Check `/health/detailed` endpoint
- Review `service_health` table for patterns
- Verify service connectivity manually
- Check service logs

### Email Delivery Issues
- Check outbound_emails table: `SELECT * FROM outbound_emails WHERE status = 'failed'`
- Review SMTP credentials in .env
- Test SMTP connection manually
- Check email worker logs
- Manually retry: `POST /admin/emails/{id}/retry`

### Redis Connection Issues
- Check `REDIS_URL` in .env
- Verify Redis is running: `redis-cli ping`
- System degrades gracefully (DB fallback)

### Session Issues
- Check session expiry: `SELECT * FROM sessions WHERE id = ?`
- View security events: `SELECT * FROM security_events WHERE session_id = ?`
- Revoke if needed: `UPDATE sessions SET revoked_at = NOW() WHERE id = ?`

## Deployment

See [docs/DEPLOYMENT.md](../docs/DEPLOYMENT.md) for production deployment guide.

### Quick Production Checklist
- [ ] Set strong `JWT_SECRET` and `API_TOKEN_SALT`
- [ ] Configure SSL/TLS for all services
- [ ] Set up database backups
- [ ] Configure log aggregation
- [ ] Set up monitoring/alerting
- [ ] Configure SMTP credentials (primary + backup)
- [ ] Set up email worker as systemd service or cron
- [ ] Review and adjust session lifetimes
- [ ] Configure CORS origins
- [ ] Set up rate limiting (nginx/cloudflare)
- [ ] Enable database connection pooling
- [ ] Configure worker processes

## Documentation

- [Project Overview](../docs/PROJECT.md)
- [API Documentation](../docs/API.md)
- [Auth System](../docs/AUTH_SYSTEM.md)
- [Tier System](../docs/TIER_SYSTEM.md)
- [Security Architecture](../docs/SECURITY.md)
- [Admin Guide](../docs/ADMIN.md)
- [Deployment Guide](../docs/DEPLOYMENT.md)
- [Troubleshooting](../docs/TROUBLESHOOTING.md)

## Contributing

1. Follow security-first principles
2. Use SQLAlchemy ORM (no raw SQL)
3. Write tests for new features
4. Update documentation
5. Use British English in docs

## License

MIT License - see [LICENSE](../LICENSE) file

## Support

- Documentation: [docs/](../docs/)
- Issues: GitHub Issues
- Email: support@logging.email

---

**⚠️ Security Notice**: Never use for production email or sensitive data (PII, PHI, PCI). This is a logging platform for development and testing.
