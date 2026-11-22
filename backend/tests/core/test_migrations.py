"""Migrations must reproduce the ORM schema and be reversible.

These tests run Alembic in-process against temporary SQLite files: no network,
no PostgreSQL and no privileges required.
"""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect

from app import models  # noqa: F401  (registers tables on Base.metadata)
from app.core import db_migrations
from app.database import Base

MANAGED = set(Base.metadata.tables)


def _url(tmp_path, name: str = "migrations.db") -> str:
    return f"sqlite:///{(tmp_path / name).as_posix()}"


def _tables(url: str) -> set[str]:
    engine = create_engine(url)
    try:
        return set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def test_there_is_exactly_one_head_revision(tmp_path):
    config = db_migrations.alembic_config(_url(tmp_path))

    assert ScriptDirectory.from_config(config).get_heads() == ["0001"]


def test_upgrade_creates_the_orm_schema(tmp_path):
    url = _url(tmp_path)

    db_migrations.ensure_schema(url)

    assert _tables(url) - {db_migrations.VERSION_TABLE} == MANAGED


def test_migrations_are_reversible(tmp_path):
    url = _url(tmp_path)
    config = db_migrations.alembic_config(url)

    command.upgrade(config, "head")
    command.downgrade(config, "base")

    assert _tables(url) == {db_migrations.VERSION_TABLE}


def test_legacy_create_all_database_is_stamped_not_recreated(tmp_path):
    url = _url(tmp_path, "legacy.db")
    engine = create_engine(url)
    Base.metadata.create_all(bind=engine)
    engine.dispose()

    state = db_migrations.ensure_schema(url)

    assert state == db_migrations.STATE_LEGACY
    assert db_migrations.VERSION_TABLE in _tables(url)
    # Adopting must not duplicate or drop the existing tables.
    assert _tables(url) - {db_migrations.VERSION_TABLE} == MANAGED


def test_ensure_schema_is_idempotent(tmp_path):
    url = _url(tmp_path)

    first = db_migrations.ensure_schema(url)
    second = db_migrations.ensure_schema(url)

    assert (first, second) == (db_migrations.STATE_EMPTY, db_migrations.STATE_MANAGED)
    assert _tables(url) - {db_migrations.VERSION_TABLE} == MANAGED


def test_schema_state_detects_empty_legacy_and_managed(tmp_path):
    empty_url = _url(tmp_path, "empty.db")
    assert db_migrations.schema_state(empty_url) == db_migrations.STATE_EMPTY

    legacy_url = _url(tmp_path, "legacy2.db")
    engine = create_engine(legacy_url)
    Base.metadata.create_all(bind=engine)
    engine.dispose()
    assert db_migrations.schema_state(legacy_url) == db_migrations.STATE_LEGACY

    db_migrations.ensure_schema(legacy_url)
    assert db_migrations.schema_state(legacy_url) == db_migrations.STATE_MANAGED


def test_alembic_url_round_trips_percent_encoded_passwords(tmp_path):
    # ConfigParser interpolates `%`, so an unescaped URL would raise here.
    config = db_migrations.alembic_config("postgresql://u:p%40ss@db/app")

    assert config.get_main_option("sqlalchemy.url") == "postgresql://u:p%40ss@db/app"


def test_container_entrypoint_applies_migrations():
    repo_root = Path(__file__).resolve().parents[3]
    entrypoint = (repo_root / "backend" / "docker-entrypoint.sh").read_text(
        encoding="utf-8"
    )

    assert "python -m app.core.db_migrations" in entrypoint
    assert "init_db" not in entrypoint


def test_production_compose_disables_create_all():
    repo_root = Path(__file__).resolve().parents[3]
    compose = (repo_root / "docker-compose.yml").read_text(encoding="utf-8")

    assert "AUTO_CREATE_SCHEMA=false" in compose
