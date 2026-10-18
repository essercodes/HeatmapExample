from typing import cast

from flask import Flask, jsonify, request
from psycopg import DataError, sql
from psycopg import Error as DBError
from psycopg.rows import dict_row
from psycopg_pool import PoolTimeout

from db import get_conn

app = Flask(__name__)

# Columns a client may set on PUT, mapped to the JSON types each accepts (null is always allowed).
# `id` is generated and `trip_id` comes from the URL. Timestamps are ISO 8601 strings.
WRITABLE_COLUMNS: dict[str, tuple[type, ...]] = {
    "icabbi_id": (int,),
    "perma_id": (str,),
    "pickup_lat": (int, float),
    "pickup_lng": (int, float),
    "booking_vehicletype": (str,),
    "bookingdate_ms": (str,),
    "event": (str,),
    "status": (str,),
    "synced_at": (str,),
}


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


@app.get("/data/<int:id>")
def get_data(id: int):
    """Pick up a single record."""
    try:
        with get_conn(timeout=2) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                row = cur.execute(
                    "SELECT * FROM bookings WHERE id = %s", (id,)
                ).fetchone()

    except (DBError, PoolTimeout) as exc:
        return jsonify(error=str(exc)), 503

    if row is None:
        return jsonify(error="not found"), 404

    return jsonify(row)


@app.put("/data/<id>")
def put_data(id: str):
    """Put down (create or replace) a single record, keyed by trip_id."""
    body: object = request.get_json(silent=True)

    if not isinstance(body, dict):
        return jsonify(error="expected a JSON object body"), 400

    # JSON object keys are always strings.
    payload = cast(dict[str, object], body)
    unknown = set(payload) - set(WRITABLE_COLUMNS)

    if unknown:
        return jsonify(error=f"unknown fields: {', '.join(sorted(unknown))}"), 400

    # bool is a subclass of int in Python, so reject it explicitly.
    invalid = [
        col
        for col, value in payload.items()
        if value is not None
        and (isinstance(value, bool) or not isinstance(value, WRITABLE_COLUMNS[col]))
    ]

    if invalid:
        return jsonify(error=f"invalid types for fields: {', '.join(sorted(invalid))}"), 400

    # Fields left out of the payload are reset to NULL, since PUT replaces the record.
    params: dict[str, object] = {col: payload.get(col) for col in WRITABLE_COLUMNS}
    params["trip_id"] = id

    columns = sql.SQL(", ").join(map(sql.Identifier, WRITABLE_COLUMNS))
    values = sql.SQL(", ").join(map(sql.Placeholder, WRITABLE_COLUMNS))
    updates = sql.SQL(", ").join(
        sql.SQL("{col} = EXCLUDED.{col}").format(col=sql.Identifier(col))
        for col in WRITABLE_COLUMNS
    )

    query = sql.SQL('''
    INSERT INTO bookings (trip_id, {columns}) VALUES (%(trip_id)s, {values})
    ON CONFLICT (trip_id) DO UPDATE SET {updates} RETURNING *
    ''').format(columns=columns, values=values, updates=updates)

    try:
        with get_conn(timeout=2) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                row = cur.execute(query, params).fetchone()

    except DataError as exc:
        return jsonify(error=str(exc)), 400

    except (DBError, PoolTimeout) as exc:
        return jsonify(error=str(exc)), 503

    return jsonify(row), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)

