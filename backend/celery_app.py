from celery import Celery
from config import settings

celery_app = Celery(
    'logging_email',
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=['tasks.email_tasks', 'tasks.maintenance_tasks']
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,
    task_soft_time_limit=240,
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
)

# Celery Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    'process-pending-emails': {
        'task': 'tasks.email_tasks.process_pending_emails_task',
        'schedule': 300.0,  # Every 5 minutes
    },
    'check-service-health': {
        'task': 'tasks.maintenance_tasks.check_service_health',
        'schedule': 60.0,  # Every minute
    },
    'cleanup-expired-emails': {
        'task': 'tasks.maintenance_tasks.cleanup_expired_emails',
        'schedule': 3600.0,  # Every hour
    },
    'cleanup-old-sessions': {
        'task': 'tasks.maintenance_tasks.cleanup_old_sessions',
        'schedule': 86400.0,  # Every day
    },
}
