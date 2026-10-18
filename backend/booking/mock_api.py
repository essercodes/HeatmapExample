import os
import random
import string
import time
from datetime import datetime, timedelta

# Simulated network latency for each mock API call, in milliseconds.
MOCK_API_DELAY_MS = float(os.environ.get("MOCK_API_DELAY_MS", "100"))
MOCK_BOOKING_MAX_FORWARD_DAYS = int(os.environ.get("MOCK_BOOKING_MAX_FORWARD_DAYS", "0"))
MOCK_BOOKING_MAX_FORWARD_HOURS = int(os.environ.get("MOCK_BOOKING_MAX_FORWARD_HOURS", "12"))
MOCK_BOOKING_MAX_FORWARD_MINUTES = int(os.environ.get("MOCK_BOOKING_MAX_FORWARD_MINUTES", "60"))

# Pickups are scattered inside this box (min_lat, max_lat, min_lng, max_lng); roughly Madison, WI.
PICKUP_BOUNDS = (43.02, 43.13, -89.52, -89.28)

VEHICLE_TYPES = ("R", "ATS", "D", "S", "V")
EVENTS = ("created", "dispatched", "picked_up", "dropped_off", "cancelled")
STATUSES = ("new", "active", "completed", "cancelled", "no_show")

# Fixed pool of trip ids for fetch_active_bookings, so repeated calls keep hitting the same trips.
ACTIVE_TRIP_IDS = tuple(f"trip-{n:04d}" for n in range(1, 601))


def fetch_booking(trip_id: str) -> dict[str, object]:
    """Pretend to fetch a booking from the upstream API.

    Returns a body for `PUT /data/<trip_id>`; trip_id itself goes in the URL, not the body.
    """
    time.sleep(MOCK_API_DELAY_MS / 1000)
    return _mock_booking(trip_id)


def fetch_bookings(trip_ids: list[str]) -> list[dict[str, object]]:
    """Pretend to fetch many bookings from the upstream API in a single batch call.

    Pays the simulated latency once for the whole batch, not once per booking.
    """
    time.sleep(MOCK_API_DELAY_MS / 1000)
    return [_mock_booking(trip_id) for trip_id in trip_ids]


def fetch_active_bookings() -> list[dict[str, object]]:
    """Pretend to fetch every active booking from the upstream API.

    Returns 400-600 bookings drawn from ACTIVE_TRIP_IDS, all scheduled within the next week.
    Ignores the MOCK_* environment variables, including the simulated latency.
    """
    trip_ids = random.sample(ACTIVE_TRIP_IDS, k=random.randint(400, 600))
    now = datetime.now()
    return [
        _mock_booking(
            trip_id,
            booked_at=now + timedelta(seconds=random.randint(0, 7 * 24 * 60 * 60)),
            # Not picked up yet, since the pickup is still in the future.
            event=random.choice(("created", "dispatched")),
            status="active",
        )
        for trip_id in trip_ids
    ]


def _mock_booking(
    trip_id: str,
    booked_at: datetime | None = None,
    event: str | None = None,
    status: str | None = None,
) -> dict[str, object]:
    min_lat, max_lat, min_lng, max_lng = PICKUP_BOUNDS
    if booked_at is None:
        booked_at = datetime.now() + timedelta(
            minutes=random.randint(0, MOCK_BOOKING_MAX_FORWARD_MINUTES),
            hours=random.randint(0, MOCK_BOOKING_MAX_FORWARD_HOURS),
            days=random.randint(0, MOCK_BOOKING_MAX_FORWARD_DAYS),
        )

    return {
        "trip_id": trip_id,
        "icabbi_id": random.randint(100_000, 999_999),
        "perma_id": "".join(
            random.choices(string.ascii_uppercase + string.digits, k=8)
        ),
        "pickup_lat": round(random.uniform(min_lat, max_lat), 6),
        "pickup_lng": round(random.uniform(min_lng, max_lng), 6),
        "booking_vehicletype": random.choice(VEHICLE_TYPES),
        "bookingdate_ms": booked_at.isoformat(timespec="milliseconds"),
        "event": event or random.choice(EVENTS),
        "status": status or random.choice(STATUSES),
    }
