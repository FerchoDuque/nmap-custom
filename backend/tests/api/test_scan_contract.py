import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.websockets import WebSocketDisconnect

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models.scan import Scan, ScanResult, Port, ScanStatus, ScanType, PortState  # noqa: E402
from app.api.websocket import (  # noqa: E402
    TERMINAL_STATUSES,
    build_error_message,
    build_status_message,
    build_update_message,
    scan_snapshot,
)
from app.schemas.scan import (  # noqa: E402
    ExportRequest,
    ScanCreate,
    ScanResponse,
    ScanSummaryResponse,
)


@pytest.fixture()
def db_engine_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield engine, TestingSessionLocal, db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_engine_session):
    _, _, db = db_engine_session

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _make_scan(**overrides):
    """Build an unsaved Scan with explicit contract-relevant values."""
    values = {
        "id": 7,
        "target": "10.0.0.9",
        "scan_type": ScanType.TCP_CONNECT,
        "status": ScanStatus.RUNNING,
        "progress": 42,
        "current_host": "10.0.0.9",
        "hosts_total": 4,
        "hosts_scanned": 2,
        "total_ports_found": 5,
        "error_message": None,
    }
    values.update(overrides)
    return Scan(**values)


def _seed_scan_with_results(db):
    scan = Scan(
        name="seed",
        target="10.0.0.1",
        scan_type=ScanType.TCP_CONNECT,
        status=ScanStatus.COMPLETED,
        progress=100,
        hosts_total=1,
        hosts_scanned=1,
        total_hosts_up=1,
        total_ports_found=1,
    )
    db.add(scan)
    db.flush()
    result = ScanResult(scan_id=scan.id, ip_address="10.0.0.1", is_up=True)
    db.add(result)
    db.flush()
    port = Port(result_id=result.id, port_number=80, protocol="tcp", state=PortState.OPEN)
    db.add(port)
    db.commit()
    db.refresh(scan)
    return scan


