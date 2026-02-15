# logging.email - Project Overview

## What is logging.email?

logging.email is a **hosted inbound email logging and inspection service** designed for developers, testers, and teams who need to receive, inspect, and debug emails without running their own mail infrastructure.

### Key Principle
**This is not a mail client. It is an email observability and logging platform.**

## Use Cases

- **Development & Testing**: Receive emails from your application during development
- **Webhook Testing**: Get email notifications for debugging
- **Email Template Testing**: Preview how emails render
- **Integration Testing**: Verify email delivery in CI/CD
- **Monitoring**: Log emails from production systems for audit
- **Debugging**: Inspect headers, attachments, and content safely

## Core Features

### ✅ Implemented

1. **Dedicated Email Addresses**
   - Each customer gets `<uuid>@logging.email`
   - Create additional addresses (3 free, 50 paid)
   - Activate/deactivate addresses

2. **Email Reception & Logging**
   - Receive emails via SMTP (port 25)
   - Parse safely (never execute content)
   - Store headers, body, attachments
   - Display in web UI

3. **Security First**
   - HTML sanitisation (XSS prevention)
   - Attachment isolation (never executed)
   - Rate limiting per tier
   - TLS everywhere
   - Fail-closed policy checks

4. **Two-Tier System**
   - **Free**: 3 addresses, 7-day retention, ads
   - **Paid**: 50 addresses, 90-day retention, no ads

5. **Stripe Billing**
   - Checkout integration
   - Webhook handling
   - Automatic tier management
   - Subscription lifecycle

6. **Web UI**
   - Authentication (JWT)
   - Message list & detail view
   - Address management
   - Billing controls

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                         Internet                             │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ SMTP (port 25)
                     ▼
            ┌────────────────┐
            │  Postfix MX    │
            │   (port 25)    │
            └────────┬───────┘
                     │
                     │ Policy Check
                     ▼
            ┌────────────────┐
            │ Policy Service │◄──────┐
            │  (localhost)   │       │
            └────────┬───────┘       │
                     │               │ HTTPS
                     │ Forward       │
                     ▼               │
            ┌────────────────┐       │
            │  Backend API   │◄──────┘
            │   (FastAPI)    │
            └────┬───────┬───┘
                 │       │
                 │       │ Enqueue
                 │       ▼
                 │  ┌─────────┐
                 │  │  Redis  │
                 │  │  Queue  │
                 │  └────┬────┘
                 │       │
                 │       │ Dequeue
                 │       ▼
                 │  ┌─────────┐
                 │  │ Worker  │
                 │  │ Service │
                 │  └────┬────┘
                 │       │
                 ▼       ▼
            ┌─────────────────┐
            │     MySQL       │
            │   Database      │
            └─────────────────┘
                     ▲
                     │
                     │ HTTPS
                     │
            ┌────────────────┐
            │   Frontend     │
            │   (HTML/JS)    │
            └────────────────┘
