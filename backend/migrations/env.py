"""Alembic environment for nmap-custom.

The database URL is resolved in this order:

1. ``sqlalchemy.url`` set programmatically (``app.core.db_migrations``).
2. ``DATABASE_URL`` / ``app.config.settings`` used by the API.

Keeping a single source (the app settings) means migrations always run
against the same database the API talks to.
"""

from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings  # noqa: E402
from app.database import Base  # noqa: E402
from app import models  # noqa: E402,F401  (registers every table on Base.metadata)

config = context.config

if config.config_file_name is not None:
    # Keep pytest/host logging handlers alive when migrations run in-process.
    fileConfig(config.config_file_name, disable_existing_loggers=False)

database_url = config.get_main_option("sqlalchemy.url") or settings.database_url
# configparser interprets `%` as interpolation; passwords are URL-encoded.
config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))

target_metadata = Base.metadata


def _configure(**kwargs) -> None:
    context.configure(
        target_metadata=target_metadata,
        compare_type=True,
        include_schemas=False,
        **kwargs,
    )


def run_migrations_offline() -> None:
    """Emit SQL to stdout instead of touching a database."""
    _configure(
        url=database_url,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        # SQLite cannot ALTER most constraints; batch mode rewrites the table.
        _configure(
            connection=connection,
            render_as_batch=connection.dialect.name == "sqlite",
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
