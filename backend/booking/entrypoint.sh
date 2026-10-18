#!/bin/sh
# Installs the booking sync cron job, starts cron, then runs the given command (gunicorn) as `app`.
set -eu

# Standard 5-field cron expression; override with the SYNC_CRON_SCHEDULE environment variable.
SYNC_CRON_SCHEDULE="${SYNC_CRON_SCHEDULE:-*/5 * * * *}"

# Cron jobs don't inherit the container environment, so pass the database settings through
# explicitly: DATABASE_URL, plus the libpq PG* variables (PGUSER, PGPASSWORD, ... on ECS).
# Output goes to PID 1's stdout/stderr so it shows up in `docker logs`.
{
    for var in DATABASE_URL $(env | sed -n 's/^\(PG[A-Z]*\)=.*/\1/p'); do
        value="$(printenv "$var" || true)"
        if [ -n "$value" ]; then
            echo "${var}=${value}"
        fi
    done
    echo "${SYNC_CRON_SCHEDULE} app cd /app && /usr/local/bin/python sync.py > /proc/1/fd/1 2> /proc/1/fd/2"
} > /etc/cron.d/booking-sync
chmod 0644 /etc/cron.d/booking-sync

cron

# setpriv keeps the root environment, so point HOME at app's home (gunicorn writes ~/.gunicorn).
exec env HOME=/home/app USER=app LOGNAME=app setpriv --reuid=app --regid=app --init-groups "$@"
