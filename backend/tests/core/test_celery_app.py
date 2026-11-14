"""Guards so a missing Celery dependency is never silently masked."""

import pytest


def test_celery_app_is_real_when_celery_is_installed():
    pytest.importorskip("celery")

    from app.celery_app import celery_app

    # A dummy app here would mean an import inside celery_app.py failed and
    # was swallowed, which breaks workers in production.
    assert type(celery_app).__name__ != "_DummyCeleryApp"
    assert celery_app.main == "network_scanner"
    assert "dispatch-due-schedules" in celery_app.conf.beat_schedule
