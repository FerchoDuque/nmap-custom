"""Regression tests for deployment wiring caught by the release dry-run."""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
COMPOSE_FILES = ["docker-compose.yml", "docker-compose.dev.yml"]


@pytest.mark.parametrize("filename", COMPOSE_FILES)
def test_celery_entrypoints_point_to_the_app_attribute(filename):
    text = (REPO_ROOT / filename).read_text(encoding="utf-8")

    assert "app.celery_app:celery_app" in text
    # `-A app.celery_app` makes Celery look for the `celery` attribute.
    assert '"app.celery_app"' not in text


@pytest.mark.parametrize("filename", COMPOSE_FILES)
def test_compose_does_not_declare_the_obsolete_version_key(filename):
    lines = (REPO_ROOT / filename).read_text(encoding="utf-8").splitlines()

    assert not any(line.strip().startswith("version:") for line in lines)


@pytest.mark.parametrize("filename", COMPOSE_FILES)
def test_compose_pins_the_psycopg2_driver(filename):
    text = (REPO_ROOT / filename).read_text(encoding="utf-8")

    # SQLAlchemy 2.1 resolves bare `postgresql://` to psycopg (v3), which is
    # not installed; the image ships psycopg2-binary.
    assert "postgresql+psycopg2://" in text
    assert "postgresql://" not in text


def test_entrypoint_parses_the_sqlalchemy_url_before_psycopg2():
    text = (REPO_ROOT / "backend" / "docker-entrypoint.sh").read_text(
        encoding="utf-8"
    )

    # psycopg2 cannot parse the `+psycopg2` dialect suffix.
    assert "make_url(" in text
    assert "psycopg2.connect(os.environ['DATABASE_URL'])" not in text
