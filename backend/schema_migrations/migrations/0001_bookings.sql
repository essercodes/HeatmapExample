CREATE TABLE IF NOT EXISTS bookings (
    id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    trip_id text NOT NULL UNIQUE,
    icabbi_id integer,
    perma_id text,
    pickup_lat real,
    pickup_lng real,
    booking_vehicletype text,
    bookingdate_ms timestamp,
    event text,
    status text,
    synced_at timestamp
);

CREATE INDEX IF NOT EXISTS idx_bookingdate_ms ON bookings (bookingdate_ms);
