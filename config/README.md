# Configuration Directory

## Overview

This directory contains deployment configurations and system service files. **No .env files are stored here.**

## Directory Structure

```
config/
├── systemd/              # systemd service files
│   ├── backend.service
│   ├── worker.service
│   └── policy-service.service
│
└── deployment/           # Deployment configs
    └── postfix-main.cf   # Postfix MX configuration
```

## Environment Files Location

**.env files are stored in their respective component directories:**

- `backend/.env` - Backend API configuration
- `worker/.env` - Worker service configuration
- `policy-service/.env` - Policy service configuration

**Examples:**
- `backend/.env.example`
- `worker/.env.example`
- `policy-service/.env.example`

## Setup

### Development

```bash
# Backend
cd backend
cp .env.example .env
nano .env  # Edit with your settings

# Worker
cd worker
cp .env.example .env
nano .env

# Policy Service
cd policy-service
cp .env.example .env
nano .env
```

### Production

```bash
# Backend
cd /opt/logging-email/backend
cp .env.example .env
nano .env

# Install systemd service
sudo cp /opt/logging-email/config/systemd/backend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable backend
sudo systemctl start backend
```

## systemd Services

### backend.service
FastAPI backend application

**Install:**
```bash
sudo cp config/systemd/backend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable backend
sudo systemctl start backend
```

### worker.service
Email processing worker

**Install:**
```bash
sudo cp config/systemd/worker.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable worker
sudo systemctl start worker
```

### policy-service.service
SMTP policy daemon

**Install:**
```bash
sudo cp config/systemd/policy-service.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable policy-service
sudo systemctl start policy-service
```

## Deployment Configs

### postfix-main.cf
Postfix MX server configuration

**Install:**
```bash
sudo cp config/deployment/postfix-main.cf /etc/postfix/main.cf
sudo postfix check
sudo systemctl reload postfix
```

## Why This Structure?

### .env Files in Component Directories
- ✅ **Execution context** - Apps load .env from their working directory
- ✅ **Clear ownership** - Each component owns its config
- ✅ **Easy development** - Run from component directory
- ✅ **No confusion** - Config lives with code

### System Configs in config/
- ✅ **Deployment templates** - systemd, Postfix configs
- ✅ **Centralized** - All deployment configs in one place
- ✅ **Version controlled** - Track changes to system configs
- ✅ **Reusable** - Copy to system locations on deployment

## Configuration Management

### Development
```bash
# Each component has its own .env
backend/.env
worker/.env
policy-service/.env
```

### Production
```bash
# Option 1: Keep .env in component directories
/opt/logging-email/backend/.env
/opt/logging-email/worker/.env
/opt/logging-email/policy-service/.env

# Option 2: Use systemd EnvironmentFile
# Specify in service file:
EnvironmentFile=/etc/logging-email/backend.env
```

## Security

### .env Files
- ✅ Never commit to git (in .gitignore)
- ✅ Restrict permissions: `chmod 600 .env`
- ✅ Different secrets per environment
- ✅ Rotate secrets regularly

### systemd Services
- ✅ Run as dedicated users
- ✅ Minimal permissions
- ✅ Security hardening enabled
- ✅ Read-only filesystems where possible

## Summary

✅ **.env files** - In component directories (backend/, worker/, policy-service/)
✅ **systemd services** - In config/systemd/
✅ **Deployment configs** - In config/deployment/
✅ **Clean separation** - No mixing of runtime and deployment configs
✅ **Easy to manage** - Clear ownership and location

Configuration is now organized and logical!
