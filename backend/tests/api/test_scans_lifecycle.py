import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure deterministic, isolated DB for tests before importing app modules that touch settings/engine.
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
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _create_scan(db, status=ScanStatus.RUNNING, task_id="task-123", **kwargs):
    scan = Scan(
        name=kwargs.get("name"),
        target=kwargs.get("target", "192.168.1.1"),
        scan_type=kwargs.get("scan_type", ScanType.TCP_CONNECT),
        status=status,
        task_id=task_id,
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)
    return scan


class TestScanLifecycle:
    @patch("app.api.scans.perform_scan_task")
    def test_create_scan_enqueues_task_and_sets_pending(self, mock_task, client, db_session):
        mock_task.delay.return_value = MagicMock(id="celery-1")

        resp = client.post(
            "/api/scans",
            json={
                "target": "192.168.1.10",
                "scan_type": "tcp_connect",
                "service_detection": True,
                "os_detection": False,
                "aggressive": False,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "pending"
        assert data["task_id"] == "celery-1"
        assert data["target"] == "192.168.1.10"
        mock_task.delay.assert_called_once_with(data["id"])

    @patch("app.celery_app.celery_app.control.revoke")
    def test_patch_status_cancelled_revokes_and_persists(self, mock_revoke, client, db_session):
        scan = _create_scan(db_session, status=ScanStatus.RUNNING, task_id="task-abc")

        resp = client.patch(f"/api/scans/{scan.id}", json={"status": "cancelled"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "cancelled"
        assert data["completed_at"] is not None
        assert data["error_message"] == "Scan cancelled by user"
        mock_revoke.assert_called_once_with("task-abc", terminate=True)

        db_session.refresh(scan)
        assert scan.status == ScanStatus.CANCELLED

    @patch("app.celery_app.celery_app.control.revoke")
    def test_delete_running_scan_revokes_and_removes(self, mock_revoke, client, db_session):
        scan = _create_scan(db_session, status=ScanStatus.RUNNING, task_id="task-del")

        resp = client.delete(f"/api/scans/{scan.id}")
        assert resp.status_code == 204
        mock_revoke.assert_called_once_with("task-del", terminate=True)
        assert db_session.query(Scan).filter(Scan.id == scan.id).first() is None

    @patch("app.celery_app.celery_app.control.revoke")
    def test_delete_pending_scan_revokes(self, mock_revoke, client, db_session):
        scan = _create_scan(db_session, status=ScanStatus.PENDING, task_id="task-pend")

        resp = client.delete(f"/api/scans/{scan.id}")
        assert resp.status_code == 204
        mock_revoke.assert_called_once_with("task-pend", terminate=True)

    def test_get_missing_scan_returns_404(self, client):
        resp = client.get("/api/scans/999999")
        assert resp.status_code == 404
