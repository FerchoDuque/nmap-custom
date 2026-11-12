"""Scheduled scan dispatch (DEC-008).

The database is the source of truth: a periodic Celery Beat task claims due
schedules, creates a pending Scan using the schedule's stored configuration and
enqueues the regular scan task. Claims are conditional updates on
``next_run_at`` so concurrent beat/worker instances cannot double-dispatch.
"""

import logging
from datetime import datetime
from typing import Callable, Optional

from croniter import croniter
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.scan import Scan, ScanStatus, ScanType, Schedule

logger = logging.getLogger(__name__)

EnqueueCallable = Callable[[int], object]


def compute_next_run(
    cron_expression: str, base: Optional[datetime] = None
) -> datetime:
    """Return the next UTC (naive) run time after ``base`` for a cron expression."""
    reference = base or datetime.utcnow()
    if not croniter.is_valid(cron_expression):
        raise ValueError(f"Invalid cron expression: {cron_expression!r}")
    return croniter(cron_expression, reference).get_next(datetime)


def _scan_from_schedule(schedule: Schedule, reference: datetime) -> Scan:
    """Build an unsaved Scan from a schedule's JSON configuration."""
    config = schedule.scan_config or {}
    if not isinstance(config, dict):
        raise ValueError("scan_config must be an object")

    target = config.get("target")
    if not isinstance(target, str) or not target.strip():
        raise ValueError("scan_config.target is required")

    raw_scan_type = config.get("scan_type", ScanType.TCP_CONNECT.value)
    try:
        scan_type = ScanType(raw_scan_type)
    except ValueError as exc:
        raise ValueError(f"Unsupported scan_type: {raw_scan_type!r}") from exc

    return Scan(
        name=config.get("name") or f"{schedule.name} @ {reference:%Y-%m-%d %H:%M}",
        target=target.strip(),
        scan_type=scan_type,
        port_range=config.get("port_range"),
        service_detection=config.get("service_detection", True),
        os_detection=config.get("os_detection", False),
        aggressive=config.get("aggressive", False),
        status=ScanStatus.PENDING,
    )


def _claim_schedule(
    db: Session,
    schedule: Schedule,
    previous_next_run: datetime,
    next_run: datetime,
    reference: datetime,
) -> bool:
    """Advance and count a schedule atomically. Returns False if already claimed."""
    claimed = (
        db.query(Schedule)
        .filter(
            Schedule.id == schedule.id,
            Schedule.enabled.is_(True),
            Schedule.next_run_at == previous_next_run,
        )
        .update(
            {
                Schedule.next_run_at: next_run,
                Schedule.last_run_at: reference,
                Schedule.updated_at: reference,
                Schedule.total_runs: func.coalesce(Schedule.total_runs, 0) + 1,
            },
            synchronize_session=False,
        )
    )
    db.commit()
    return claimed == 1


def _increment_failed(db: Session, schedule_id: int) -> None:
    db.query(Schedule).filter(Schedule.id == schedule_id).update(
        {
            Schedule.failed_runs: func.coalesce(Schedule.failed_runs, 0) + 1,
            Schedule.updated_at: datetime.utcnow(),
        },
        synchronize_session=False,
    )
    db.commit()


def dispatch_due_schedules(
    db: Session,
    now: Optional[datetime] = None,
    enqueue: Optional[EnqueueCallable] = None,
) -> int:
    """Dispatch every enabled schedule whose ``next_run_at`` is due.

    Returns the number of scans successfully enqueued. ``enqueue`` defaults to
    ``perform_scan_task.delay`` and is injectable for deterministic tests.
    """
    reference = now or datetime.utcnow()

    if enqueue is None:
        from app.tasks import perform_scan_task

        enqueue = perform_scan_task.delay

    due_schedules = (
        db.query(Schedule)
        .filter(
            Schedule.enabled.is_(True),
            Schedule.next_run_at.isnot(None),
            Schedule.next_run_at <= reference,
        )
        .order_by(Schedule.next_run_at.asc())
        .all()
    )

    dispatched = 0

    for schedule in due_schedules:
        previous_next_run = schedule.next_run_at

        try:
            next_run = compute_next_run(schedule.cron_expression, reference)
        except ValueError:
            logger.error(
                "Disabling schedule %s: invalid cron expression %r",
                schedule.id,
                schedule.cron_expression,
            )
            db.query(Schedule).filter(Schedule.id == schedule.id).update(
                {
                    Schedule.enabled: False,
                    Schedule.next_run_at: None,
                    Schedule.updated_at: reference,
                },
                synchronize_session=False,
            )
            db.commit()
            continue

        # Validate configuration before claiming so bad schedules still advance
        # (and are counted as failed) instead of blocking the queue forever.
        try:
            scan = _scan_from_schedule(schedule, reference)
        except ValueError as exc:
            if _claim_schedule(db, schedule, previous_next_run, next_run, reference):
                _increment_failed(db, schedule.id)
            logger.error("Schedule %s has invalid scan_config: %s", schedule.id, exc)
            continue

        if not _claim_schedule(db, schedule, previous_next_run, next_run, reference):
            logger.info("Schedule %s already claimed by another dispatcher", schedule.id)
            continue

        try:
            db.add(scan)
            db.commit()
            db.refresh(scan)

            result = enqueue(scan.id)
            task_id = getattr(result, "id", None)
            if task_id:
                scan.task_id = task_id
                db.commit()

            db.query(Schedule).filter(Schedule.id == schedule.id).update(
                {
                    Schedule.successful_runs: func.coalesce(Schedule.successful_runs, 0) + 1,
                },
                synchronize_session=False,
            )
            db.commit()
            dispatched += 1
            logger.info("Dispatched schedule %s as scan %s", schedule.id, scan.id)
        except Exception as exc:  # noqa: BLE001 - never let one schedule stop the batch
            logger.error("Failed to dispatch schedule %s: %s", schedule.id, exc)
            db.rollback()
            if scan.id is not None:
                db.query(Scan).filter(Scan.id == scan.id).update(
                    {
                        Scan.status: ScanStatus.FAILED,
                        Scan.error_message: f"Failed to enqueue scheduled scan: {exc}",
                        Scan.completed_at: datetime.utcnow(),
                    },
                    synchronize_session=False,
                )
            db.commit()
            _increment_failed(db, schedule.id)

    db.expire_all()
    return dispatched
