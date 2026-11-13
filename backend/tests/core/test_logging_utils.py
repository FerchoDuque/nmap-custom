import io
import json
import logging
import sys

import pytest

from app.core.logging_utils import (
    JsonFormatter,
    ScanLoggerAdapter,
    configure_logging,
    get_scan_logger,
)


class ListHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(record)


def test_json_formatter_includes_correlation_fields():
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="app.scans",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="Scan completed",
        args=(),
        exc_info=None,
    )
    record.scan_id = 42
    record.task_id = "task-42"
    record.event = "scan.completed"
    record.ports_found = 12

    payload = json.loads(formatter.format(record))

    assert payload["level"] == "INFO"
    assert payload["logger"] == "app.scans"
    assert payload["message"] == "Scan completed"
    assert payload["scan_id"] == 42
    assert payload["task_id"] == "task-42"
    assert payload["event"] == "scan.completed"
    assert payload["ports_found"] == 12
    assert "timestamp" in payload


def test_json_formatter_includes_exception_text():
    formatter = JsonFormatter()
    try:
        raise RuntimeError("boom")
    except RuntimeError:
        exc_info = sys.exc_info()
        record = logging.LogRecord(
            name="app.scans",
            level=logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg="Scan failed",
            args=(),
            exc_info=exc_info,
        )

    payload = json.loads(formatter.format(record))
    assert "RuntimeError: boom" in payload["exception"]


def test_json_formatter_tolerates_bool_exc_info_without_active_exception():
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="app.scans",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg="Failed outside handler",
        args=(),
        exc_info=True,
    )

    payload = json.loads(formatter.format(record))

    assert payload["message"] == "Failed outside handler"
    assert "exception" not in payload


def test_scan_logger_adapter_injects_scan_and_task_ids():
    logger = logging.getLogger("test.scan.adapter")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    handler = ListHandler()
    logger.addHandler(handler)

    try:
        scan_log = get_scan_logger(7, task_id="task-7", logger=logger)
        assert isinstance(scan_log, ScanLoggerAdapter)
        scan_log.info("Scan started", extra={"event": "scan.started"})
    finally:
        logger.removeHandler(handler)

    record = handler.records[0]
    assert record.scan_id == 7
    assert record.task_id == "task-7"
    assert record.event == "scan.started"


def test_call_extra_overrides_adapter_defaults():
    logger = logging.getLogger("test.scan.adapter.override")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    handler = ListHandler()
    logger.addHandler(handler)

    try:
        get_scan_logger(7, logger=logger).info("Progress", extra={"scan_id": 99})
    finally:
        logger.removeHandler(handler)

    assert handler.records[0].scan_id == 99


def test_configure_logging_is_idempotent_for_a_logger():
    logger = logging.getLogger("test.configure.logging")
    original_handlers = list(logger.handlers)
    original_level = logger.level
    stream = io.StringIO()

    try:
        configure_logging(level="INFO", logger=logger, stream=stream)
        configure_logging(level="INFO", logger=logger, stream=stream)
        assert len(logger.handlers) == 1
        assert isinstance(logger.handlers[0].formatter, JsonFormatter)

        logger.info("hello", extra={"scan_id": 3})
        payload = json.loads(stream.getvalue().strip())
        assert payload["message"] == "hello"
        assert payload["scan_id"] == 3
    finally:
        logger.handlers = original_handlers
        logger.setLevel(original_level)


@pytest.mark.parametrize("level", ["DEBUG", "INFO", "WARNING"])
def test_configure_logging_sets_level(level):
    logger = logging.getLogger(f"test.configure.level.{level}")
    original_handlers = list(logger.handlers)
    original_level = logger.level

    try:
        configure_logging(level=level, logger=logger, stream=io.StringIO())
        assert logger.level == getattr(logging, level)
    finally:
        logger.handlers = original_handlers
        logger.setLevel(original_level)
