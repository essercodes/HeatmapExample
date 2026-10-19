"""Shared fixtures for the booking service tests.

Integration tests run against a throwaway database (heatmap_test_booking) on the Postgres
server named by TEST_ADMIN_DATABASE_URL; it is created and migrated once per session, then
dropped. When that server is unreachable, tests that need the database are skipped.
"""

import os
import sys
from collections.abc import Iterator

import psycopg
import pytest
from flask.testing import FlaskClient
from psycopg import sql
from psycopg.conninfo import make_conninfo
from psycopg_pool import ConnectionPool

ADMIN_DATABASE_URL = os.environ.get(
    "TEST_ADMIN_DATABASE_URL", "postgresql://heatmap:heatmap@localhost:5432/heatmap"
)
TEST_DB_NAME = "heatmap_test_booking"
TEST_DATABASE_URL = make_conninfo(ADMIN_DATABASE_URL, dbname=TEST_DB_NAME)

# db.py, migrate.py and mock_api.py read these at import time, so set them before any test module imports them.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["MOCK_API_DELAY_MS"] = "0"


def pytest_sessionfinish() -> None:
    # Close the pool even when the database fixture never ran (e.g. Postgres was unreachable),
    # so its worker threads don't outlive the interpreter.
    if "db" in sys.modules:
        import db

        db.pool.close()


def _admin_connect() -> psycopg.Connection:
    return psycopg.connect(ADMIN_DATABASE_URL, autocommit=True, connect_timeout=3)


@pytest.fixture(scope="session")
def database() -> Iterator[str]:
    """Create and migrate the test database, and point db.pool at it; yields its URL."""
    try:
        admin = _admin_connect()
    except psycopg.OperationalError as exc:
        pytest.skip(f"Postgres unavailable at {ADMIN_DATABASE_URL}: {exc}")

    name = sql.Identifier(TEST_DB_NAME)
    with admin:
        _ = admin.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(name))
        _ = admin.execute(sql.SQL("CREATE DATABASE {}").format(name))

    import migrate

    migrate.main()

    # The pool db.py opened at import time started before this database existed, and may be
    # backing off between reconnect attempts; swap in a fresh one that is ready now.
    import db

    db.pool.close()
    db.pool = ConnectionPool(TEST_DATABASE_URL, min_size=1, max_size=5, open=True, timeout=5)
    db.pool.wait()

    yield TEST_DATABASE_URL

    db.pool.close()
    with _admin_connect() as admin:
        _ = admin.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(name))


@pytest.fixture
def conn(database: str) -> Iterator[psycopg.Connection]:
    """A connection to an empty bookings table."""
    with psycopg.connect(database, autocommit=True) as conn:
        _ = conn.execute("TRUNCATE bookings RESTART IDENTITY")
        yield conn


@pytest.fixture
def client() -> FlaskClient:
    from app import app

    app.config["TESTING"] = True
    return app.test_client()
