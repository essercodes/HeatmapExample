"""Shared fixtures for the migration runner tests.

Each test gets its own empty database (heatmap_test_migrations) on the Postgres server named by
TEST_ADMIN_DATABASE_URL, created before and dropped after. When that server is unreachable, tests
that need the database are skipped.
"""

import os
import shutil
from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import make_conninfo

import migrate

ADMIN_DATABASE_URL = os.environ.get(
    "TEST_ADMIN_DATABASE_URL", "postgresql://heatmap:heatmap@localhost:5432/heatmap"
)
TEST_DB_NAME = "heatmap_test_migrations"
TEST_DATABASE_URL = make_conninfo(ADMIN_DATABASE_URL, dbname=TEST_DB_NAME)


def _admin_connect() -> psycopg.Connection:
    return psycopg.connect(ADMIN_DATABASE_URL, autocommit=True, connect_timeout=3)


def _drop(admin: psycopg.Connection) -> None:
    _ = admin.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(TEST_DB_NAME)))


@pytest.fixture
def database(monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    """An empty database that migrate.main() targets; yields its URL."""
    try:
        admin = _admin_connect()
    except psycopg.OperationalError as exc:
        pytest.skip(f"Postgres unavailable at {ADMIN_DATABASE_URL}: {exc}")

    with admin:
        _drop(admin)
        _ = admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(TEST_DB_NAME)))

    monkeypatch.setattr(migrate, "DATABASE_URL", TEST_DATABASE_URL)
    yield TEST_DATABASE_URL

    with _admin_connect() as admin:
        _drop(admin)


@pytest.fixture
def conn(database: str) -> Iterator[psycopg.Connection]:
    with psycopg.connect(database, autocommit=True) as conn:
        yield conn


@pytest.fixture
def migrations_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A scratch copy of the real migrations that migrate.main() reads instead; add files to it freely."""
    path = tmp_path / "migrations"
    _ = shutil.copytree(migrate.MIGRATIONS_DIR, path)
    monkeypatch.setattr(migrate, "MIGRATIONS_DIR", path)
    monkeypatch.setattr(migrate, "BOOTSTRAP", path / migrate.BOOTSTRAP.name)
    return path
