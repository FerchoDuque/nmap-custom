"""Resilience tests for PLAN-032: failure isolation, timeout and idempotency."""

import asyncio
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.scanner import NetworkScanner
from app.database import Base
from app.models.scan import Port, Scan, ScanResult, ScanStatus, ScanType, PortState
from app.tasks import ScanTimeoutError, execute_scan

TERMINAL = [ScanStatus.COMPLETED, ScanStatus.FAILED, ScanStatus.CANCELLED]


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def make_scan(db, **overrides):
    scan = Scan(
        target="192.168.1.0/24",
        scan_type=ScanType.TCP_CONNECT,
        port_range="1-1000",
        service_detection=True,
        os_detection=False,
        aggressive=False,
        status=overrides.pop("status", ScanStatus.PENDING),
        **overrides,
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)
    return scan


def scan_results(ports_found=1):
    return {
        "hosts_total": 1,
        "hosts_up": 1,
        "hosts_failed": 0,
        "total_ports_found": ports_found,
        "results": [
            {
                "ip_address": "192.168.1.10",
                "hostname": "router.local",
                "is_up": True,
                "ports": [
                    {
                        "port_number": 443,
                        "protocol": "tcp",
                        "state": PortState.OPEN.value,
                        "service_name": "https",
                        "service_product": "nginx",
                        "service_version": "1.25",
                        "banner": None,
                    }
                ],
                "os_name": None,
                "os_accuracy": None,
                "os_details": None,
            }
        ],
    }


class FakeScanner:
    def __init__(self, result=None, error=None, delay=None):
        self.result = result if result is not None else scan_results()
        self.error = error
        self.delay = delay
        self.calls = []

    async def scan(self, **kwargs):
        self.calls.append(kwargs)
        if self.delay is not None:
            await asyncio.sleep(self.delay)
        if self.error is not None:
            raise self.error
        callback = kwargs.get("progress_callback")
        if callback is not None:
            await callback(
                {
                    "progress": 50,
                    "current_host": "192.168.1.10",
                    "hosts_scanned": 1,
                }
            )
        return self.result


class TestExecuteScanIdempotency:
    @pytest.mark.parametrize("status", TERMINAL)
    def test_terminal_scans_are_not_rerun(self, db, status):
        scan = make_scan(db, status=status)
        scanner = Mock()
        scanner.scan = AsyncMock()

        result = execute_scan(db, scan.id, scanner=scanner, timeout=1)

        assert result == {"scan_id": scan.id, "status": "skipped"}
        scanner.scan.assert_not_called()
        db.refresh(scan)
        assert scan.status == status

    def test_missing_scan_is_reported(self, db):
        result = execute_scan(db, 999, scanner=Mock(), timeout=1)

        assert result == {"scan_id": 999, "status": "not_found"}


class TestExecuteScanLifecycle:
    def test_persists_results_and_marks_completed(self, db):
        scan = make_scan(db)
        scanner = FakeScanner()
        update_state = Mock()

        result = execute_scan(
            db,
            scan.id,
            task_id="task-1",
            scanner=scanner,
            update_state=update_state,
            timeout=5,
        )

        assert result == {
            "scan_id": scan.id,
            "status": "completed",
            "hosts_up": 1,
            "ports_found": 1,
        }
        db.refresh(scan)
        assert scan.status == ScanStatus.COMPLETED
        assert scan.progress == 100
        assert scan.task_id == "task-1"
        assert scan.total_hosts_up == 1
        assert scan.total_ports_found == 1
        assert db.query(ScanResult).count() == 1
        assert db.query(Port).count() == 1
        update_state.assert_called()
        assert update_state.call_args.kwargs["state"] == "PROGRESS"
        assert scanner.calls[0]["target"] == "192.168.1.0/24"

    def test_timeout_marks_scan_failed_with_non_sensitive_message(self, db):
        scan = make_scan(db)
        scanner = FakeScanner(delay=0.5)

        with pytest.raises(ScanTimeoutError) as excinfo:
            execute_scan(db, scan.id, scanner=scanner, timeout=0.01)

        db.refresh(scan)
        assert scan.status == ScanStatus.FAILED
        assert scan.completed_at is not None
        assert "timeout" in scan.error_message.lower()
        assert "asyncio" not in scan.error_message.lower()
        assert "Traceback" not in str(excinfo.value)

    def test_failure_is_recorded_and_message_is_truncated(self, db):
        scan = make_scan(db)
        scanner = FakeScanner(error=RuntimeError("x" * 1000))

        with pytest.raises(RuntimeError):
            execute_scan(db, scan.id, scanner=scanner, timeout=5)

        db.refresh(scan)
        assert scan.status == ScanStatus.FAILED
        assert len(scan.error_message) <= 500
        assert scan.error_message.startswith("x")


class TestScannerHostIsolation:
    @pytest.fixture()
    def scanner(self):
        s = NetworkScanner()
        s.resolve_hostnames = False
        s.network_mapper = Mock()
        s.network_mapper.parse_target.return_value = [
            "192.168.1.10",
            "192.168.1.11",
        ]
        s.network_mapper.discover_hosts = AsyncMock(
            return_value=["192.168.1.10", "192.168.1.11"]
        )
        s.port_scanner = AsyncMock()
        s.service_detector = AsyncMock()
        s.service_detector.detect_service.return_value = {
            "service_name": None,
            "service_product": None,
            "service_version": None,
            "banner": None,
        }
        s.os_fingerprinter = AsyncMock()
        return s

    async def test_host_failure_does_not_abort_the_scan(self, scanner):
        scanner.port_scanner.tcp_connect_scan.side_effect = [
            RuntimeError("socket blew up"),
            {80: PortState.OPEN},
        ]
        progress = AsyncMock()

        result = await NetworkScanner.scan(
            scanner,
            target="192.168.1.0/24",
            scan_type=ScanType.TCP_CONNECT,
            service_detection=False,
            progress_callback=progress,
        )

        assert result["hosts_up"] == 2
        assert result["hosts_failed"] == 1
        assert result["total_ports_found"] == 1
        assert [host["ip_address"] for host in result["results"]] == [
            "192.168.1.11"
        ]

        messages = [
            call.args[0].get("message", "")
            for call in progress.await_args_list
            if call.args
        ]
        assert any("192.168.1.10" in message for message in messages)
        assert any("192.168.1.11" in message for message in messages)
        assert messages[-1] == "Scan completed"

    async def test_successful_scan_reports_zero_failed_hosts(self, scanner):
        scanner.port_scanner.tcp_connect_scan.return_value = {80: PortState.OPEN}

        result = await NetworkScanner.scan(
            scanner,
            target="192.168.1.0/24",
            scan_type=ScanType.TCP_CONNECT,
            service_detection=False,
        )

        assert result["hosts_failed"] == 0
        assert result["hosts_up"] == 2
