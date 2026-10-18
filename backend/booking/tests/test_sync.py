import mock_api
import sync


def test_sync_writes_all_active_bookings(conn):
    count = sync.sync_data()

    assert 400 <= count <= 600
    rows = conn.execute("SELECT status, synced_at FROM bookings").fetchall()
    assert len(rows) == count
    assert {status for status, _ in rows} == {"active"}
    assert len({synced_at for _, synced_at in rows}) == 1, "one sync shares one synced_at"


def test_repeated_syncs_upsert(conn):
    sync.sync_data()
    sync.sync_data()

    total, distinct = conn.execute("SELECT count(*), count(DISTINCT trip_id) FROM bookings").fetchone()
    assert total == distinct
    assert total <= len(mock_api.ACTIVE_TRIP_IDS)


def test_sync_with_no_bookings(conn, monkeypatch):
    monkeypatch.setattr(sync, "fetch_active_bookings", lambda: [])
    assert sync.sync_data() == 0
    assert conn.execute("SELECT count(*) FROM bookings").fetchone()[0] == 0
