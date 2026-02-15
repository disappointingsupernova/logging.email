# Documentation

## Getting Started

- **[QUICKSTART.md](QUICKSTART.md)** - Get running locally in 10 minutes
- **[PROJECT.md](PROJECT.md)** - Complete project overview and architecture

## Core Documentation

### Development
- **[API.md](API.md)** - REST API reference and endpoints
- **[TESTING.md](TESTING.md)** - Unit, integration, and load testing
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Common issues and solutions

### Operations
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Production deployment guide
- **[INFRASTRUCTURE.md](INFRASTRUCTURE.md)** - Redis, RabbitMQ, MongoDB setup
- **[SECURITY.md](SECURITY.md)** - Threat model and security architecture

### Features
- **[ADMIN.md](ADMIN.md)** - Platform admin access and management
- **[AUDIT.md](AUDIT.md)** - Audit logging system
- **[BUSINESS.md](BUSINESS.md)** - Tiers, billing, and business model

## Quick Links

**Setup:**
```bash
# Quick start
cd backend
cp .env.example .env
python main.py
python create_admin.py
```

**Architecture:**
```
Internet → Postfix → Policy Service → Backend API
                ↓
            RabbitMQ → Workers → MySQL + MongoDB
                                      ↓
                                  Frontend
```

**Key Concepts:**
- Organizations own email addresses and subscriptions
- Users are members of organizations (owner/admin/member)
- Email content stored in MongoDB, metadata in MySQL
- Redis caching for policy checks
- RabbitMQ for reliable message processing

## Archive

Implementation notes and migration guides are in `/archive/` directory.
