import os
from celery import Celery
from app.config import settings

# We use the Redis service name defined in docker-compose
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

celery_app = Celery(
    "pdf_video_worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.tasks"]  
)

# Configure Celery to respect your project settings
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # If the worker crashes, the task is not lost
    task_acks_late=True,
)