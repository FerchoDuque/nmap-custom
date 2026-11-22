"""Backup/restore is deterministic and never leaks credentials into argv."""

from __future__ import annotations

import sqlite3
import subprocess

import pytest

from app.core import backup

POSTGRES_URL = "postgresql+psycopg2://scanner:s3cr3t%40pw@db.internal:6543/network_scanner"


def _make_sqlite(path, value: str = "kept") -> None:
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE items (name TEXT)")
        conn.execute("INSERT INTO items (name) VALUES (?)", (value,))
        conn.commit()


class _FakeRunner:
    def __init__(self):
        self.calls = []

    def __call__(self, args, **kwargs):
        self.calls.append((args, kwargs))
        return subprocess.CompletedProcess(args=args, returncode=0)


@pytest.fixture()
def sqlite_db(tmp_path):
    path = tmp_path / "app.db"
    _make_sqlite(path)
    return path


def test_sqlite_backup_and_restore_round_trip(tmp_path, sqlite_db):
    dump = tmp_path / "backups" / "app.db"

    result = backup.backup_database(f"sqlite:///{sqlite_db.as_posix()}", dump)

    assert result.backend == "sqlite"
    assert result.path == dump
    assert result.size_bytes > 0

    target = tmp_path / "restored.db"
    backup.restore_database(f"sqlite:///{target.as_posix()}", dump)

    with sqlite3.connect(target) as conn:
        assert conn.execute("SELECT name FROM items").fetchone() == ("kept",)


def test_in_memory_sqlite_cannot_be_backed_up(tmp_path):
    with pytest.raises(ValueError, match="in-memory"):
        backup.backup_database("sqlite:///:memory:", tmp_path / "x.db")


def test_missing_sqlite_file_is_reported(tmp_path):
    with pytest.raises(FileNotFoundError, match="database not found"):
        backup.backup_database(f"sqlite:///{(tmp_path / 'nope.db').as_posix()}", tmp_path / "x.db")


def test_restore_requires_an_existing_dump(tmp_path):
    with pytest.raises(FileNotFoundError, match="backup file not found"):
        backup.restore_database(f"sqlite:///{(tmp_path / 't.db').as_posix()}", tmp_path / "nope.dump")


def test_postgres_backup_uses_pg_dump_and_hides_the_password(tmp_path, monkeypatch):
    monkeypatch.setattr(backup.shutil, "which", lambda tool: f"/usr/bin/{tool}")
    runner = _FakeRunner()
    dump = tmp_path / "db.dump"
    dump.write_bytes(b"custom-format")

    result = backup.backup_database(POSTGRES_URL, dump, runner=runner, env={"PATH": "/usr/bin"})

    assert result.backend == "postgresql"
    args, kwargs = runner.calls[0]
    assert args[:3] == ["pg_dump", "--format=custom", "--no-owner"]
    assert "-h" in args and "db.internal" in args
    assert "6543" in args and "network_scanner" in args
    assert "s3cr3t" not in " ".join(args)
    assert kwargs["env"]["PGPASSWORD"] == "s3cr3t@pw"
    assert kwargs["check"] is True


def test_postgres_restore_uses_pg_restore_clean(tmp_path, monkeypatch):
    monkeypatch.setattr(backup.shutil, "which", lambda tool: f"/usr/bin/{tool}")
    runner = _FakeRunner()
    dump = tmp_path / "db.dump"
    dump.write_bytes(b"custom-format")

    backup.restore_database(POSTGRES_URL, dump, runner=runner, env={"PATH": "/usr/bin"})

    args, kwargs = runner.calls[0]
    assert args[0] == "pg_restore"
    assert "--clean" in args and "--if-exists" in args
    assert str(dump) in args
    assert "s3cr3t" not in " ".join(args)
    assert kwargs["env"]["PGPASSWORD"] == "s3cr3t@pw"


def test_postgres_backup_requires_the_client(tmp_path, monkeypatch):
    monkeypatch.setattr(backup.shutil, "which", lambda tool: None)

    with pytest.raises(RuntimeError, match="pg_dump not found"):
        backup.backup_database(POSTGRES_URL, tmp_path / "db.dump", runner=_FakeRunner())


def test_unsupported_backend_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="unsupported database backend: mysql"):
        backup.backup_database("mysql://user@host/db", tmp_path / "db.dump")


def test_cli_backup_prints_the_result(tmp_path, capsys, monkeypatch):
    db = tmp_path / "app.db"
    _make_sqlite(db)

    code = backup.main(
        [
            "backup",
            "--url",
            f"sqlite:///{db.as_posix()}",
            "--output",
            str(tmp_path / "out.db"),
        ]
    )

    assert code == 0
    assert "sqlite backup written" in capsys.readouterr().out
