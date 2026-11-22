import asyncio
from datetime import datetime
from typing import Callable, Dict, Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models.scan import Scan, ScanResult, Port, ScanStatus
from app.core.logging_utils import get_scan_logger
from app.core.scanner import NetworkScanner

try:
    from app.celery_app import celery_app
except Exception:  # pragma: no cover - test fallback
    celery_app = None


TERMINAL_STATUSES = {
    ScanStatus.COMPLETED,
    ScanStatus.FAILED,
    ScanStatus.CANCELLED,
}

ERROR_MESSAGE_LIMIT = 500


class ScanTimeoutError(RuntimeError):
    """Raised when a scan exceeds the configured wall-clock budget."""


def _task_decorator(*dargs, **dkwargs):
    if celery_app is not None and hasattr(celery_app, "task"):
        return celery_app.task(*dargs, **dkwargs)

    def decorator(func):
        return func

    return decorator


def _safe_error_message(exc: Exception) -> str:
    """Return an actionable but non-sensitive message for persistence."""
    if isinstance(exc, SQLAlchemyError):
        return "Scan failed due to a database error"

    message = str(exc).strip() or exc.__class__.__name__
    return message[:ERROR_MESSAGE_LIMIT]


def _timeout_message(timeout: float) -> str:
    return f"Scan exceeded the configured timeout of {timeout:g}s"


