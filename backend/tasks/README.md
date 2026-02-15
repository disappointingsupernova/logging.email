# Celery Tasks

All background processing is handled by Celery workers.

## Task Modules

### email_tasks.py
- `send_email_task(email_id)` - Send single email with retry
- `process_pending_emails_task()` - Process all pending emails (scheduled every 5 min)
- `retry_failed_email(email_id)` - Manually retry failed email

### maintenance_tasks.py
- `check_service_health()` - Monitor service health (scheduled every 1 min)
- `cleanup_expired_emails()` - Remove expired emails (scheduled hourly)
- `cleanup_old_sessions()` - Remove old sessions (scheduled daily)

## Running Celery

### Development
```bash
# Worker
celery -A celery_app worker --loglevel=info

# Beat scheduler (separate terminal)
celery -A celery_app beat --loglevel=info
```

### Production
```bash
# Install systemd services
sudo cp celery-worker.service /etc/systemd/system/
sudo cp celery-beat.service /etc/systemd/system/

# Start services
sudo systemctl start celery-worker celery-beat
sudo systemctl enable celery-worker celery-beat
```

## Monitoring

### Flower (Web UI)
```bash
pip install flower
celery -A celery_app flower --port=5555
# Access at http://localhost:5555
```

### CLI
```bash
# Inspect active tasks
celery -A celery_app inspect active

# View stats
celery -A celery_app inspect stats

# Purge all tasks (CAUTION)
celery -A celery_app purge
```

## Manual Task Execution

```python
from tasks.email_tasks import send_email_task, retry_failed_email
from tasks.maintenance_tasks import check_service_health

# Queue email for sending
send_email_task.delay(email_id=123)

# Retry failed email
retry_failed_email.delay(email_id=456)

# Check health
check_service_health.delay()
```

## Configuration

Edit `celery_app.py` to modify:
- Task schedules (beat_schedule)
- Worker concurrency
- Task time limits
- Queue routing

See [docs/CELERY.md](../docs/CELERY.md) for full documentation.
