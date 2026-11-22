"""Retention deletes only old, finished scans and their children."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app import models  # noqa: F401  (registers tables)
from app.core.retention import purge_expired_scans
from app.database import Base
from app.models.scan import Port, PortState, Scan, ScanResult, ScanStatus, ScanType

NOW = datetime(2026, 11, 21, 12, 0, 0)


@pytest.fixture()
def session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine)
    db = factory()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


def _scan(db, *, days_ago: float, status=ScanStatus.COMPLETED, with_port=False) -> Scan:
    scan = Scan(
        target="192.168.1.0/24",
        scan_type=ScanType.TCP_CONNECT,
        status=status,
        created_at=NOW - timedelta(days=days_ago),
    )
    db.add(scan)
    db.flush()

    result = ScanResult(scan_id=scan.id, ip_address="192.168.1.10", is_up=True)
    db.add(result)
    db.flush()

    if with_port:
        db.add(
            Port(
                result_id=result.id,
                port_number=22,
                protocol="tcp",
                state=PortState.OPEN,
            )
        )
    db.commit()
    return scan


def _count(db, model) -> int:
    return db.scalar(select(func.count()).select_from(model))


def test_deletes_old_terminal_scans_with_children(session):
    old = _scan(session, days_ago=31, with_port=True)
    old_id = old.id

    deleted = purge_expired_scans(session, retention_days=30, now=NOW)

    assert deleted == 1
    assert session.get(Scan, old_id) is None
    assert _count(session, ScanResult) == 0
    assert _count(session, Port) == 0


def test_keeps_scans_inside_the_window(session):
    _scan(session, days_ago=29, with_port=True)

    assert purge_expired_scans(session, retention_days=30, now=NOW) == 0
    assert _count(session, Scan) == 1
    assert _count(session, Port) == 1


@pytest.mark.parametrize(
    "status", [ScanStatus.PENDING, ScanStatus.RUNNING]
)
def test_never_deletes_unfinished_scans(session, status):
    _scan(session, days_ago=365, status=status)

    assert purge_expired_scans(session, retention_days=30, now=NOW) == 0
    assert _count(session, Scan) == 1


def test_zero_or_negative_retention_disables_the_purge(session):
    _scan(session, days_ago=365)

    assert purge_expired_scans(session, retention_days=0, now=NOW) == 0
    assert purge_expired_scans(session, retention_days=-5, now=NOW) == 0
    assert _count(session, Scan) == 1


def test_uses_configured_retention_days_by_default(session, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "data_retention_days", 7)
    _scan(session, days_ago=8)
    _scan(session, days_ago=6)

    assert purge_expired_scans(session, now=NOW) == 1
    assert _count(session, Scan) == 1