```

### Data Flow

1. **Email Arrives**: Internet → Postfix MX
2. **Policy Check**: Postfix → Policy Service → Backend API
3. **Accept/Reject**: Backend validates recipient, rate limits
4. **Ingestion**: Postfix → Backend API → Redis Queue
5. **Processing**: Worker → Parse → Sanitise → Store
6. **Display**: Frontend → Backend API → MySQL

### Security Layers

1. **SMTP Layer**: Postfix hardening, rate limits
2. **Policy Layer**: Recipient validation, fail-closed
3. **Ingestion Layer**: API token auth, size limits
4. **Processing Layer**: Safe parsing, HTML sanitisation
5. **Storage Layer**: Isolated attachments, encrypted DB
6. **API Layer**: JWT auth, input validation
7. **Frontend Layer**: Sanitised output only

## Technology Stack

### Backend
- **Language**: Python 3.10+
- **Framework**: FastAPI
- **Database**: MySQL 8.0+
- **Queue**: Redis 6.0+
- **Auth**: JWT (python-jose), Bcrypt (passlib)
- **Billing**: Stripe
- **HTML Sanitisation**: Bleach

### MX Infrastructure
- **MTA**: Postfix 3.6+
- **Policy Service**: Python (custom daemon)
- **TLS**: Let's Encrypt

### Frontend
- **Stack**: Vanilla HTML/CSS/JavaScript
- **API Client**: Fetch API
- **Hosting**: Nginx (can be Cloudflare proxied)

### Deployment
- **OS**: Ubuntu 22.04 LTS
- **Process Manager**: systemd
- **Reverse Proxy**: Nginx
- **TLS**: Certbot (Let's Encrypt)

## File Structure

```
logging.email/
├── backend/              # FastAPI application
│   ├── main.py          # Application entry point
│   ├── config.py        # Configuration management
│   ├── database.py      # Database connection
│   ├── auth.py          # Authentication & tokens
│   ├── policy.py        # Policy check endpoint
│   ├── ingest.py        # Email ingestion endpoint
│   ├── api.py           # Customer-facing API
│   ├── billing.py       # Stripe integration
│   └── requirements.txt
│
├── policy-service/       # SMTP policy daemon
│   ├── policy_daemon.py # Policy service
│   └── requirements.txt
│
├── worker/              # Email processing worker
│   ├── worker.py        # Worker service
│   ├── config.py        # Worker configuration
│   └── requirements.txt
│
├── frontend/            # Web UI
│   └── index.html       # Single-page app
│
├── config/              # Configuration templates
│   ├── schema.sql       # Database schema
│   ├── postfix-main.cf  # Postfix configuration
│   ├── backend.service  # systemd service
│   ├── worker.service   # systemd service
│   ├── policy-service.service
│   ├── *.env.example    # Environment templates
│   └── generate_tokens.py
│
├── docs/                # Documentation
│   ├── DEPLOYMENT.md    # Deployment guide
│   ├── SECURITY.md      # Security architecture
│   ├── API.md           # API documentation
│   ├── BUSINESS.md      # Business logic
│   └── TESTING.md       # Testing guide
│
├── README.md            # Project overview
├── QUICKSTART.md        # Quick start guide
├── .gitignore
└── dev-setup.sh         # Local dev setup script
```

## Security Highlights

### Email Content
- ✅ Never executed
- ✅ HTML sanitised with allowlist
- ✅ Attachments isolated
- ✅ Safe parsing only

### SMTP
- ✅ Recipient validation at RCPT stage
- ✅ Rate limiting enforced
- ✅ No catch-all addresses
- ✅ Fail-closed policy

### API
- ✅ JWT authentication
- ✅ API token authentication
- ✅ Input validation
- ✅ SQL injection prevention
- ✅ XSS prevention

### Infrastructure
- ✅ TLS everywhere
- ✅ Least privilege
- ✅ Service isolation
- ✅ No secrets on MX hosts

See [docs/SECURITY.md](docs/SECURITY.md) for full details.

## Business Model

### Free Tier
- **Price**: £0/month
- **Addresses**: 3
- **Retention**: 7 days
- **Rate Limit**: 100/hour
- **Ads**: Yes
- **Revenue**: Ad-supported

### Paid Tier
- **Price**: £9/month
- **Addresses**: 50
- **Retention**: 90 days
- **Rate Limit**: 1000/hour
- **Ads**: No
- **Revenue**: Subscription

### Target Metrics
- 10,000 free users
- 1,000 paid users (10% conversion)
- £9,000/month revenue
- ~£1,500/month costs
- ~£7,500/month profit

See [docs/BUSINESS.md](docs/BUSINESS.md) for full details.

## Roadmap

### Phase 1: MVP ✅ (Current)
- [x] Email reception
- [x] Safe parsing & sanitisation
- [x] Web UI
- [x] Authentication
- [x] Two-tier system
- [x] Stripe billing

### Phase 2: Enhancement
- [ ] Webhooks for new messages
- [ ] Email forwarding rules
- [ ] Search and filters
- [ ] API rate limiting
- [ ] Mobile-responsive UI

### Phase 3: Growth
- [ ] Custom domains
- [ ] Team accounts
- [ ] Shared inboxes
- [ ] Advanced analytics
- [ ] Mobile app

### Phase 4: Enterprise
- [ ] White-label offering
- [ ] SLA guarantees
- [ ] Priority support
- [ ] Integration with ownyour.email
- [ ] Integration with notify.work

## Getting Started

### For Developers
1. Read [QUICKSTART.md](QUICKSTART.md)
2. Run locally in 10 minutes
3. Explore the code
4. Run tests

### For Deployment
1. Read [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
2. Provision infrastructure
3. Configure DNS
4. Deploy services
5. Monitor and scale

### For Security Review
1. Read [docs/SECURITY.md](docs/SECURITY.md)
2. Review threat model
3. Test security controls
4. Report issues

## Contributing

### Code Style
- Python: PEP 8
- British English in docs
- Security-first mindset
- Minimal, boring solutions

### Pull Requests
1. Fork repository
2. Create feature branch
3. Write tests
4. Update documentation
5. Submit PR

### Security Issues
- **DO NOT** open public issues for security vulnerabilities
- Email: security@logging.email
- PGP key available on request

## License

[Choose appropriate license - MIT, Apache 2.0, etc.]

## Support

- **Documentation**: [docs/](docs/)
- **Issues**: GitHub Issues
- **Email**: support@logging.email
- **Status**: status.logging.email

## Credits

Built with security and simplicity in mind.

Inspired by:
- Mailinator
- Mailtrap
- MailHog
- notify.work
- ownyour.email

---

**Remember**: This is an email logging platform, not a mail client. Never use it for production email or sensitive data.
