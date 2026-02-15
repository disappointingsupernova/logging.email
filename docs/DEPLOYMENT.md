# Deployment Guide

## Architecture Overview

```
Internet → Postfix MX (port 25) → Policy Service (localhost:10040) → Backend API (HTTPS)
                ↓
            Backend API → Redis Queue → Workers → MySQL + Attachments
                                                      ↓
                                                  Frontend (HTTPS)
```

## Security Principles

1. **Email is hostile** - All content sanitised, never executed
2. **Fail closed** - Policy service rejects on errors
3. **TLS everywhere** - Backend API, Stripe, external comms
4. **Least privilege** - Separate users for each service
5. **No secrets on MX** - Only API token, no database access

## Prerequisites

- Ubuntu 22.04 LTS (or similar)
- MySQL 8.0+
- Redis 6.0+
- Python 3.10+
- Postfix 3.6+
- Valid DNS records (MX, A)
- TLS certificates (Let's Encrypt)

## DNS Configuration

```
logging.email.           IN MX  10 mx1.logging.email.
logging.email.           IN MX  20 mx2.logging.email.
mx1.logging.email.       IN A   <MX_IP_1>
mx2.logging.email.       IN A   <MX_IP_2>
api.logging.email.       IN A   <BACKEND_IP>
logging.email.           IN A   <FRONTEND_IP>
```

## Installation Steps

### 1. Database Setup

```bash
mysql -u root -p < config/schema.sql

# Create database user
mysql -u root -p
CREATE USER 'logging_email'@'localhost' IDENTIFIED BY 'STRONG_PASSWORD';
GRANT ALL PRIVILEGES ON logging_email.* TO 'logging_email'@'localhost';
FLUSH PRIVILEGES;
```

### 2. Create System Users

```bash
sudo useradd -r -s /bin/false backend
sudo useradd -r -s /bin/false worker
sudo useradd -r -s /bin/false policy
```

### 3. Install Backend

```bash
sudo mkdir -p /opt/logging-email/backend
sudo cp -r backend/* /opt/logging-email/backend/
sudo chown -R backend:backend /opt/logging-email/backend

cd /opt/logging-email/backend
sudo -u backend python3 -m venv venv
sudo -u backend venv/bin/pip install -r requirements.txt

# Configure
sudo mkdir -p /etc/logging-email
sudo cp config/backend.env.example /etc/logging-email/backend.env
sudo nano /etc/logging-email/backend.env  # Edit with real values
sudo chmod 600 /etc/logging-email/backend.env
sudo chown backend:backend /etc/logging-email/backend.env

# Install service
sudo cp config/backend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable backend
sudo systemctl start backend
```

### 4. Generate API Tokens

```bash
# Run Python script to generate tokens
python3 << EOF
import secrets
import hashlib

# Generate policy token
policy_token = secrets.token_urlsafe(32)
policy_hash = hashlib.sha256(f"{policy_token}YOUR_API_TOKEN_SALT".encode()).hexdigest()

print(f"Policy Token: {policy_token}")
print(f"Policy Hash: {policy_hash}")

# Insert into database
# INSERT INTO api_tokens (token_hash, description, scope, is_active) 
# VALUES ('{policy_hash}', 'MX Policy Service', 'policy', TRUE);
EOF
```

### 5. Install Worker

```bash
sudo mkdir -p /opt/logging-email/worker
sudo mkdir -p /var/lib/logging-email/attachments
sudo cp -r worker/* /opt/logging-email/worker/
sudo chown -R worker:worker /opt/logging-email/worker
sudo chown -R worker:worker /var/lib/logging-email/attachments

cd /opt/logging-email/worker
sudo -u worker python3 -m venv venv
sudo -u worker venv/bin/pip install -r requirements.txt

sudo cp config/worker.env.example /etc/logging-email/worker.env
sudo nano /etc/logging-email/worker.env
sudo chmod 600 /etc/logging-email/worker.env
sudo chown worker:worker /etc/logging-email/worker.env

sudo cp config/worker.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable worker
sudo systemctl start worker
```

### 6. Install Policy Service (on MX hosts)

```bash
sudo mkdir -p /opt/logging-email/policy-service
sudo cp -r policy-service/* /opt/logging-email/policy-service/
sudo chown -R policy:policy /opt/logging-email/policy-service

cd /opt/logging-email/policy-service
sudo -u policy python3 -m venv venv
sudo -u policy venv/bin/pip install -r requirements.txt

sudo cp config/policy.env.example /etc/logging-email/policy.env
sudo nano /etc/logging-email/policy.env  # Add API_TOKEN from step 4
sudo chmod 600 /etc/logging-email/policy.env
sudo chown policy:policy /etc/logging-email/policy.env

sudo cp config/policy-service.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable policy-service
sudo systemctl start policy-service
```

### 7. Configure Postfix (on MX hosts)

```bash
# Backup existing config
sudo cp /etc/postfix/main.cf /etc/postfix/main.cf.backup

# Install new config
sudo cp config/postfix-main.cf /etc/postfix/main.cf
sudo nano /etc/postfix/main.cf  # Adjust hostnames

# Test configuration
sudo postfix check

# Reload
sudo systemctl reload postfix
```

### 8. Deploy Frontend

```bash
# Serve via nginx with TLS
sudo apt install nginx certbot python3-certbot-nginx

sudo cp frontend/index.html /var/www/logging.email/index.html

# Configure nginx
sudo nano /etc/nginx/sites-available/logging.email
# Add proxy to backend API at api.logging.email

sudo certbot --nginx -d logging.email -d api.logging.email
sudo systemctl reload nginx
```

## Stripe Configuration

1. Create Stripe account
2. Create product and price
3. Configure webhook endpoint: `https://api.logging.email/billing/webhook`
4. Add webhook secret to backend.env
5. Test with Stripe CLI: `stripe listen --forward-to localhost:8000/billing/webhook`

## Monitoring

```bash
# Check services
sudo systemctl status backend
sudo systemctl status worker
sudo systemctl status policy-service
sudo systemctl status postfix

# View logs
sudo journalctl -u backend -f
sudo journalctl -u worker -f
sudo journalctl -u policy-service -f
sudo tail -f /var/log/postfix.log
```

## Testing

### Test Policy Service

```bash
# From MX host
echo -e "request=smtpd_access_policy\nrecipient=test@logging.email\n" | nc 127.0.0.1 10040
```

### Test Email Flow

```bash
# Send test email
echo "Test message" | mail -s "Test" <uuid>@logging.email

# Check queue
redis-cli LLEN email_processing

# Check database
mysql -u logging_email -p logging_email
SELECT * FROM messages ORDER BY received_at DESC LIMIT 5;
```

## Security Hardening

1. **Firewall**: Only ports 25, 80, 443 open on MX
2. **Fail2ban**: Configure for Postfix
3. **Rate limiting**: Cloudflare for frontend
4. **Backups**: Daily MySQL dumps, attachment storage
5. **Updates**: Automated security updates
6. **Monitoring**: Prometheus + Grafana

## Scaling

- **MX hosts**: Add more MX records, identical config
- **Workers**: Run multiple worker processes
- **Backend**: Run behind load balancer (nginx/HAProxy)
- **Database**: MySQL replication or managed service (RDS)
- **Queue**: Redis Cluster or managed service (ElastiCache)

## Retention Policy

Implement cron job to delete old messages:

```bash
# /etc/cron.daily/logging-email-cleanup
#!/bin/bash
mysql -u logging_email -p'PASSWORD' logging_email << EOF
DELETE m, a FROM messages m
LEFT JOIN attachments a ON m.id = a.message_id
JOIN email_addresses ea ON m.email_address_id = ea.id
JOIN customers c ON ea.customer_id = c.id
JOIN tier_limits tl ON c.tier = tl.tier
WHERE m.received_at < DATE_SUB(NOW(), INTERVAL tl.retention_days DAY);
EOF
```

## Troubleshooting

### Policy service not responding
- Check systemctl status
- Verify API token
- Test backend connectivity: `curl -H "X-API-Token: TOKEN" https://api.logging.email/policy/check`

### Emails not being processed
- Check Redis queue: `redis-cli LLEN email_processing`
- Check worker logs: `journalctl -u worker -f`
- Verify database connectivity

### Postfix rejecting all mail
- Check policy service: `systemctl status policy-service`
- Review Postfix logs: `tail -f /var/log/postfix.log`
- Test policy manually (see Testing section)
