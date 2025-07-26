"""Celery application configuration for background tasks."""

from celery import Celery
from celery.signals import setup_logging

from app.settings import get_settings

settings = get_settings()

celery_app = Celery(
    "saber_build_system",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.infrastructure.tasks.build_tasks",
        "app.infrastructure.tasks.task_execution",
        "app.infrastructure.tasks.maintenance_tasks",
        "app.infrastructure.tasks.log_management",
    ],
)

celery_app.conf.update(
    task_routes={
        "app.infrastructure.tasks.build_tasks.*": {"queue": "builds"},
        "app.infrastructure.tasks.task_execution.*": {"queue": "execution"},
        "app.infrastructure.tasks.maintenance_tasks.*": {"queue": "maintenance"},
        "app.infrastructure.tasks.log_management.*": {"queue": "maintenance"},
    },
    
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=1000,
    
    result_expires=3600,  # 1 hour
    result_backend_transport_options={
        "retry_policy": {
            "timeout": 5.0,
        },
    },
    
    task_default_retry_delay=60,  # 1 minute
    task_max_retries=3,
    
    worker_send_task_events=True,
    task_send_sent_event=True,
    
    beat_schedule={
        "cleanup-expired-tokens": {
            "task": "app.infrastructure.tasks.maintenance_tasks.cleanup_expired_tokens",
            "schedule": 3600.0,  # Every hour
        },
        "cleanup-old-build-results": {
            "task": "app.infrastructure.tasks.maintenance_tasks.cleanup_old_build_results",
            "schedule": 86400.0,  # Every day
        },
        "health-check-services": {
            "task": "app.infrastructure.tasks.maintenance_tasks.health_check_services",
            "schedule": 300.0,  # Every 5 minutes
        },
    },
)


@setup_logging.connect
def config_loggers(*args, **kwargs):
    """Configure Celery logging."""
    from logging.config import dictConfig
    from app.utils.logging import get_logging_config
    
    dictConfig(get_logging_config())


celery_app.autodiscover_tasks([
    "app.infrastructure.tasks",
])


def get_celery_app() -> Celery:
    """
    Get configured Celery application.
    
    Returns:
        Celery: Configured Celery application
    """
    return celery_app