class TestScanContract:
    def test_list_scans_returns_summary_without_results(self, client, db_engine_session):
        _, _, db = db_engine_session
        _seed_scan_with_results(db)

        resp = client.get("/api/scans")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list) and len(data) == 1
        item = data[0]
        # Summary contract: core fields present, heavy results omitted
        assert item["id"] >= 1
        assert item["target"] == "10.0.0.1"
        assert item["status"] == "completed"
        assert "results" not in item

    def test_get_scan_returns_detail_with_results(self, client, db_engine_session):
        _, _, db = db_engine_session
        scan = _seed_scan_with_results(db)

        resp = client.get(f"/api/scans/{scan.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == scan.id
        assert "results" in data
        assert len(data["results"]) == 1
        assert data["results"][0]["ip_address"] == "10.0.0.1"
        assert data["results"][0]["ports"][0]["port_number"] == 80
        assert data["results"][0]["ports"][0]["protocol"] == "tcp"

    def test_list_scans_empty_returns_empty_list(self, client):
        resp = client.get("/api/scans")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_scans_filters_by_status(self, client, db_engine_session):
        _, _, db = db_engine_session
        db.add(
            Scan(
                target="10.0.0.3",
                scan_type=ScanType.TCP_CONNECT,
                status=ScanStatus.COMPLETED,
            )
        )
        db.add(
            Scan(
                target="10.0.0.4",
                scan_type=ScanType.TCP_CONNECT,
                status=ScanStatus.RUNNING,
            )
        )
        db.commit()

        resp = client.get("/api/scans", params={"status_filter": "running"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["target"] == "10.0.0.4"
        assert data[0]["status"] == "running"

    def test_list_scans_respects_pagination(self, client, db_engine_session):
        _, _, db = db_engine_session
        for i in range(3):
            db.add(
                Scan(
                    target=f"10.0.0.{10 + i}",
                    scan_type=ScanType.TCP_CONNECT,
                    status=ScanStatus.COMPLETED,
                )
            )
        db.commit()

        resp = client.get("/api/scans", params={"skip": 1, "limit": 1})
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_create_scan_rejects_blank_target(self, client):
        resp = client.post(
            "/api/scans",
            json={"target": "   ", "scan_type": "tcp_connect"},
        )
        assert resp.status_code == 422

    def test_patch_scan_updates_name_and_status(self, client, db_engine_session):
        _, _, db = db_engine_session
        scan = _seed_scan_with_results(db)

        resp = client.patch(
            f"/api/scans/{scan.id}",
            json={"name": "renamed", "status": "failed"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "renamed"
        assert data["status"] == "failed"

    def test_patch_scan_rejects_unknown_status(self, client, db_engine_session):
        _, _, db = db_engine_session
        scan = _seed_scan_with_results(db)

        resp = client.patch(f"/api/scans/{scan.id}", json={"status": "exploded"})
        assert resp.status_code == 422

    def test_export_json_contract(self, client, db_engine_session):
        _, _, db = db_engine_session
        scan = _seed_scan_with_results(db)

        resp = client.post(f"/api/scans/{scan.id}/export", json={"format": "JSON"})
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("application/json")
        assert f"scan_{scan.id}.json" in resp.headers["content-disposition"]

        data = resp.json()
        assert set(data.keys()) == {"scan", "results"}
        assert data["scan"]["id"] == scan.id
        assert data["scan"]["status"] == "completed"
        assert data["results"][0]["ip_address"] == "10.0.0.1"
        assert data["results"][0]["ports"][0] == {
            "port": 80,
            "protocol": "tcp",
            "state": "open",
            "service": None,
            "version": None,
        }

    def test_export_csv_contract(self, client, db_engine_session):
        _, _, db = db_engine_session
        scan = _seed_scan_with_results(db)

        resp = client.post(f"/api/scans/{scan.id}/export", json={"format": "csv"})
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/csv")
        lines = resp.text.strip().splitlines()
        assert lines[0] == "IP Address,Hostname,Port,Protocol,State,Service,Version"
        assert lines[1].startswith("10.0.0.1")
        assert "80" in lines[1]

    def test_export_xml_contract(self, client, db_engine_session):
        _, _, db = db_engine_session
        scan = _seed_scan_with_results(db)

        resp = client.post(f"/api/scans/{scan.id}/export", json={"format": "xml"})
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("application/xml")
        assert "<nmaprun" in resp.text
        assert '<port protocol="tcp" portid="80">' in resp.text

    def test_export_rejects_unsupported_format(self, client, db_engine_session):
        _, _, db = db_engine_session
        scan = _seed_scan_with_results(db)

        resp = client.post(f"/api/scans/{scan.id}/export", json={"format": "pdf"})
        assert resp.status_code == 422

    def test_export_missing_scan_returns_404(self, client):
        resp = client.post("/api/scans/424242/export", json={"format": "json"})
        assert resp.status_code == 404


class TestSchemaContract:
    def test_summary_schema_has_no_results(self):
        assert "results" not in ScanSummaryResponse.model_fields

    def test_detail_schema_extends_summary_with_results(self):
        summary_fields = set(ScanSummaryResponse.model_fields)
        detail_fields = set(ScanResponse.model_fields)
        assert summary_fields < detail_fields
        assert detail_fields - summary_fields == {"results"}

    def test_scan_create_defaults(self):
        payload = ScanCreate(target=" 10.0.0.1 ")
        assert payload.target == "10.0.0.1"
        assert payload.scan_type == ScanType.TCP_CONNECT
        assert payload.service_detection is True
        assert payload.os_detection is False
        assert payload.aggressive is False

    def test_scan_create_rejects_blank_target(self):
        with pytest.raises(ValidationError):
            ScanCreate(target="  ")

    def test_export_request_normalizes_format(self):
        assert ExportRequest(format="XML").format == "xml"

    def test_export_request_rejects_unknown_format(self):
        with pytest.raises(ValidationError):
            ExportRequest(format="pdf")


class TestWebSocketMessageBuilders:
    def test_terminal_statuses_contract(self):
        assert set(TERMINAL_STATUSES) == {"completed", "failed", "cancelled"}

    def test_status_message_contract(self):
        message = build_status_message(_make_scan())

        assert set(message) == {
            "type",
            "scan_id",
            "status",
            "progress",
            "current_host",
            "hosts_scanned",
            "hosts_total",
            "ports_found",
            "error_message",
        }
        assert message["type"] == "status"
        assert message["scan_id"] == 7
        assert message["status"] == "running"
        assert message["progress"] == 42
        assert message["hosts_total"] == 4
        assert message["hosts_scanned"] == 2
        assert message["ports_found"] == 5

    def test_update_message_reflects_snapshot(self):
        scan = _make_scan(
            status=ScanStatus.COMPLETED,
            progress=100,
            hosts_scanned=4,
            total_ports_found=9,
            error_message=None,
        )
        message = build_update_message(scan)

        assert message["type"] == "update"
        assert message == {
            "type": "update",
            "scan_id": 7,
            **scan_snapshot(scan),
            "hosts_total": 4,
        }
        assert message["status"] == "completed"
        assert message["progress"] == 100
        assert message["ports_found"] == 9

    def test_error_message_contract(self):
        message = build_error_message(999, "Scan 999 not found")

        assert message == {
            "type": "error",
            "scan_id": 999,
            "message": "Scan 999 not found",
        }


class TestWebSocketContract:
    def test_ws_not_found_emits_error(self, client, db_engine_session):
        _, SessionLocal, _ = db_engine_session
        with patch("app.database.SessionLocal", SessionLocal):
            with client.websocket_connect("/ws/scan/999999") as ws:
                msg = ws.receive_json()
                assert msg["type"] == "error"
                assert msg["scan_id"] == 999999
                assert "not found" in msg["message"].lower()

    def test_ws_completed_scan_emits_status_with_contract_fields(self, client, db_engine_session):
        _, SessionLocal, db = db_engine_session
        scan = Scan(
            target="10.0.0.2",
            scan_type=ScanType.TCP_CONNECT,
            status=ScanStatus.COMPLETED,
            progress=100,
            hosts_total=1,
            hosts_scanned=1,
            total_hosts_up=1,
            total_ports_found=2,
        )
        db.add(scan)
        db.commit()
        db.refresh(scan)

        with patch("app.database.SessionLocal", SessionLocal):
            with client.websocket_connect(f"/ws/scan/{scan.id}") as ws:
                msg = ws.receive_json()
                assert msg["type"] == "status"
                assert msg["scan_id"] == scan.id
                assert msg["status"] == "completed"
                assert msg["progress"] == 100
                assert msg["hosts_total"] == 1
                assert msg["hosts_scanned"] == 1
                assert msg["ports_found"] == 2
                assert "error_message" in msg
                # Terminal scans emit one status message and close the socket.
                with pytest.raises(WebSocketDisconnect):
                    ws.receive_json()
