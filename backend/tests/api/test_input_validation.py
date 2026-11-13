import os
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402


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


@pytest.fixture()
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _scan_payload(**overrides):
    payload = {
        "target": "192.168.1.0/24",
        "scan_type": "tcp_connect",
        "port_range": "1-1000",
        "service_detection": True,
        "os_detection": False,
        "aggressive": False,
    }
    payload.update(overrides)
    return payload


def _schedule_payload(**overrides):
    payload = {
        "name": "nightly",
        "scan_config": {
            "target": "192.168.1.0/24",
            "scan_type": "tcp_connect",
            "port_range": "22,80",
        },
        "cron_expression": "0 3 * * *",
        "enabled": True,
    }
    payload.update(overrides)
    return payload


class TestScanInputValidation:
    @pytest.mark.parametrize(
        "target",
        ["", "999.1.1.1", "10.0.0.0/33", "bad_host", "-bad.example.com"],
    )
    def test_rejects_invalid_targets(self, client, target):
        response = client.post("/api/scans", json=_scan_payload(target=target))
        assert response.status_code == 422

    @pytest.mark.parametrize("port_range", ["70000", "100-50", "abc", "22,,80"])
    def test_rejects_invalid_port_ranges(self, client, port_range):
        response = client.post("/api/scans", json=_scan_payload(port_range=port_range))
        assert response.status_code == 422

    @pytest.mark.parametrize(
        "target",
        [
            "192.168.1.10",
            "localhost",
            "scan-01.example.com",
            "2001:db8::1",
            "192.168.1.10-192.168.1.20",
        ],
    )
    def test_accepts_supported_targets(self, client, target):
        with patch("app.api.scans.perform_scan_task") as task:
            task.delay.return_value = SimpleNamespace(id="task-validate")
            response = client.post("/api/scans", json=_scan_payload(target=target))

        assert response.status_code == 201
        assert response.json()["target"] == target

    def test_normalizes_target_and_port_range(self, client):
        with patch("app.api.scans.perform_scan_task") as task:
            task.delay.return_value = SimpleNamespace(id="task-normalize")
            response = client.post(
                "/api/scans",
                json=_scan_payload(target=" 10.0.0.0/24 ", port_range="22, 100-200,443"),
            )

        assert response.status_code == 201
        data = response.json()
        assert data["target"] == "10.0.0.0/24"
        assert data["port_range"] == "22,100-200,443"

    @pytest.mark.parametrize(
        "target",
        ["10.0.0.0/8", "2001:db8::/32", "10.0.0.1-10.1.0.1"],
    )
    def test_rejects_targets_above_host_limit(self, client, target):
        response = client.post("/api/scans", json=_scan_payload(target=target))
        assert response.status_code == 422


class TestScheduleInputValidation:
    @pytest.mark.parametrize(
        "scan_config",
        [
            {},
            {"target": ""},
            {"target": "999.1.1.1"},
            {"target": "10.0.0.1", "scan_type": "invalid"},
            {"target": "10.0.0.1", "port_range": "70000"},
        ],
    )
    def test_rejects_invalid_scan_config(self, client, scan_config):
        response = client.post(
            "/api/schedules", json=_schedule_payload(scan_config=scan_config)
        )
        assert response.status_code == 422

    def test_patch_rejects_invalid_scan_config(self, client):
        created = client.post("/api/schedules", json=_schedule_payload()).json()

        response = client.patch(
            f"/api/schedules/{created['id']}",
            json={"scan_config": {"target": "bad_host"}},
        )

        assert response.status_code == 422

    def test_normalizes_valid_scan_config(self, client):
        response = client.post(
            "/api/schedules",
            json=_schedule_payload(
                scan_config={
                    "target": " 10.0.0.0/24 ",
                    "scan_type": "udp",
                    "port_range": "53, 123",
                }
            ),
        )

        assert response.status_code == 201
        assert response.json()["scan_config"] == {
            "target": "10.0.0.0/24",
            "scan_type": "udp",
            "port_range": "53,123",
        }
