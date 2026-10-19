"""Apply the booking service's SQL migrations and record each one in the booking_migrations table.

Each file in migrations/ is named <major>.<minor>.<patch>_<description>.sql and applies in semantic
version order. Run before the service starts by changing the container command: `python migrate.py`
(DATABASE_URL selects the target; works against local Postgres or RDS).
"""

import hashlib
import os
import re
from pathlib import Path

import psycopg

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://heatmap:heatmap@heatmap-db:5432/heatmap"
)
MIGRATIONS_DIR = Path(__file__).parent / "migrations"

# Serializes concurrent runners of this service's migrations (e.g. two deploys at once) without
# blocking other services' migration runners.
LOCK_KEY = "booking_migrations"

FILENAME = re.compile(r"(?P<version>(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*))_[a-z0-9_]+\.sql")

BOOTSTRAP = """
CREATE TABLE IF NOT EXISTS booking_migrations (
    version text PRIMARY KEY,
    filename text NOT NULL,
    checksum text NOT NULL,
    applied_at timestamptz NOT NULL DEFAULT now()
)
"""


# TODO: Add a method to check if container is running with compatible 
# MAJOR version database schema.
# MAJOR: version when you make incompatible changes
# MINOR: version when you add functionality in a backward compatible manner
# PATCH: version when you make backward compatible bug fixes

def semver(version: str) -> tuple[int, int, int]:
    major, minor, patch = (int(part) for part in version.split("."))
    return major, minor, patch


def migrations() -> list[tuple[str, Path]]:
    """(version, path) for every migration file, in semantic version order."""
    found: dict[str, Path] = {}
    for path in MIGRATIONS_DIR.glob("*.sql"):
        match = FILENAME.fullmatch(path.name)
        if not match:
            raise RuntimeError(f"{path.name} doesn't match <major>.<minor>.<patch>_<description>.sql")
        version = match["version"]
        if version in found:
            raise RuntimeError(f"{path.name} and {found[version].name} share version {version}")
        found[version] = path
    return sorted(found.items(), key=lambda item: semver(item[0]))


def main() -> None:
    pending = migrations()
    # Autocommit, so each conn.transaction() below is a real transaction rather than a savepoint
    # inside one implicit transaction spanning the whole run.
    with psycopg.connect(DATABASE_URL, autocommit=True) as conn:
        _ = conn.execute("SELECT pg_advisory_lock(hashtext(%s))", (LOCK_KEY,))
        _ = conn.execute(BOOTSTRAP)

        applied = dict(conn.execute("SELECT version, checksum FROM booking_migrations"))
        latest = max(map(semver, applied), default=None)

        for version, path in pending:
            sql = path.read_bytes()
            checksum = hashlib.sha256(sql).hexdigest()

            if version in applied:
                if applied[version] != checksum:
                    raise RuntimeError(f"{path.name} was modified after it was applied")
                continue

            # A new file below the newest applied version would run out of order (e.g. after
            # merging branches); give it a version above the latest instead.
            if latest is not None and semver(version) < latest:
                raise RuntimeError(f"{path.name} is older than applied version {'.'.join(map(str, latest))}")

            # One transaction per migration: the DDL and its bookkeeping row commit together.
            with conn.transaction():
                _ = conn.execute(sql)
                _ = conn.execute(
                    "INSERT INTO booking_migrations (version, filename, checksum) VALUES (%s, %s, %s)",
                    (version, path.name, checksum),
                )
            latest = semver(version)
            print(f"applied {path.name}")

        _ = conn.execute("SELECT pg_advisory_unlock(hashtext(%s))", (LOCK_KEY,))


if __name__ == "__main__":
    main()
