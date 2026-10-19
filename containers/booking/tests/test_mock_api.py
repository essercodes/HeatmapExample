"""The mock upstream API's output contract: every booking the service stores comes from here."""

from datetime import datetime, timedelta

import pytest

import mock_api

BOOKING_KEYS = {
    "trip_id",
    "icabbi_id",
    "perma_id",
    "pickup_lat",
    "pickup_lng",
    "booking_vehicletype",
    "bookingdate_ms",
    "event",
    "status",
}


def iso_datetime(value: object) -> datetime:
    assert isinstance(value, str)
    return datetime.fromisoformat(value)


def assert_valid_booking(booking: dict[str, object]) -> None:
    min_lat, max_lat, min_lng, max_lng = mock_api.PICKUP_BOUNDS
    assert set(booking) == BOOKING_KEYS
    icabbi_id, perma_id = booking["icabbi_id"], booking["perma_id"]
    pickup_lat, pickup_lng = booking["pickup_lat"], booking["pickup_lng"]
    assert isinstance(icabbi_id, int) and isinstance(perma_id, str)
    assert isinstance(pickup_lat, float) and isinstance(pickup_lng, float)
    assert 100_000 <= icabbi_id <= 999_999
    assert len(perma_id) == 8 and perma_id.isalnum()
    assert min_lat <= pickup_lat <= max_lat
    assert min_lng <= pickup_lng <= max_lng
    assert booking["booking_vehicletype"] in mock_api.VEHICLE_TYPES
    assert booking["event"] in mock_api.EVENTS
    assert booking["status"] in mock_api.STATUSES
    _ = iso_datetime(booking["bookingdate_ms"])


@pytest.mark.parametrize("_", range(20))
def test_fetch_booking_is_valid(_: int) -> None:
    booking = mock_api.fetch_booking("trip-x")
    assert booking["trip_id"] == "trip-x"
    assert_valid_booking(booking)


def test_fetch_booking_is_scheduled_within_forward_window() -> None:
    before = datetime.now()
    booking = mock_api.fetch_booking("trip-x")
    window = timedelta(
        days=mock_api.MOCK_BOOKING_MAX_FORWARD_DAYS,
        hours=mock_api.MOCK_BOOKING_MAX_FORWARD_HOURS,
        minutes=mock_api.MOCK_BOOKING_MAX_FORWARD_MINUTES,
    )
    # isoformat truncates to milliseconds, so allow for that on the lower bound.
    booked_at = iso_datetime(booking["bookingdate_ms"])
    assert before - timedelta(milliseconds=1) <= booked_at <= datetime.now() + window


def test_fetch_bookings_preserves_order() -> None:
    trip_ids = ["trip-a", "trip-b", "trip-c"]
    bookings = mock_api.fetch_bookings(trip_ids)
    assert [b["trip_id"] for b in bookings] == trip_ids
    for booking in bookings:
        assert_valid_booking(booking)


def test_fetch_active_bookings() -> None:
    before = datetime.now()
    bookings = mock_api.fetch_active_bookings()

    assert 400 <= len(bookings) <= 600
    trip_ids = [b["trip_id"] for b in bookings]
    assert len(set(trip_ids)) == len(trip_ids), "trip ids must be unique within a sync"
    assert set(trip_ids) <= set(mock_api.ACTIVE_TRIP_IDS)

    for booking in bookings:
        assert_valid_booking(booking)
        assert booking["status"] == "active"
        assert booking["event"] in ("created", "dispatched")
        booked_at = iso_datetime(booking["bookingdate_ms"])
        assert before - timedelta(milliseconds=1) <= booked_at <= datetime.now() + timedelta(days=7)
