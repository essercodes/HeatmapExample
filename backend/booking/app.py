from datetime import datetime

from flask import Flask, jsonify
from psycopg import Error as DBError
from psycopg.rows import dict_row
from psycopg_pool import PoolTimeout

from db import get_conn, upsert_bookings_query
from mock_api import fetch_booking

app = Flask(__name__)

@app.get("/health")
def health():
    try:
        with get_conn(timeout=2) as conn:
            _ = conn.execute("SELECT 1")

    except (DBError, PoolTimeout) as exc:
        return jsonify(status="degraded", database=str(exc)), 503

    return jsonify(status="ok", database="ok")


@app.get("/data")
def list_data():
    """Pick up all stored records."""
    try:
        with get_conn(timeout=2) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                rows = cur.execute("SELECT * FROM bookings").fetchall()

    except (DBError, PoolTimeout) as exc:
        return jsonify(error=str(exc)), 503

    return jsonify(rows)


@app.get("/data/<trip_id>")
def get_data(trip_id: str):
    """Pick up a single record."""
    try:
        with get_conn(timeout=2) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                row = cur.execute(
                    "SELECT * FROM bookings WHERE trip_id = %s", (trip_id,)
                ).fetchone()

    except (DBError, PoolTimeout) as exc:
        return jsonify(error=str(exc)), 503

    if row is None:
        return jsonify(error="not found"), 404

    return jsonify(row)


@app.put("/data/<trip_id>")
def put_data(trip_id: str):
    """Put down (create or replace) a single record, keyed by trip_id, with data from the mock API."""
    booking = fetch_booking(trip_id)
    booking["synced_at"] = datetime.now()

    query = upsert_bookings_query(booking)

    try:
        with get_conn(timeout=2) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                row = cur.execute(query, booking).fetchone()

    except (DBError, PoolTimeout) as exc:
        return jsonify(error=str(exc)), 503

    return jsonify(row), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)

