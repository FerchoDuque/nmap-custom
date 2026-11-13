import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app, raise_server_exceptions=False) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)


def test_unhandled_errors_return_generic_message_without_internals(client):
    async def boom():
        raise RuntimeError("secret-token-should-not-leak")

    app.add_api_route("/api/__test_boom", boom, methods=["GET"])
    route = app.router.routes[-1]

    try:
        response = client.get("/api/__test_boom")
    finally:
        app.router.routes.remove(route)

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}
    assert "secret-token" not in response.text
    assert "Traceback" not in response.text


def test_known_http_errors_keep_their_detail(client):
    response = client.get("/api/scans/999999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Scan 999999 not found"}


def test_validation_errors_keep_field_details(client):
    response = client.post("/api/scans", json={"target": "bad_host"})

    assert response.status_code == 422
    assert "target" in response.text
