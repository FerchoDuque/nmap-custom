"""Operational endpoints: health and basic metrics (PLAN-040)."""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.scan import Scan, ScanStatus

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Report API liveness and real database connectivity."""
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "database": "unavailable"},
        )

    return {"status": "healthy", "database": "connected"}


@router.get("/metrics")
def metrics(db: Session = Depends(get_db)):
    """Aggregate scan state for dashboards and smoke checks."""
    rows = db.query(Scan.status, func.count(Scan.id)).group_by(Scan.status).all()

    by_status = {}
    for status, count in rows:
        key = status.value if isinstance(status, ScanStatus) else str(status)
        by_status[key] = count

    hosts_up, ports_found = db.query(
        func.coalesce(func.sum(Scan.total_hosts_up), 0),
        func.coalesce(func.sum(Scan.total_ports_found), 0),
    ).one()

    active = by_status.get(ScanStatus.PENDING.value, 0) + by_status.get(
        ScanStatus.RUNNING.value, 0
    )

    return {
        "scans": {
            "total": sum(by_status.values()),
            "by_status": by_status,
            "active": active,
        },
        "hosts_up_total": int(hosts_up),
        "ports_found_total": int(ports_found),
    }
