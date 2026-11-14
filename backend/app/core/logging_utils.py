"""Structured logging helpers with scan/task correlation.

Output is one JSON object per line so logs can be shipped and filtered by
``scan_id``/``task_id``. No external dependencies are required.
"""

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# Correlation and operation fields copied from ``LogRecord.extra``.
EXTRA_FIELDS = (
    "scan_id",
    "task_id",
    "event",
    "status",
    "duration_ms",
    "hosts_found",
    "ports_found",
)


class JsonFormatter(logging.Formatter):
    """Render a log record as a single JSON line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        for field in EXTRA_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value

        exc_info = _resolve_exc_info(record)
        if exc_info is not None:
            payload["exception"] = self.formatException(exc_info)

        return json.dumps(payload, ensure_ascii=False, default=str)


def _resolve_exc_info(
    record: logging.LogRecord,
) -> Optional[tuple]:
    """Normalize ``exc_info`` to a formatter-ready tuple.

    Python 3.14 keeps ``exc_info=True`` as a boolean on the record (instead of
    resolving it at creation time), so bools are resolved against the currently
    handled exception. Missing/empty info yields ``None`` instead of raising.
    """
    exc_info = record.exc_info
    if not exc_info:
        return None
    if isinstance(exc_info, BaseException):
        return (type(exc_info), exc_info, exc_info.__traceback__)
    if not isinstance(exc_info, tuple):
        exc_info = sys.exc_info()
    if not isinstance(exc_info, tuple) or exc_info[0] is None:
        return None
    return exc_info


class ScanLoggerAdapter(logging.LoggerAdapter):
    """Logger adapter that injects ``scan_id``/``task_id`` into every record."""

    def process(self, msg: str, kwargs: Dict[str, Any]):
        extra = {**self.extra, **kwargs.get("extra", {})}
        kwargs["extra"] = extra
        return msg, kwargs


def get_scan_logger(
    scan_id: int,
    task_id: Optional[str] = None,
    logger: Optional[logging.Logger] = None,
) -> ScanLoggerAdapter:
    """Return a logger bound to a scan (and optionally a Celery task).

    ``logger`` is injectable so tests (and alternative sinks) can target a
    dedicated logger instead of the shared ``app.scans`` one.
    """
    extra: Dict[str, Any] = {"scan_id": scan_id}
    if task_id:
        extra["task_id"] = task_id
    return ScanLoggerAdapter(logger or logging.getLogger("app.scans"), extra)


UVICORN_LOGGERS = ("uvicorn", "uvicorn.error", "uvicorn.access")


def configure_logging(
    level: str = "INFO",
    logger: Optional[logging.Logger] = None,
    stream=None,
    include_uvicorn: bool = False,
) -> logging.Handler:
    """Configure JSON logging once for the given logger (root by default).

    ``include_uvicorn`` also routes uvicorn's own loggers (which do not
    propagate by default) through the same JSON handler, so access/error logs
    keep the one-JSON-object-per-line format.
    """
    target = logger or logging.getLogger()
    level_value = getattr(logging, str(level).upper(), logging.INFO)
    target.setLevel(level_value)

    handler = next(
        (
            candidate
            for candidate in target.handlers
            if getattr(candidate, "_network_scanner_json", False)
        ),
        None,
    )
    if handler is None:
        handler = logging.StreamHandler(stream)
        handler.setFormatter(JsonFormatter())
        handler._network_scanner_json = True  # type: ignore[attr-defined]
        target.addHandler(handler)

    if include_uvicorn:
        for name in UVICORN_LOGGERS:
            uvicorn_logger = logging.getLogger(name)
            uvicorn_logger.setLevel(level_value)
            uvicorn_logger.handlers = [handler]
            # Uvicorn installs propagate=False; keep it to avoid duplicates.
            uvicorn_logger.propagate = False

    return handler
