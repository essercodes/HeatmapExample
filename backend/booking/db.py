import os

from psycopg import sql
from psycopg_pool import ConnectionPool

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://heatmap:heatmap@heatmap-db:5432/heatmap"
)

# Opens in the background; checkouts wait (up to `timeout`) until the database is reachable.
pool = ConnectionPool(DATABASE_URL, min_size=1, max_size=5, open=True, timeout=5)


def get_conn(timeout: float | None = None):
    """Borrow a connection: `with get_conn() as conn: conn.execute(...)`."""
    return pool.connection(timeout=timeout)


def upsert_bookings_query(columns) -> sql.Composed:
    """Insert a booking, or replace the existing row with the same trip_id; returns the row."""
    updates = sql.SQL(", ").join(
        sql.SQL("{col} = EXCLUDED.{col}").format(col=sql.Identifier(col))
        for col in columns
        if col != "trip_id"
    )
    return sql.SQL('''
    INSERT INTO bookings ({columns}) VALUES ({values})
    ON CONFLICT (trip_id) DO UPDATE SET {updates} RETURNING *
    ''').format(
        columns=sql.SQL(", ").join(map(sql.Identifier, columns)),
        values=sql.SQL(", ").join(map(sql.Placeholder, columns)),
        updates=updates,
    )
