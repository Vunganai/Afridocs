"""
Celery application factory.
"""

from celery import Celery

from app.core.config import get_settings


def create_celery_app() -> Celery:
    settings = get_settings()

    app = Celery(
        "afridocs",
        broker=settings.celery_broker_url,
        backend=settings.celery_result_backend,
        include=["app.worker.tasks.process_document"],
    )

    app.conf.update(
        # Serialisation
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        # Timezones
        timezone="Africa/Johannesburg",
        enable_utc=True,
        # Reliability
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        task_track_started=True,
        # Queues
        task_default_queue="documents",
        task_queues={
            "documents": {"exchange": "documents", "routing_key": "documents"},
        },
        # Results TTL
        result_expires=86400,  # 24 hours
        # Rate limiting
        task_annotations={
            "app.worker.tasks.process_document.process_invoice": {
                "rate_limit": "30/m",  # 30 invoices/minute per worker
            }
        },
    )

    return app


celery_app = create_celery_app()
