main: up

up:
	docker compose up --build

down:
	docker compose down

# Re-run the migration container against the running db (also runs automatically on `make up`).
migrate:
	docker compose run --rm --build migrate

# Shared docker network so the gateway can reach services by container name.
NETWORK := heatmap

venv:
	python -m venv ./venv

install-python-dependencies: venv
	. ./venv/bin/activate && \
	pip install --no-cache-dir -r ./backend/vehicle/requirements.txt && \
	pip install --no-cache-dir -r ./backend/booking/requirements.txt

arm-docker-postgis:
	cd docker-postgis && \
	make build VERSION=18-3.6 VARIANT=default
