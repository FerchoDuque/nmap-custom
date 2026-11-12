import os
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from app.core.scheduler import (  # noqa: E402
    _scan_from_schedule,
    compute_next_run,
    dispatch_due_schedules,
)
from app.database import Base  # noqa: E402
from app.models.scan import Scan, ScanStatus, ScanType, Schedule  # noqa: E402

NOW = datetime(2026, 11, 11, 12, 0, 0)


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def _make_schedule(db, **overrides):
    values = {
        "name": "nightly",
        "scan_config": {"target": "192.168.1.0/24", "scan_type": "tcp_connect"},
        "cron_expression": "*/5 * * * *",
        "enabled": True,
        "next_run_at": NOW - timedelta(minutes=1),
    }
    values.update(overrides)
    schedule = Schedule(**values)
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return schedule


class TestComputeNextRun:
    def test_next_interval_within_the_hour(self):
        assert compute_next_run("*/5 * * * *", NOW) == datetime(2026, 11, 11, 12, 5)

    def test_next_daily_run(self):
        assert compute_next_run("0 3 * * *", NOW) == datetime(2026, 11, 12, 3, 0)

    def test_invalid_cron_raises_value_error(self):
        with pytest.raises(ValueError):
            compute_next_run("not a cron", NOW)


class TestScanFromSchedule:
    def test_maps_scan_config_fields(self):
        schedule = Schedule(
            id=1,
            name="nightly",
            scan_config={
                "target": " 10.0.0.0/24 ",
                "scan_type": "udp",
                "port_range": "53,123",
                "service_detection": False,
                "os_detection": True,
                "aggressive": True,
            },
            cron_expression="0 3 * * *",
            enabled=True,
        )

        scan = _scan_from_schedule(schedule, NOW)

        assert scan.target == "10.0.0.0/24"
        assert scan.scan_type == ScanType.UDP
        assert scan.port_range == "53,123"
        assert scan.service_detection is False
        assert scan.os_detection is True
        assert scan.aggressive is True
        assert scan.status == ScanStatus.PENDING
        assert scan.name == "nightly @ 2026-11-11 12:00"

    def test_rejects_missing_target(self):
        schedule = Schedule(
            id=1,
            name="broken",
            scan_config={"scan_type": "tcp_connect"},
            cron_expression="* * * * *",
            enabled=True,
        )

        with pytest.raises(ValueError, match="target"):
            _scan_from_schedule(schedule, NOW)


class TestDispatchDueSchedules:
    def test_dispatches_due_schedule_and_advances_it(self, db_session):
        schedule = _make_schedule(db_session)
        enqueue = Mock(return_value=SimpleNamespace(id="task-1"))

        dispatched = dispatch_due_schedules(db_session, now=NOW, enqueue=enqueue)

        assert dispatched == 1
        scan = db_session.query(Scan).one()
        assert scan.target == "192.168.1.0/24"
        assert scan.status == ScanStatus.PENDING
        assert scan.task_id == "task-1"
        enqueue.assert_called_once_with(scan.id)

        db_session.refresh(schedule)
        assert schedule.total_runs == 1
        assert schedule.successful_runs == 1
        assert schedule.failed_runs == 0
        assert schedule.last_run_at == NOW
        assert schedule.next_run_at == NOW + timedelta(minutes=5)

    def test_skips_disabled_and_future_schedules(self, db_session):
        _make_schedule(db_session, name="disabled", enabled=False)
        _make_schedule(
            db_session,
            name="future",
            next_run_at=NOW + timedelta(hours=1),
        )
        enqueue = Mock(return_value=SimpleNamespace(id="task-x"))

        dispatched = dispatch_due_schedules(db_session, now=NOW, enqueue=enqueue)

        assert dispatched == 0
        assert db_session.query(Scan).count() == 0
        enqueue.assert_not_called()

    def test_is_idempotent_across_dispatches(self, db_session):
        _make_schedule(db_session)
        enqueue = Mock(return_value=SimpleNamespace(id="task-1"))

        first = dispatch_due_schedules(db_session, now=NOW, enqueue=enqueue)
        second = dispatch_due_schedules(db_session, now=NOW, enqueue=enqueue)

        assert first == 1
        assert second == 0
        assert db_session.query(Scan).count() == 1
        assert enqueue.call_count == 1

    def test_dispatches_multiple_due_schedules(self, db_session):
        _make_schedule(db_session, name="first")
        _make_schedule(db_session, name="second", cron_expression="0 * * * *")
        enqueue = Mock(side_effect=[SimpleNamespace(id="t1"), SimpleNamespace(id="t2")])

        dispatched = dispatch_due_schedules(db_session, now=NOW, enqueue=enqueue)

        assert dispatched == 2
        assert db_session.query(Scan).count() == 2
        assert enqueue.call_count == 2

    def test_enqueue_failure_marks_scan_failed_and_counts_failure(self, db_session):
        schedule = _make_schedule(db_session)
        enqueue = Mock(side_effect=RuntimeError("broker down"))

        dispatched = dispatch_due_schedules(db_session, now=NOW, enqueue=enqueue)

        assert dispatched == 0
        scan = db_session.query(Scan).one()
        assert scan.status == ScanStatus.FAILED
        assert "broker down" in scan.error_message
        assert scan.completed_at is not None

        db_session.refresh(schedule)
        assert schedule.total_runs == 1
        assert schedule.successful_runs == 0
        assert schedule.failed_runs == 1
        assert schedule.next_run_at == NOW + timedelta(minutes=5)

    def test_invalid_scan_config_advances_and_counts_failure(self, db_session):
        schedule = _make_schedule(db_session, scan_config={})
        enqueue = Mock()

        dispatched = dispatch_due_schedules(db_session, now=NOW, enqueue=enqueue)

        assert dispatched == 0
        assert db_session.query(Scan).count() == 0
        enqueue.assert_not_called()

        db_session.refresh(schedule)
        assert schedule.total_runs == 1
        assert schedule.failed_runs == 1
        assert schedule.next_run_at == NOW + timedelta(minutes=5)

    def test_invalid_cron_disables_schedule(self, db_session):
        schedule = _make_schedule(db_session, cron_expression="bad cron")
        enqueue = Mock()

        dispatched = dispatch_due_schedules(db_session, now=NOW, enqueue=enqueue)

        assert dispatched == 0
        assert db_session.query(Scan).count() == 0

        db_session.refresh(schedule)
        assert schedule.enabled is False
        assert schedule.next_run_at is None
        assert schedule.total_runs == 0
