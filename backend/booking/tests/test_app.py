from contextlib import AbstractContextManager
from email.utils import parsedate_to_datetime
from typing import cast

import pytest
from flask.testing import FlaskClient
from psycopg import Connection
from psycopg_pool import PoolTimeout
from werkzeug.test import TestResponse

import app as app_module

JsonObject = dict[str, object]


def json_object(response: TestResponse) -> JsonObject:
    body = cast(object, response.get_json())
    assert isinstance(body, dict)
    return cast(JsonObject, body)


def json_list(response: TestResponse) -> list[JsonObject]:
    body = cast(object, response.get_json())
    assert isinstance(body, list)
    return cast(list[JsonObject], body)


def http_date(value: object) -> str:
    assert isinstance(value, str)
    return value


@pytest.fixture
def db_down(monkeypatch: pytest.MonkeyPatch) -> None:
    def unavailable(timeout: float | None = None) -> AbstractContextManager[Connection]:
        raise PoolTimeout(f"couldn't get a connection after {timeout} sec")

    monkeypatch.setattr(app_module, "get_conn", unavailable)


@pytest.mark.usefixtures("db_down")
@pytest.mark.parametrize(
    "method, path",
    [("get", "/data"), ("get", "/data/trip-1"), ("put", "/data/trip-1")],
)
def test_returns_503_when_database_unavailable(
    client: FlaskClient, method: str, path: str
) -> None:
    response = client.open(path, method=method.upper())
    assert response.status_code == 503
    assert "error" in json_object(response)


@pytest.mark.usefixtures("db_down")
def test_health_degraded_when_database_unavailable(client: FlaskClient) -> None:
    response = client.get("/health")
    assert response.status_code == 503
    assert json_object(response)["status"] == "degraded"


@pytest.mark.usefixtures("conn")
def test_health(client: FlaskClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert json_object(response) == {"status": "ok", "database": "ok"}


@pytest.mark.usefixtures("conn")
def test_list_empty(client: FlaskClient) -> None:
    response = client.get("/data")
    assert response.status_code == 200
    assert json_list(response) == []


@pytest.mark.usefixtures("conn")
def test_get_missing_returns_404(client: FlaskClient) -> None:
    response = client.get("/data/trip-missing")
    assert response.status_code == 404
    assert json_object(response) == {"error": "not found"}


@pytest.mark.usefixtures("conn")
def test_put_then_get(client: FlaskClient) -> None:
    put = client.put("/data/trip-1")
    assert put.status_code == 200
    stored = json_object(put)
    assert stored["trip_id"] == "trip-1"
    assert stored["synced_at"] is not None

    get = client.get("/data/trip-1")
    assert get.status_code == 200
    assert json_object(get) == stored

    listed = json_list(client.get("/data"))
    assert listed == [stored]


@pytest.mark.usefixtures("conn")
def test_put_twice_replaces(client: FlaskClient) -> None:
    first = json_object(client.put("/data/trip-1"))
    second = json_object(client.put("/data/trip-1"))

    assert second["id"] == first["id"]
    assert parsedate_to_datetime(
        http_date(second["synced_at"])
    ) >= parsedate_to_datetime(http_date(first["synced_at"]))
    assert len(json_list(client.get("/data"))) == 1


@pytest.mark.usefixtures("conn")
def test_put_ignores_request_body(client: FlaskClient) -> None:
    """PUT always pulls the booking from upstream; a client can't overwrite fields."""
    response = client.put(
        "/data/trip-1", json={"trip_id": "trip-2", "status": "hacked"}
    )
    body = json_object(response)
    assert body["trip_id"] == "trip-1"
    assert body["status"] != "hacked"
