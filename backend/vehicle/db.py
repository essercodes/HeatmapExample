import os

from psycopg_pool import ConnectionPool

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://heatmap:heatmap@heatmap-db:5432/heatmap"
)

# Opens in the background; checkouts wait (up to `timeout`) until the database is reachable.
pool = ConnectionPool(DATABASE_URL, min_size=1, max_size=5, open=True, timeout=5)


def get_conn(timeout=None):
    """Borrow a connection: `with get_conn() as conn: conn.execute(...)`."""
    return pool.connection(timeout=timeout)
