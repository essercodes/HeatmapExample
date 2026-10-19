"""Tests for the migration runner.

Each test gets its own empty database (heatmap_test_booking_migrations) on the Postgres server
named by TEST_ADMIN_DATABASE_URL, created before and dropped after, rather than the session's
already-migrated booking database. When that server is unreachable, these tests are skipped.
"""

import hashlib
import os
import shutil
from collections.abc import Iterator
from pathlib import Path
from typing import LiteralString

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import make_conninfo

import migrate

ADMIN_DATABASE_URL = os.environ.get(
    "TEST_ADMIN_DATABASE_URL", "postgresql://heatmap:heatmap@localhost:5432/heatmap"
)
TEST_DB_NAME = "heatmap_test_booking_migrations"
TEST_DATABASE_URL = make_conninfo(ADMIN_DATABASE_URL, dbname=TEST_DB_NAME)


def _admin_connect() -> psycopg.Connection:
    return psycopg.connect(ADMIN_DATABASE_URL, autocommit=True, connect_timeout=3)


def _drop(admin: psycopg.Connection) -> None:
    _ = admin.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(TEST_DB_NAME)))


@pytest.fixture
def empty_conn(monkeypatch: pytest.MonkeyPatch) -> Iterator[psycopg.Connection]:
    """A connection to an empty database that migrate.main() targets."""
    try:
        admin = _admin_connect()
    except psycopg.OperationalError as exc:
        pytest.skip(f"Postgres unavailable at {ADMIN_DATABASE_URL}: {exc}")

    with admin:
        _drop(admin)
        _ = admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(TEST_DB_NAME)))

    monkeypatch.setattr(migrate, "DATABASE_URL", TEST_DATABASE_URL)
    with psycopg.connect(TEST_DATABASE_URL, autocommit=True) as conn:
        yield conn

    with _admin_connect() as admin:
        _drop(admin)