def execute_scan(
    db: Session,
    scan_id: int,
    task_id: Optional[str] = None,
    scanner: Optional[NetworkScanner] = None,
    update_state: Optional[Callable[..., None]] = None,
    timeout: Optional[float] = None,
) -> Dict:
    """Run one scan synchronously with bounded time and idempotent semantics.

    - Terminal scans (completed/failed/cancelled) are skipped so a duplicated
      Celery delivery cannot re-run finished work.
    - The scan is aborted after ``timeout`` seconds (default
      ``settings.default_scan_timeout``) and marked as failed.
    - Persisted error messages are truncated and never include tracebacks or
      database internals.

    ``scanner`` and ``update_state`` are injectable for deterministic tests.
    """
    scan_log = get_scan_logger(scan_id, task_id=task_id)
    timeout = settings.default_scan_timeout if timeout is None else timeout

    scan = db.query(Scan).filter(Scan.id == scan_id).first()

    if not scan:
        scan_log.error("Scan not found", extra={"event": "scan.not_found"})
        return {"scan_id": scan_id, "status": "not_found"}

    if scan.status in TERMINAL_STATUSES:
        scan_log.info(
            "Skipping scan in terminal state",
            extra={
                "event": "scan.skipped",
                "status": getattr(scan.status, "value", str(scan.status)),
            },
        )
        return {"scan_id": scan_id, "status": "skipped"}

    scan.status = ScanStatus.RUNNING
    scan.started_at = datetime.utcnow()
    scan.task_id = task_id
    db.commit()
    scan_log.info("Scan started", extra={"event": "scan.started"})

    scanner = scanner or NetworkScanner()

    async def progress_callback(update: dict):
        """Persist progress; a failure here must not abort the scan."""
        try:
            scan.progress = update.get("progress", scan.progress)
            scan.current_host = update.get("current_host", scan.current_host)
            scan.hosts_scanned = update.get("hosts_scanned", scan.hosts_scanned)
            db.commit()

            if update_state is not None:
                update_state(
                    state="PROGRESS",
                    meta={
                        "progress": scan.progress,
                        "current_host": scan.current_host,
                        "message": update.get("message", ""),
                    },
                )
        except Exception as exc:  # noqa: BLE001 - progress must never abort
            scan_log.error(
                "Error updating progress: %s",
                exc,
                extra={"event": "scan.progress_error"},
            )

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        results = loop.run_until_complete(
            asyncio.wait_for(
                scanner.scan(
                    target=scan.target,
                    scan_type=scan.scan_type,
                    port_range=scan.port_range,
                    service_detection=scan.service_detection,
                    os_detection=scan.os_detection,
                    progress_callback=progress_callback,
                ),
                timeout=timeout,
            )
        )
    except Exception as exc:  # noqa: BLE001 - persist failure then re-raise
        deadline_exceeded = isinstance(exc, asyncio.TimeoutError)
        try:
            failed = db.query(Scan).filter(Scan.id == scan_id).first()
            if failed is not None:
                failed.status = ScanStatus.FAILED
                failed.error_message = (
                    _timeout_message(timeout)
                    if deadline_exceeded
                    else _safe_error_message(exc)
                )
                failed.completed_at = datetime.utcnow()
                db.commit()
        except Exception as persist_error:  # noqa: BLE001 - best effort
            db.rollback()
            scan_log.error(
                "Error persisting scan failure: %s",
                persist_error,
                extra={"event": "scan.persist_error"},
            )

        if deadline_exceeded:
            scan_log.error(
                "Scan timed out",
                extra={"event": "scan.timeout", "status": "failed"},
            )
            raise ScanTimeoutError(_timeout_message(timeout)) from exc

        scan_log.error(
            "Scan failed: %s",
            exc,
            extra={"event": "scan.failed", "status": "failed"},
        )
        raise
    finally:
        loop.close()
        asyncio.set_event_loop(None)

    # Persist successful results
    scan.hosts_total = results["hosts_total"]
    scan.total_hosts_up = results["hosts_up"]
    scan.total_ports_found = results["total_ports_found"]

    for host_result in results["results"]:
        scan_result = ScanResult(
            scan_id=scan.id,
            ip_address=host_result["ip_address"],
            hostname=host_result.get("hostname"),
            is_up=host_result["is_up"],
            os_name=host_result.get("os_name"),
            os_accuracy=host_result.get("os_accuracy"),
            os_details=host_result.get("os_details"),
            scanned_at=datetime.utcnow(),
        )
        db.add(scan_result)
        db.flush()  # Get scan_result.id

        for port_info in host_result.get("ports", []):
            db.add(
                Port(
                    result_id=scan_result.id,
                    port_number=port_info["port_number"],
                    protocol=port_info["protocol"],
                    state=port_info["state"],
                    service_name=port_info.get("service_name"),
                    service_product=port_info.get("service_product"),
                    service_version=port_info.get("service_version"),
                    banner=port_info.get("banner"),
                )
            )

    scan.status = ScanStatus.COMPLETED
    scan.completed_at = datetime.utcnow()
    scan.progress = 100
    db.commit()

    scan_log.info(
        "Scan completed",
        extra={
            "event": "scan.completed",
            "status": "completed",
            "hosts_found": results["hosts_up"],
            "hosts_failed": results.get("hosts_failed", 0),
            "ports_found": results["total_ports_found"],
        },
    )

    return {
        "scan_id": scan_id,
        "status": "completed",
        "hosts_up": results["hosts_up"],
        "ports_found": results["total_ports_found"],
    }


@_task_decorator(bind=True)
def perform_scan_task(self, scan_id: int):
    """Celery task wrapper around :func:`execute_scan`."""
    db = SessionLocal()
    task_id = getattr(getattr(self, "request", None), "id", None)
    update_state = getattr(self, "update_state", None)

    try:
        return execute_scan(
            db,
            scan_id,
            task_id=task_id,
            update_state=update_state,
        )
    finally:
        db.close()


@_task_decorator
def dispatch_due_schedules_task():
    """Celery Beat entrypoint that dispatches due scheduled scans (DEC-008)."""
    # Imported lazily so the task module and scheduler stay import-cycle free.
    from app.core.scheduler import dispatch_due_schedules

    db = SessionLocal()
    try:
        return {"dispatched": dispatch_due_schedules(db)}
    finally:
        db.close()


@_task_decorator
def purge_expired_scans_task():
    """Celery Beat entrypoint applying DATA_RETENTION_DAYS (PLAN-062)."""
    from app.core.retention import purge_expired_scans

    db = SessionLocal()
    try:
        return {"deleted_scans": purge_expired_scans(db)}
    finally:
        db.close()
