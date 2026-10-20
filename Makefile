main: up

.PHONY: test test-booking test-vehicle test-frontend migrate migrate-booking db venv install-python-dependencies

up:
	docker compose up --build -d

follow:
	docker compose logs -f

down:
	docker compose down --volumes

migrate: migrate-booking

migrate-booking:
	docker compose run --rm --build booking-migrate

# Shared docker network so the gateway can reach services by container name.
NETWORK := heatmap

venv:
	python -m venv ./venv

install-python-dependencies: install-booking install-vehicle

install-%: venv
	. ./venv/bin/activate && pip install --no-cache-dir -r ./containers/$(subst -,_,$*)/requirements-dev.txt

# Just the database, for integration tests (starts it if needed, waits until healthy).
db:
	docker compose up -d --wait db

test: test-booking test-frontend # test-vehicle

test-booking: install-booking db
	cd containers/booking && ../../venv/bin/python -m pytest

test-frontend:
	cd containers/frontend && pnpm install --frozen-lockfile && pnpm run typecheck

# vehicle has no tests yet
# test-vehicle: install-vehicle db
# 	cd containers/vehicle && ../../venv/bin/python -m pytest

arm-docker-postgis:
	cd docker-postgis && \
	make build VERSION=18-3.6 VARIANT=default