@pytest.fixture
def migrations_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A scratch copy of the real migrations that migrate.main() reads instead; add files to it freely."""
    path = tmp_path / "migrations"
    _ = shutil.copytree(migrate.MIGRATIONS_DIR, path)
    monkeypatch.setattr(migrate, "MIGRATIONS_DIR", path)
    return path


def rows(conn: psycopg.Connection, query: LiteralString) -> list[tuple[object, ...]]:
    return conn.execute(query).fetchall()


def scalar(conn: psycopg.Connection, query: LiteralString) -> object:
    result = rows(conn, query)
    assert len(result) == 1
    return result[0][0]


def applied(conn: psycopg.Connection) -> dict[str, object]:
    return {
        str(version): checksum
        for version, checksum in rows(conn, "SELECT version, checksum FROM booking_migrations")
    }


def test_migration_filenames_have_unique_semantic_versions() -> None:
    files = sorted(migrate.MIGRATIONS_DIR.glob("*.sql"))
    assert files, "no migrations found"
    assert len(migrate.migrations()) == len(files)


def test_migrations_apply_in_semantic_version_order(migrations_dir: Path) -> None:
    for name in ["1.10.0_ten.sql", "1.9.0_nine.sql", "2.0.0_two.sql", "1.0.1_patch.sql"]:
        _ = (migrations_dir / name).write_text("SELECT 1;")

    assert [version for version, _ in migrate.migrations()] == ["1.0.0", "1.0.1", "1.9.0", "1.10.0", "2.0.0"]


@pytest.mark.parametrize("name", ["0001_bookings.sql", "1.0_short.sql", "01.0.0_leading_zero.sql", "1.1.0-Dash.sql"])
def test_misnamed_migration_is_rejected(migrations_dir: Path, name: str) -> None:
    _ = (migrations_dir / name).write_text("SELECT 1;")

    with pytest.raises(RuntimeError, match="doesn't match"):
        _ = migrate.migrations()


def test_duplicate_version_is_rejected(migrations_dir: Path) -> None:
    _ = (migrations_dir / "1.0.0_again.sql").write_text("SELECT 1;")

    with pytest.raises(RuntimeError, match="share version 1.0.0"):
        _ = migrate.migrations()


def test_fresh_database_applies_every_migration(empty_conn: psycopg.Connection, capsys: pytest.CaptureFixture[str]) -> None:
    migrate.main()

    pending = migrate.migrations()
    assert applied(empty_conn) == {version: hashlib.sha256(path.read_bytes()).hexdigest() for version, path in pending}
    assert capsys.readouterr().out.splitlines() == [f"applied {path.name}" for _, path in pending]


def test_rerun_is_a_no_op(empty_conn: psycopg.Connection, capsys: pytest.CaptureFixture[str]) -> None:
    migrate.main()
    before = rows(empty_conn, "SELECT version, filename, checksum, applied_at FROM booking_migrations")
    _ = capsys.readouterr()

    migrate.main()

    assert capsys.readouterr().out == ""
    assert rows(empty_conn, "SELECT version, filename, checksum, applied_at FROM booking_migrations") == before


def test_new_migration_is_applied_incrementally(empty_conn: psycopg.Connection, migrations_dir: Path) -> None:
    migrate.main()
    _ = (migrations_dir / "9.0.0_extra.sql").write_text("CREATE TABLE extra (id integer);")

    migrate.main()

    assert scalar(empty_conn, "SELECT filename FROM booking_migrations WHERE version = '9.0.0'") == "9.0.0_extra.sql"
    assert scalar(empty_conn, "SELECT to_regclass('extra')") == "extra"


def test_out_of_order_migration_is_rejected(empty_conn: psycopg.Connection, migrations_dir: Path) -> None:
    _ = (migrations_dir / "2.0.0_newer.sql").write_text("SELECT 1;")
    migrate.main()
    _ = (migrations_dir / "1.5.0_older.sql").write_text("CREATE TABLE older (id integer);")

    with pytest.raises(RuntimeError, match="1.5.0_older.sql is older than applied version 2.0.0"):
        migrate.main()

    assert "1.5.0" not in applied(empty_conn)
    assert scalar(empty_conn, "SELECT to_regclass('older')") is None


@pytest.mark.usefixtures("empty_conn")
def test_modified_migration_is_rejected(migrations_dir: Path) -> None:
    migrate.main()
    _ = (migrations_dir / "1.0.0_create_bookings.sql").write_text("-- edited after it was applied\n", "utf-8")

    with pytest.raises(RuntimeError, match="1.0.0_create_bookings.sql was modified"):
        migrate.main()


def test_failed_migration_rolls_back(empty_conn: psycopg.Connection, migrations_dir: Path) -> None:
    _ = (migrations_dir / "9.0.0_good.sql").write_text("CREATE TABLE good (id integer);")
    _ = (migrations_dir / "9.0.1_bad.sql").write_text("CREATE TABLE half (id integer); SELECT nope;")

    with pytest.raises(psycopg.errors.UndefinedColumn):
        migrate.main()

    versions = applied(empty_conn)
    assert "9.0.0" in versions, "migrations before the failure stay committed"
    assert "9.0.1" not in versions
    assert scalar(empty_conn, "SELECT to_regclass('half')") is None

    # Fixing the file lets the next run pick up where it stopped.
    _ = (migrations_dir / "9.0.1_bad.sql").write_text("CREATE TABLE half (id integer);")
    migrate.main()
    assert "9.0.1" in applied(empty_conn)


def test_bookings_schema(empty_conn: psycopg.Connection) -> None:
    migrate.main()

    columns = {
        str(name): data_type
        for name, data_type in rows(
            empty_conn,
            "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'bookings'",
        )
    }
    assert columns == {
        "id": "integer",
        "trip_id": "text",
        "icabbi_id": "integer",
        "perma_id": "text",
        "pickup_lat": "real",
        "pickup_lng": "real",
        "booking_vehicletype": "text",
        "bookingdate_ms": "timestamp without time zone",
        "event": "text",
        "status": "text",
        "synced_at": "timestamp without time zone",
    }

    # The booking service's upsert relies on ON CONFLICT (trip_id).
    _ = empty_conn.execute("INSERT INTO bookings (trip_id) VALUES ('trip-1')")
    with pytest.raises(psycopg.errors.UniqueViolation):
        _ = empty_conn.execute("INSERT INTO bookings (trip_id) VALUES ('trip-1')")
    with pytest.raises(psycopg.errors.NotNullViolation):
        _ = empty_conn.execute("INSERT INTO bookings (trip_id) VALUES (NULL)")


def test_existing_bookings_table_is_adopted(empty_conn: psycopg.Connection) -> None:
    """Databases migrated by the old shared schema_migrations runner already have bookings."""
    _ = empty_conn.execute((migrate.MIGRATIONS_DIR / "1.0.0_create_bookings.sql").read_bytes())
    _ = empty_conn.execute("INSERT INTO bookings (trip_id) VALUES ('trip-1')")

    migrate.main()

    assert "1.0.0" in applied(empty_conn)
    assert scalar(empty_conn, "SELECT count(*) FROM bookings") == 1
