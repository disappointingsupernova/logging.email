# Celery Deployment Guide

## Overview

Celery handles asynchronous tasks for logging.email:
- Email sending with retry logic
- Service health monitoring
- Periodic maintenance tasks
- Session cleanup

## Architecture

```
FastAPI App → Celery Tasks → Redis (Broker) → Celery Workers
                                    ↓
                              Celery Beat (Scheduler)
```

## Redis Configuration

Celery uses a separate Redis database from the cache:
- **Cache**: `redis://localhost:6379/0`
- **Celery**: `redis://localhost:6379/1`

This allows independent scaling and prevents cache eviction from affecting task queue.

## Installation

### 1. Install Dependencies
```bash
pip install celery==5.3.4 redis==5.0.1
```

### 2. Configure Environment
```bash
# .env
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/1
```

### 3. Test Celery
```bash
# Start worker
celery -A celery_app worker --loglevel=info

# Start beat scheduler (separate terminal)
celery -A celery_app beat --loglevel=info
```

## Production Deployment

### Option 1: Same Server as Backend

**Advantages:**
- Simpler deployment
- Shared resources
- Lower latency

**Setup:**
```bash
# Copy systemd service files
sudo cp celery-worker.service /etc/systemd/system/
sudo cp celery-beat.service /etc/systemd/system/

# Create log directory
sudo mkdir -p /var/log/celery
sudo chown www-data:www-data /var/log/celery

# Create PID directory
sudo mkdir -p /var/run/celery
sudo chown www-data:www-data /var/run/celery

# Enable and start services
sudo systemctl daemon-reload
sudo systemctl enable celery-worker celery-beat
sudo systemctl start celery-worker celery-beat

# Check status
sudo systemctl status celery-worker
sudo systemctl status celery-beat
```

### Option 2: Dedicated Worker Server

**Advantages:**
- Better resource isolation
- Independent scaling
- Reduced backend server load

**Setup on Worker Server:**
```bash
# 1. Clone repository
git clone https://github.com/yourusername/logging.email.git
cd logging.email/backend

# 2. Install dependencies
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Configure .env (only Celery and database settings needed)
cp .env.example .env
# Edit: CELERY_BROKER_URL, DB_*, MONGODB_*, SMTP_*

# 4. Install systemd services
sudo cp celery-worker.service /etc/systemd/system/
sudo cp celery-beat.service /etc/systemd/system/

# Update WorkingDirectory in service files to match your path

# 5. Start services
sudo systemctl daemon-reload
sudo systemctl enable celery-worker celery-beat
sudo systemctl start celery-worker celery-beat
```

## Scaling Workers

### Multiple Workers on Same Server
```bash
# Edit celery-worker.service
ExecStart=/path/to/venv/bin/celery -A celery_app worker --concurrency=4 --loglevel=info

# Or run multiple instances
sudo systemctl start celery-worker@1
sudo systemctl start celery-worker@2
```

### Multiple Worker Servers
Simply deploy the worker setup on multiple servers pointing to the same Redis broker.

## Monitoring

### Check Worker Status
```bash
# View logs
sudo journalctl -u celery-worker -f
sudo journalctl -u celery-beat -f

# Or log files
tail -f /var/log/celery/worker.log
tail -f /var/log/celery/beat.log
```

### Celery Flower (Web UI)
```bash
# Install
pip install flower

# Run
celery -A celery_app flower --port=5555

# Access at http://localhost:5555
```

### Monitor Tasks
```python
from celery_app import celery_app

# Inspect active tasks
i = celery_app.control.inspect()
print(i.active())
print(i.scheduled())
print(i.reserved())
```

## Task Configuration

### Scheduled Tasks (Celery Beat)

Configured in `celery_app.py`:
- **process-pending-emails**: Every 5 minutes
- **check-service-health**: Every minute
- **cleanup-expired-emails**: Every hour
- **cleanup-old-sessions**: Every day

### Manual Task Execution

```python
from tasks.email_tasks import send_email_task, retry_failed_email
from tasks.maintenance_tasks import check_service_health

# Send email immediately
send_email_task.delay(email_id=123)

# Retry failed email
retry_failed_email.delay(email_id=456)

# Check health
check_service_health.delay()
```

## Troubleshooting

### Worker Not Processing Tasks
```bash
# Check Redis connection
redis-cli -n 1 ping

# Check worker is running
ps aux | grep celery

# Check for errors
sudo journalctl -u celery-worker -n 100
```

### Tasks Stuck in Queue
```bash
# Purge all tasks (CAUTION)
celery -A celery_app purge

# Inspect queue
redis-cli -n 1 LLEN celery
```

### High Memory Usage
```bash
# Restart worker
sudo systemctl restart celery-worker

# Or configure max tasks per child
# In celery_app.py:
worker_max_tasks_per_child=1000
```

### Email Tasks Failing
```bash
# Check SMTP configuration
# Check outbound_emails table for error messages
SELECT * FROM outbound_emails WHERE status = 'failed' ORDER BY created_at DESC LIMIT 10;

# Manually retry
curl -X POST http://localhost:8000/admin/emails/123/retry \
  -H "Authorization: Bearer TOKEN"
```

## Performance Tuning

### Worker Concurrency
```bash
# CPU-bound tasks
celery -A celery_app worker --concurrency=4

# I/O-bound tasks (emails, API calls)
celery -A celery_app worker --concurrency=10
```

### Task Priorities
```python
# In celery_app.py
task_routes = {
    'tasks.email_tasks.send_email_task': {'queue': 'high_priority'},
    'tasks.maintenance_tasks.*': {'queue': 'low_priority'},
}

# Start workers for specific queues
celery -A celery_app worker -Q high_priority --concurrency=8
celery -A celery_app worker -Q low_priority --concurrency=2
```

### Redis Optimization
```bash
# In redis.conf
maxmemory 2gb
maxmemory-policy allkeys-lru
```

## Security

### Network Isolation
```bash
# Bind Redis to localhost only
# In redis.conf:
bind 127.0.0.1

# Or use firewall
sudo ufw allow from WORKER_IP to any port 6379
```

### Authentication
```bash
# Set Redis password
# In redis.conf:
requirepass YOUR_STRONG_PASSWORD

# Update .env:
CELERY_BROKER_URL=redis://:YOUR_STRONG_PASSWORD@localhost:6379/1
```

## Backup & Recovery

### Task Queue Backup
Redis persistence handles this automatically with RDB/AOF.

### Failed Task Recovery
```sql
-- Find failed emails
SELECT * FROM outbound_emails WHERE status = 'failed' AND attempts < max_attempts;

-- Reset for retry
UPDATE outbound_emails SET status = 'pending', next_retry_at = NOW() WHERE id = ?;
```

## Maintenance

### Restart Services
```bash
sudo systemctl restart celery-worker
sudo systemctl restart celery-beat
```

### Update Code
```bash
cd /var/www/logging.email/backend
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart celery-worker celery-beat
```

### View Metrics
```bash
# Task success/failure rates
celery -A celery_app inspect stats

# Active workers
celery -A celery_app inspect active_queues
```
