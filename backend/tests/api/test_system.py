import os
from datetime import datetime
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models.scan import Scan, ScanStatus, ScanType  # noqa: E402


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
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _scan(status: ScanStatus, hosts_up: int = 0, ports: int = 0, scan_id: int = 1):
    return Scan(
        id=scan_id,
        name=f"scan-{scan_id}",
        target="192.168.1.0/24",
        scan_type=ScanType.TCP_CONNECT,
        status=status,
        port_range="1-1000",
        service_detection=True,
        os_detection=False,
        aggressive=False,
        progress=100 if status == ScanStatus.COMPLETED else 50,
        hosts_total=10,
        hosts_scanned=10,
        created_at=datetime.utcnow(),
        total_hosts_up=hosts_up,
        total_ports_found=ports,
    )


class TestHealth:
    def test_reports_healthy_and_connected(self, client):
        response = client.get("/api/health")

        assert response.status_code == 200
        assert response.json() == {"status": "healthy", "database": "connected"}

    def test_reports_degraded_when_database_fails(self):
        db = MagicMock()
        db.execute.side_effect = RuntimeError("db down")

        def override_get_db():
            yield db

        app.dependency_overrides[get_db] = override_get_db
        try:
            with TestClient(app) as test_client:
                response = test_client.get("/api/health")
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 503
        assert response.json() == {
            "status": "degraded",
            "database": "unavailable",
        }


class TestMetrics:
    def test_returns_status_counts_and_totals(self, client, db_session):
        db_session.add_all(
            [
                _scan(ScanStatus.COMPLETED, hosts_up=3, ports=10, scan_id=1),
                _scan(ScanStatus.COMPLETED, hosts_up=2, ports=5, scan_id=2),
                _scan(ScanStatus.RUNNING, hosts_up=1, ports=2, scan_id=3),
                _scan(ScanStatus.FAILED, scan_id=4),
                _scan(ScanStatus.PENDING, scan_id=5),
            ]
        )
        db_session.commit()

        response = client.get("/api/metrics")

        assert response.status_code == 200
        payload = response.json()
        assert payload["scans"]["total"] == 5
        assert payload["scans"]["by_status"] == {
            "completed": 2,
            "failed": 1,
            "pending": 1,
            "running": 1,
        }
        assert payload["scans"]["active"] == 2
        assert payload["hosts_up_total"] == 6
        assert payload["ports_found_total"] == 17

    def test_returns_zeroes_for_empty_database(self, client):
        response = client.get("/api/metrics")

        assert response.status_code == 200
        payload = response.json()
        assert payload["scans"]["total"] == 0
        assert payload["scans"]["by_status"] == {}
        assert payload["scans"]["active"] == 0
        assert payload["hosts_up_total"] == 0
        assert payload["ports_found_total"] == 0
