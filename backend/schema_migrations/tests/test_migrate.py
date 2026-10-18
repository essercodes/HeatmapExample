import hashlib
import re

import psycopg
import pytest

import migrate


def applied(conn):
    return dict(conn.execute("SELECT version, checksum FROM schema_migrations ORDER BY version"))


def test_migration_filenames_are_ordered_and_unique():
    """Files apply in sorted order, so each needs a unique, zero-padded numeric prefix."""
    names = [p.name for p in sorted(migrate.MIGRATIONS_DIR.glob("*.sql"))]
    assert names[0] == migrate.BOOTSTRAP.name
    prefixes = []
    for name in names:
        match = re.fullmatch(r"(\d{4})_[a-z0-9_]+\.sql", name)
        assert match, f"{name} doesn't match NNNN_description.sql"
        prefixes.append(match[1])
    assert len(set(prefixes)) == len(prefixes), "duplicate migration numbers"


def test_fresh_database_applies_every_migration(conn, capsys):
    migrate.main()

    files = sorted(migrate.MIGRATIONS_DIR.glob("*.sql"))
    assert applied(conn) == {p.stem: hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    assert capsys.readouterr().out.splitlines() == [f"applied {p.name}" for p in files]


def test_rerun_is_a_no_op(conn, capsys):
    migrate.main()
    before = conn.execute("SELECT version, checksum, applied_at FROM schema_migrations").fetchall()
    capsys.readouterr()

    migrate.main()

    assert capsys.readouterr().out == ""
    assert conn.execute("SELECT version, checksum, applied_at FROM schema_migrations").fetchall() == before


def test_new_migration_is_applied_incrementally(conn, migrations_dir):
    migrate.main()
    (migrations_dir / "9999_extra.sql").write_text("CREATE TABLE extra (id integer);")

    migrate.main()

    assert "9999_extra" in applied(conn)
    assert conn.execute("SELECT to_regclass('extra')").fetchone()[0] == "extra"


def test_modified_migration_is_rejected(conn, migrations_dir):
    migrate.main()
    (migrations_dir / "0001_bookings.sql").write_text("-- edited after it was applied\n", "utf-8")

    with pytest.raises(RuntimeError, match="0001_bookings.sql was modified"):
        migrate.main()


def test_failed_migration_rolls_back(conn, migrations_dir):
    (migrations_dir / "9998_good.sql").write_text("CREATE TABLE good (id integer);")
    (migrations_dir / "9999_bad.sql").write_text("CREATE TABLE half (id integer); SELECT nope;")

    with pytest.raises(psycopg.errors.UndefinedColumn):
        migrate.main()

    versions = applied(conn)
    assert "9998_good" in versions, "migrations before the failure stay committed"
    assert "9999_bad" not in versions
    assert conn.execute("SELECT to_regclass('half')").fetchone()[0] is None

    # Fixing the file lets the next run pick up where it stopped.
    (migrations_dir / "9999_bad.sql").write_text("CREATE TABLE half (id integer);")
    migrate.main()
    assert "9999_bad" in applied(conn)


def test_bookings_schema(conn):
    migrate.main()

    columns = dict(
        conn.execute(
            "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'bookings'"
        )
    )
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
    conn.execute("INSERT INTO bookings (trip_id) VALUES ('trip-1')")
    with pytest.raises(psycopg.errors.UniqueViolation):
        conn.execute("INSERT INTO bookings (trip_id) VALUES ('trip-1')")
    with pytest.raises(psycopg.errors.NotNullViolation):
        conn.execute("INSERT INTO bookings (trip_id) VALUES (NULL)")
