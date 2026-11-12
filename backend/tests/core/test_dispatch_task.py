import os
from unittest.mock import Mock

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from app import tasks  # noqa: E402


def test_dispatch_task_reports_count_and_closes_session(monkeypatch):
    fake_db = Mock()
    monkeypatch.setattr(tasks, "SessionLocal", Mock(return_value=fake_db))
    dispatch = Mock(return_value=3)
    monkeypatch.setattr("app.core.scheduler.dispatch_due_schedules", dispatch)

    result = tasks.dispatch_due_schedules_task()

    assert result == {"dispatched": 3}
    dispatch.assert_called_once_with(fake_db)
    fake_db.close.assert_called_once()


def test_dispatch_task_closes_session_on_error(monkeypatch):
    fake_db = Mock()

    def boom(_db):
        raise RuntimeError("boom")

    monkeypatch.setattr(tasks, "SessionLocal", Mock(return_value=fake_db))
    monkeypatch.setattr("app.core.scheduler.dispatch_due_schedules", boom)

    with pytest.raises(RuntimeError):
        tasks.dispatch_due_schedules_task()

    fake_db.close.assert_called_once()
