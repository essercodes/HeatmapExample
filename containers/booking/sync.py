"""Sync active bookings from the (mock) upstream API into the database.

One sync per run: `python sync.py`. It's scheduled by EventBridge on ECS (terraform/ecs.tf)
and by the booking-sync sidecar in compose.yaml.
"""
from datetime import datetime

from db import get_conn, pool, upsert_bookings_query
from mock_api import fetch_active_bookings


def sync_data() -> int:
    """Upsert every active booking from the upstream API; returns how many were written."""
    bookings = fetch_active_bookings()
    if not bookings:
        return 0

    synced_at = datetime.now()
    for booking in bookings:
        booking["synced_at"] = synced_at

    with get_conn(timeout=10) as conn:
        with conn.cursor() as cur:
            cur.executemany(upsert_bookings_query(bookings[0]), bookings)

    return len(bookings)


if __name__ == "__main__":
    try:
        count = sync_data()
    finally:
        pool.close()
    print(f"{datetime.now().isoformat(timespec='seconds')} synced {count} active bookings")
