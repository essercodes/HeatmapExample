from flask import Flask, jsonify, request
from psycopg import Error as DBError
from psycopg_pool import PoolTimeout

from db import get_conn

app = Flask(__name__)

# In-memory stand-in for the database until persistence is wired up.
_store: dict[str, object] = {}


@app.get("/live")
def live():
    """Liveness: the server is answering requests. Doesn't touch the database, unlike /health."""
    return jsonify(status="ok")


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
    return jsonify(_store)


@app.get("/data/<key>")
def get_data(key: str):
    """Pick up a single record."""
    # TODO: read from the database via get_conn()
    if key not in _store:
        return jsonify(error="not found"), 404
    return jsonify(_store[key])


@app.put("/data/<key>")
def put_data(key: str):
    """Put down (create or replace) a single record."""
    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify(error="expected a JSON body"), 400
    # TODO: write to the database via get_conn()
    _store[key] = payload
    return jsonify(payload), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
