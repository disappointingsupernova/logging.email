# logging.email

**Hosted inbound email logging and inspection service for developers.**

[![Security](https://img.shields.io/badge/security-first-green.svg)](docs/SECURITY.md)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## What is this?

logging.email provides dedicated email addresses that receive, parse, and display emails safely. Perfect for:

- 🧪 **Testing**: Receive emails from your application during development
- 🔍 **Debugging**: Inspect headers, bodies, and attachments
- 📧 **Monitoring**: Log production emails for audit trails
- 🚀 **CI/CD**: Verify email delivery in automated tests

**This is not a mail client. It's an email observability platform.**

## Quick Start

```bash
# Clone and setup
git clone https://github.com/yourusername/logging.email.git
cd logging.email

# See QUICKSTART.md for full instructions
./dev-setup.sh
```

Running locally in 10 minutes: [QUICKSTART.md](QUICKSTART.md)

## Features

✅ **Secure by Design**
- HTML sanitisation (XSS prevention)
- Safe email parsing (never executes content)
- Isolated attachment storage
- TLS everywhere

✅ **Two-Tier System**
- **Free**: 3 addresses, 7-day retention, ads
- **Paid**: 50 addresses, 90-day retention, no ads (£9/month)

✅ **Developer Friendly**
- REST API with JWT authentication
- Webhook support (coming soon)
- Clean, simple web UI

## Architecture

```
Internet → Postfix MX → Policy Service → Backend API
                ↓
            Redis Queue → Workers → MySQL
                                      ↓
                                  Frontend
```

**Components:**
- `backend/` - FastAPI application
- `policy-service/` - SMTP policy daemon
- `worker/` - Email processing workers
- `frontend/` - Web UI
- `config/` - Deployment configs

## Documentation

- 📖 [Project Overview](docs/PROJECT.md) - Complete project details
- 🚀 [Quick Start](docs/QUICKSTART.md) - Get running in 10 minutes
- 🔧 [Deployment Guide](docs/DEPLOYMENT.md) - Production deployment
- 🔒 [Security Architecture](docs/SECURITY.md) - Threat model & mitigations
- 📡 [API Documentation](docs/API.md) - REST API reference
- 💰 [Business Logic](docs/BUSINESS.md) - Tiers, billing, revenue
- 🧪 [Testing Guide](docs/TESTING.md) - Unit, integration, load tests
- 🏗️ [Infrastructure](docs/INFRASTRUCTURE.md) - Redis, RabbitMQ, MongoDB
- 👤 [Admin Guide](docs/ADMIN.md) - Platform administration
- 📋 [Audit System](docs/AUDIT.md) - Audit logging
- 🔍 [Troubleshooting](docs/TROUBLESHOOTING.md) - Common issues

## Security First

**Email content is hostile.** We treat every email as a potential attack:

- ✅ Never execute email content
- ✅ HTML sanitised with strict allowlist
- ✅ Attachments isolated (never opened)
- ✅ Policy service fails closed
- ✅ Rate limiting enforced
- ✅ SQL injection prevention
- ✅ XSS prevention

See [docs/SECURITY.md](docs/SECURITY.md) for full threat model.

## Technology Stack

- **Backend**: Python 3.10+, FastAPI, MySQL, Redis
- **MX**: Postfix, custom policy daemon
- **Frontend**: Vanilla HTML/CSS/JavaScript
- **Billing**: Stripe
- **Deployment**: Ubuntu, systemd, Nginx, Let's Encrypt

## Contributing

Contributions welcome! Please:

1. Read [PROJECT.md](PROJECT.md) for architecture overview
2. Follow security-first principles
3. Write tests for new features
4. Use British English in documentation

**Security issues**: Email security@logging.email (do not open public issues)

## License

MIT License - see [LICENSE](LICENSE) file

## Support

- 📚 Documentation: [docs/](docs/)
- 🐛 Issues: [GitHub Issues](https://github.com/yourusername/logging.email/issues)
- 💬 Email: support@logging.email

---

**⚠️ Important**: This is a logging platform, not a mail client. Never use it for production email or sensitive data (PII, PHI, PCI).
