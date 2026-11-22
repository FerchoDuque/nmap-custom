"""Retention policy for scan history.

Only scans in a terminal state are purged: deleting a `pending`/`running` scan
would race with a worker still writing progress. Children are removed
explicitly because SQLite does not enforce foreign keys by default.

`DATA_RETENTION_DAYS=0` disables the purge.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.scan import Port, Scan, ScanResult, ScanStatus

TERMINAL_STATUSES = (
    ScanStatus.COMPLETED,
    ScanStatus.FAILED,
    ScanStatus.CANCELLED,
)


def purge_expired_scans(
    session: Session,
    retention_days: Optional[int] = None,
    now: Optional[datetime] = None,
) -> int:
    """Delete terminal scans created before the retention cutoff.

    Returns the number of scans deleted.
    """
    days = settings.data_retention_days if retention_days is None else retention_days
    if days <= 0:
        return 0

    cutoff = (now or datetime.utcnow()) - timedelta(days=days)

    scan_ids = list(
        session.scalars(
            select(Scan.id).where(
                Scan.created_at < cutoff,
                Scan.status.in_(TERMINAL_STATUSES),
            )
        )
    )
    if not scan_ids:
        return 0

    result_ids = list(
        session.scalars(select(ScanResult.id).where(ScanResult.scan_id.in_(scan_ids)))
    )
    if result_ids:
        session.execute(delete(Port).where(Port.result_id.in_(result_ids)))
        session.execute(delete(ScanResult).where(ScanResult.id.in_(result_ids)))

    session.execute(delete(Scan).where(Scan.id.in_(scan_ids)))
    session.commit()

    return len(scan_ids)
