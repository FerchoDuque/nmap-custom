"""Schema lifecycle: apply Alembic migrations and adopt legacy databases.

The 0.1.0 releases created the schema with ``Base.metadata.create_all()`` and
have no ``alembic_version`` table. Running ``upgrade`` on such a database would
fail because the tables already exist, so those databases are stamped at the
baseline revision first.

Usage::

    python -m app.core.db_migrations            # upgrade to head
    python -m app.core.db_migrations --revision 0001
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

BACKEND_DIR = Path(__file__).resolve().parents[2]
ALEMBIC_INI = BACKEND_DIR / "alembic.ini"
MIGRATIONS_DIR = BACKEND_DIR / "migrations"

VERSION_TABLE = "alembic_version"
BASELINE_REVISION = "0001"
MANAGED_TABLES = frozenset({"scans", "scan_results", "ports", "schedules"})

STATE_EMPTY = "empty"
STATE_LEGACY = "legacy"
STATE_MANAGED = "managed"


def alembic_config(database_url: str) -> Config:
    """Build an Alembic config bound to ``database_url``."""
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("script_location", str(MIGRATIONS_DIR))
    # configparser treats `%` as interpolation; passwords are URL-encoded.
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    return config


def schema_state(database_url: str) -> str:
    """Classify the database as ``empty``, ``legacy`` or ``managed``."""
    engine = create_engine(database_url)
    try:
        tables = set(inspect(engine).get_table_names())
    finally:
        engine.dispose()

    if VERSION_TABLE in tables:
        return STATE_MANAGED
    if tables & MANAGED_TABLES:
        return STATE_LEGACY
    return STATE_EMPTY


def ensure_schema(database_url: str, revision: str = "head") -> str:
    """Bring the database to ``revision``, stamping pre-Alembic schemas.

    Returns the state the database was in before migrating.
    """
    state = schema_state(database_url)
    config = alembic_config(database_url)

    if state == STATE_LEGACY:
        command.stamp(config, BASELINE_REVISION)

    command.upgrade(config, revision)
    return state


def main(argv: list[str] | None = None) -> int:
    from app.config import settings

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision", default="head", help="target revision")
    parser.add_argument("--url", default=settings.database_url, help="database URL")
    args = parser.parse_args(argv)

    state = ensure_schema(args.url, args.revision)
    print(f"schema {state} -> {args.revision}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
