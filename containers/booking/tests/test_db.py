from datetime import datetime

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

import mock_api
from db import upsert_bookings_query


def render(query: sql.Composed) -> str:
    return " ".join(query.as_string(None).split())


def test_upsert_query_shape() -> None:
    query = render(upsert_bookings_query({"trip_id": 1, "status": 2, "event": 3}))
    assert query == (
        'INSERT INTO bookings ("trip_id", "status", "event") '
        "VALUES (%(trip_id)s, %(status)s, %(event)s) "
        'ON CONFLICT (trip_id) DO UPDATE SET "status" = EXCLUDED."status", '
        '"event" = EXCLUDED."event" RETURNING *'
    )


def test_upsert_query_quotes_column_names() -> None:
    query = render(upsert_bookings_query({"trip_id": 1, 'x"; DROP TABLE bookings; --': 2}))
    assert '"x""; DROP TABLE bookings; --"' in query


def test_booking_fields_exist_in_schema(conn: psycopg.Connection) -> None:
    """Every field the service writes must be a column of the migrated bookings table."""
    columns = {
        row[0]
        for row in conn.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'bookings'"
        )
    }
    written = set(mock_api.fetch_booking("trip-x")) | {"synced_at"}
    assert written <= columns, f"missing columns: {written - columns}"


def test_upsert_inserts_then_replaces(conn: psycopg.Connection) -> None:
    first = mock_api.fetch_booking("trip-1") | {"synced_at": datetime(2026, 1, 1)}
    second = mock_api.fetch_booking("trip-1") | {"synced_at": datetime(2026, 1, 2), "status": "cancelled"}

    with conn.cursor(row_factory=dict_row) as cur:
        inserted = cur.execute(upsert_bookings_query(first), first).fetchone()
        updated = cur.execute(upsert_bookings_query(second), second).fetchone()
        rows = cur.execute("SELECT * FROM bookings").fetchall()

    assert inserted is not None and updated is not None
    assert len(rows) == 1
    assert updated["id"] == inserted["id"], "an upsert must keep the row's identity"
    assert updated["status"] == "cancelled"
    assert updated["synced_at"] == datetime(2026, 1, 2)
    assert updated["icabbi_id"] == second["icabbi_id"]
