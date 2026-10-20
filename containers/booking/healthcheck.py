"""Container health check; exits 0 when healthy.

`python healthcheck.py`       the API (default command) answers GET /health with 2xx.
`python healthcheck.py live`  the API answers GET /live with 2xx, whatever the database's state.
`python healthcheck.py db`    the database is reachable, for one-shot jobs (migrate.py, sync.py).
"""

import os
import sys
import urllib.request

import psycopg

BASE_URL = "http://localhost:8000"  # gunicorn --bind in the Dockerfile


def check_api():
    urllib.request.urlopen(f"{BASE_URL}/health", timeout=3).close()  # pyright: ignore[reportAny]


def check_live():
    urllib.request.urlopen(f"{BASE_URL}/live", timeout=3).close()  # pyright: ignore[reportAny]


def check_db():
    psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=3).close()


checks = {"api": check_api, "live": check_live, "db": check_db}
mode = sys.argv[1] if len(sys.argv) > 1 else "api"

try:
    checks[mode]()
except Exception as exc:
    print(f"unhealthy ({mode}): {exc}", file=sys.stderr)
    sys.exit(1)
