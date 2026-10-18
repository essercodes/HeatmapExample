main: up

.PHONY: test

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

install-python-dependencies: venv
	. ./venv/bin/activate && \
	pip install --no-cache-dir -r ./backend/vehicle/requirements-dev.txt && \
	pip install --no-cache-dir -r ./backend/booking/requirements-dev.txt && \
	pip install --no-cache-dir -r ./backend/schema_migrations/requirements-dev.txt

# Regression tests. Integration tests need Postgres (`make up`) and create/drop their own
# heatmap_test_* databases; point TEST_ADMIN_DATABASE_URL elsewhere to use another server.
test: install-python-dependencies up
	cd backend/schema_migrations && ../../venv/bin/python -m pytest
	cd backend/booking && ../../venv/bin/python -m pytest

arm-docker-postgis:
	cd docker-postgis && \
	make build VERSION=18-3.6 VARIANT=default

