import psycopg
import pytest

import mock_api
import sync


def test_sync_writes_all_active_bookings(conn: psycopg.Connection) -> None:
    count = sync.sync_data()

    assert 400 <= count <= 600
    rows: list[tuple[object, ...]] = conn.execute("SELECT status, synced_at FROM bookings").fetchall()
    assert len(rows) == count
    assert {status for status, _ in rows} == {"active"}
    assert len({synced_at for _, synced_at in rows}) == 1, "one sync shares one synced_at"


def test_repeated_syncs_upsert(conn: psycopg.Connection) -> None:
    _ = sync.sync_data()
    _ = sync.sync_data()

    counts: tuple[object, ...] | None = conn.execute("SELECT count(*), count(DISTINCT trip_id) FROM bookings").fetchone()
    assert counts is not None
    total, distinct = counts
    assert isinstance(total, int)
    assert total == distinct
    assert total <= len(mock_api.ACTIVE_TRIP_IDS)


def test_sync_with_no_bookings(conn: psycopg.Connection, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sync, "fetch_active_bookings", lambda: list[dict[str, object]]())
    assert sync.sync_data() == 0
    row = conn.execute("SELECT count(*) FROM bookings").fetchone()
    assert row is not None
    assert row[0] == 0
