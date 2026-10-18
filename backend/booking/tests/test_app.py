from contextlib import contextmanager
from email.utils import parsedate_to_datetime

import pytest
from psycopg_pool import PoolTimeout

import app as app_module


@pytest.fixture
def db_down(monkeypatch):
    @contextmanager
    def unavailable(timeout=None):
        raise PoolTimeout("couldn't get a connection after 2.00 sec")
        yield

    monkeypatch.setattr(app_module, "get_conn", unavailable)


@pytest.mark.parametrize(
    "method, path",
    [("get", "/data"), ("get", "/data/trip-1"), ("put", "/data/trip-1")],
)
def test_returns_503_when_database_unavailable(client, db_down, method, path):
    response = getattr(client, method)(path)
    assert response.status_code == 503
    assert "error" in response.get_json()


def test_health_degraded_when_database_unavailable(client, db_down):
    response = client.get("/health")
    assert response.status_code == 503
    assert response.get_json()["status"] == "degraded"


def test_health(client, conn):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "database": "ok"}


def test_list_empty(client, conn):
    response = client.get("/data")
    assert response.status_code == 200
    assert response.get_json() == []


def test_get_missing_returns_404(client, conn):
    response = client.get("/data/trip-missing")
    assert response.status_code == 404
    assert response.get_json() == {"error": "not found"}


def test_put_then_get(client, conn):
    put = client.put("/data/trip-1")
    assert put.status_code == 200
    stored = put.get_json()
    assert stored["trip_id"] == "trip-1"
    assert stored["synced_at"] is not None

    get = client.get("/data/trip-1")
    assert get.status_code == 200
    assert get.get_json() == stored

    listed = client.get("/data").get_json()
    assert listed == [stored]


def test_put_twice_replaces(client, conn):
    first = client.put("/data/trip-1").get_json()
    second = client.put("/data/trip-1").get_json()

    assert second["id"] == first["id"]
    assert parsedate_to_datetime(second["synced_at"]) >= parsedate_to_datetime(first["synced_at"])
    assert len(client.get("/data").get_json()) == 1


def test_put_ignores_request_body(client, conn):
    """PUT always pulls the booking from upstream; a client can't overwrite fields."""
    response = client.put("/data/trip-1", json={"trip_id": "trip-2", "status": "hacked"})
    body = response.get_json()
    assert body["trip_id"] == "trip-1"
    assert body["status"] != "hacked"
