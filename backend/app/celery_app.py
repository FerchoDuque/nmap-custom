from app.config import settings

try:
    from celery import Celery

    # Create Celery app
    celery_app = Celery(
        "network_scanner",
        broker=settings.celery_broker_url,
        backend=settings.celery_result_backend
    )

    # Configure Celery
    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_time_limit=3600,  # 1 hour max
        task_soft_time_limit=3300,  # 55 minutes soft limit
        beat_schedule={
            "dispatch-due-schedules": {
                "task": "app.tasks.dispatch_due_schedules_task",
                "schedule": 60.0,
            },
        },
    )

    # Autodiscover tasks from app.tasks module
    celery_app.autodiscover_tasks(['app.tasks'])

    # Import tasks to ensure they're registered
    from app import tasks  # noqa: F401, E402
except ImportError:
    # Fallback for test environments without Celery installed.
    class _DummyControl:
        def revoke(self, *args, **kwargs):
            return None

    class _DummyCeleryApp:
        control = _DummyControl()

        def task(self, *args, **kwargs):
            # Mirror Celery's `@app.task` and `@app.task(...)` usage.
            if len(args) == 1 and callable(args[0]) and not kwargs:
                return args[0]

            def decorator(func):
                return func
            return decorator

        def autodiscover_tasks(self, *args, **kwargs):
            return None

        @property
        def conf(self):
            return self

        def update(self, *args, **kwargs):
            return None

    celery_app = _DummyCeleryApp()
