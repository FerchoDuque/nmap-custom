"""Database backup and restore (PLAN-062).

SQLite files are copied with the ``sqlite3`` online backup API, which is safe
while the application is running. PostgreSQL uses ``pg_dump``/``pg_restore``
with credentials passed through ``PGPASSWORD`` so the password never appears in
the process arguments.

CLI::

    python -m app.core.backup backup --output backups/db.dump
    python -m app.core.backup restore --input backups/db.dump
"""

from __future__ import annotations

import argparse
import os
import shutil
import sqlite3
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Optional

from sqlalchemy.engine import URL, make_url

Runner = Callable[..., subprocess.CompletedProcess]


@dataclass(frozen=True)
class BackupResult:
    path: Path
    backend: str
    size_bytes: int


def _sqlite_file(url: URL) -> Path:
    database = url.database
    if not database or database == ":memory:":
        raise ValueError("cannot back up an in-memory SQLite database")
    path = Path(database)
    if not path.is_file():
        raise FileNotFoundError(f"SQLite database not found: {path}")
    return path


def _sqlite_copy(source: Path, destination: Path) -> None:
    source_conn = sqlite3.connect(f"file:{source.as_posix()}?mode=ro", uri=True)
    try:
        with sqlite3.connect(destination) as destination_conn:
            source_conn.backup(destination_conn)
    finally:
        source_conn.close()


def _pg_env(url: URL, base: Optional[Mapping[str, str]] = None) -> dict:
    env = dict(os.environ if base is None else base)
    if url.password:
        env["PGPASSWORD"] = url.password
    return env


def _pg_connection_args(url: URL) -> list[str]:
    return [
        "-h",
        url.host or "localhost",
        "-p",
        str(url.port or 5432),
        "-U",
        url.username or "postgres",
        "-d",
        url.database or "postgres",
    ]


def _require(tool: str) -> None:
    if shutil.which(tool) is None:
        raise RuntimeError(f"{tool} not found in PATH; install the PostgreSQL client")


def backup_database(
    database_url: str,
    destination: Path,
    *,
    runner: Runner = subprocess.run,
    env: Optional[Mapping[str, str]] = None,
) -> BackupResult:
    """Create a consistent backup of ``database_url`` at ``destination``."""
    url = make_url(database_url)
    backend = url.get_backend_name()
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)

    if backend == "sqlite":
        _sqlite_copy(_sqlite_file(url), destination)
    elif backend == "postgresql":
        _require("pg_dump")
        runner(
            [
                "pg_dump",
                "--format=custom",
                "--no-owner",
                "--file",
                str(destination),
                *_pg_connection_args(url),
            ],
            check=True,
            env=_pg_env(url, env),
        )
    else:
        raise ValueError(f"unsupported database backend: {backend}")

    return BackupResult(
        path=destination,
        backend=backend,
        size_bytes=destination.stat().st_size,
    )


def restore_database(
    database_url: str,
    source: Path,
    *,
    runner: Runner = subprocess.run,
    env: Optional[Mapping[str, str]] = None,
) -> None:
    """Restore ``source`` into ``database_url``, replacing existing objects."""
    source = Path(source)
    if not source.is_file():
        raise FileNotFoundError(f"backup file not found: {source}")

    url = make_url(database_url)
    backend = url.get_backend_name()

    if backend == "sqlite":
        destination = url.database
        if not destination or destination == ":memory:":
            raise ValueError("cannot restore into an in-memory SQLite database")
        _sqlite_copy(source, Path(destination))
    elif backend == "postgresql":
        _require("pg_restore")
        runner(
            [
                "pg_restore",
                "--clean",
                "--if-exists",
                "--no-owner",
                str(source),
                *_pg_connection_args(url),
            ],
            check=True,
            env=_pg_env(url, env),
        )
    else:
        raise ValueError(f"unsupported database backend: {backend}")


def main(argv: list[str] | None = None) -> int:
    from app.config import settings

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("backup", "restore"))
    parser.add_argument("--url", default=settings.database_url)
    parser.add_argument("--output", type=Path, help="destination for `backup`")
    parser.add_argument("--input", type=Path, help="source for `restore`")
    args = parser.parse_args(argv)

    if args.action == "backup":
        if args.output is None:
            parser.error("--output is required for backup")
        result = backup_database(args.url, args.output)
        print(f"{result.backend} backup written to {result.path} ({result.size_bytes} bytes)")
    else:
        if args.input is None:
            parser.error("--input is required for restore")
        restore_database(args.url, args.input)
        print(f"restored {args.input} into {args.url}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
