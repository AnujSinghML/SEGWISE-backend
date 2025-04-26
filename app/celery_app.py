from celery import Celery
from app.config import settings


celery_app = Celery(
    "webhook_delivery_service",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.tasks"]
)


# Celery Config
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_max_tasks_per_child=1000,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_time_limit=300,
    broker_connection_retry_on_startup=True,
    broker_connection_timeout=10,
)

celery_app.conf.beat_schedule = {
    'cleanup-old-logs': {
        'task': 'app.workers.tasks.cleanup_old_webhook_logs',  # Task function
        'schedule': 3600.0,  # Run every hour (3600 seconds)
    },
}