from celery import Celery

from app.core.config import settings

# Initialize Celery for async processing
celery_app = Celery(
    "hrms_bot",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    enable_utc=True,
    timezone="UTC",
)

# Import tasks here to ensure Celery knows about them
# Import the task module directly
# from app.tasks.process_doc import process_document_task  # <-- This is critical

# Make sure Celery uses the config
# celery_app.config_from_object('celeryconfig')

# Auto-discover tasks across all registered app namespaces
celery_app.autodiscover_tasks(["app.workers.process_doc"])
