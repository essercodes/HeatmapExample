main: up

.PHONY: test test-schema-migrations test-booking test-vehicle db venv install-python-dependencies

up:
	docker compose up --build -d

follow:
	docker compose logs -f

down:
	docker compose down --volumes

# Re-run the migration container against the running db (also runs automatically on `make up`).
migrate:
	docker compose run --rm --build migrate

# Shared docker network so the gateway can reach services by container name.
NETWORK := heatmap

venv:
	python -m venv ./venv

install-python-dependencies: install-booking install-vehicle install-schema-migrations

install-%: venv
	. ./venv/bin/activate && pip install --no-cache-dir -r ./backend/$(subst -,_,$*)/requirements-dev.txt

# Just the database, for integration tests (starts it if needed, waits until healthy).
db:
	docker compose up -d --wait db

# Regression tests, one target per container so CI can run them as parallel jobs.
# Integration tests need Postgres (started by `db`) and create/drop their own heatmap_test_*
# databases; point TEST_ADMIN_DATABASE_URL elsewhere to use another server.
test: test-schema-migrations test-booking test-vehicle

test-schema-migrations: install-schema-migrations db
	cd backend/schema_migrations && ../../venv/bin/python -m pytest

test-booking: install-booking db
	cd backend/booking && ../../venv/bin/python -m pytest

# vehicle has no tests yet; check that its image builds.
test-vehicle:
	docker compose build vehicle

arm-docker-postgis:
	cd docker-postgis && \
	make build VERSION=18-3.6 VARIANT=default

