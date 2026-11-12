import os
from datetime import datetime

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


def _schedule_payload(**overrides):
    payload = {
        "name": "nightly",
        "description": "Nightly recon",
        "scan_config": {"target": "192.168.1.0/24", "scan_type": "tcp_connect"},
        "cron_expression": "0 3 * * *",
        "enabled": True,
    }
    payload.update(overrides)
    return payload


class TestScheduleContract:
    def test_create_enabled_schedule_sets_next_run(self, client):
        response = client.post("/api/schedules", json=_schedule_payload())

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "nightly"
        assert data["enabled"] is True
        assert data["total_runs"] == 0
        assert data["next_run_at"] is not None
        assert datetime.fromisoformat(data["next_run_at"]) > datetime.utcnow()

    def test_create_disabled_schedule_has_no_next_run(self, client):
        response = client.post(
            "/api/schedules", json=_schedule_payload(enabled=False)
        )

        assert response.status_code == 201
        assert response.json()["next_run_at"] is None

    def test_create_rejects_invalid_cron(self, client):
        response = client.post(
            "/api/schedules", json=_schedule_payload(cron_expression="bad cron")
        )

        assert response.status_code == 422

    def test_list_returns_schedules(self, client):
        client.post("/api/schedules", json=_schedule_payload())

        response = client.get("/api/schedules")

        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_patch_cron_recomputes_next_run(self, client):
        created = client.post("/api/schedules", json=_schedule_payload()).json()

        response = client.patch(
            f"/api/schedules/{created['id']}",
            json={"cron_expression": "*/15 * * * *"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["cron_expression"] == "*/15 * * * *"
        assert data["next_run_at"] is not None

    def test_patch_name_only_keeps_next_run(self, client):
        created = client.post("/api/schedules", json=_schedule_payload()).json()

        response = client.patch(
            f"/api/schedules/{created['id']}", json={"name": "renamed"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "renamed"
        assert data["next_run_at"] == created["next_run_at"]

    def test_patch_disable_clears_next_run_and_reenable_restores_it(self, client):
        created = client.post("/api/schedules", json=_schedule_payload()).json()

        disabled = client.patch(
            f"/api/schedules/{created['id']}", json={"enabled": False}
        )
        assert disabled.status_code == 200
        assert disabled.json()["next_run_at"] is None

        enabled = client.patch(
            f"/api/schedules/{created['id']}", json={"enabled": True}
        )
        assert enabled.status_code == 200
        assert enabled.json()["next_run_at"] is not None

    def test_patch_rejects_invalid_cron(self, client):
        created = client.post("/api/schedules", json=_schedule_payload()).json()

        response = client.patch(
            f"/api/schedules/{created['id']}",
            json={"cron_expression": "not valid"},
        )

        assert response.status_code == 422

    def test_get_missing_schedule_returns_404(self, client):
        assert client.get("/api/schedules/999").status_code == 404

    def test_delete_schedule(self, client):
        created = client.post("/api/schedules", json=_schedule_payload()).json()

        assert client.delete(f"/api/schedules/{created['id']}").status_code == 204
        assert client.get(f"/api/schedules/{created['id']}").status_code == 404
