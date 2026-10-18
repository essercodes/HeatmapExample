"""Apply the SQL files in schema_migrations/ and record each one in the schema_migrations table.

Usage: python migrate.py (DATABASE_URL selects the target; works against local Postgres or RDS)
"""

import hashlib
import os
from pathlib import Path

import psycopg

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://heatmap:heatmap@localhost:5432/heatmap"
)
MIGRATIONS_DIR = Path(__file__).parent / "migrations"

# Arbitrary constant so concurrent runners (e.g. two services starting at once) serialize.
LOCK_ID = 727274

# Creates the schema_migrations table; run before anything else so the applied list can be read.
BOOTSTRAP = MIGRATIONS_DIR / "0000_schema_migrations.sql"


def main():
    files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    with psycopg.connect(DATABASE_URL) as conn:
        _ = conn.execute("SELECT pg_advisory_lock(%s)", (LOCK_ID,))
        _ = conn.execute(BOOTSTRAP.read_bytes())
        conn.commit()

        applied = dict(conn.execute("SELECT version, checksum FROM schema_migrations"))

        for path in files:
            sql = path.read_bytes()
            checksum = hashlib.sha256(sql).hexdigest()

            if path.stem in applied:
                if applied[path.stem] != checksum:
                    raise RuntimeError(f"{path.name} was modified after it was applied")
                continue

            # One transaction per migration: the DDL and its bookkeeping row commit together.
            with conn.transaction():
                _ = conn.execute(sql)
                _ = conn.execute(
                    "INSERT INTO schema_migrations (version, checksum) VALUES (%s, %s)",
                    (path.stem, checksum),
                )
            print(f"applied {path.name}")

        _ = conn.execute("SELECT pg_advisory_unlock(%s)", (LOCK_ID,))


if __name__ == "__main__":
    main()
