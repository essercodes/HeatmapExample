main: up

.PHONY: test test-booking test-vehicle test-frontend migrate migrate-booking up-db up-backend venv install-python-dependencies

up:
	docker compose --profile '*' up --build -d

# Everything except the frontend, for running it locally with `pnpm dev --host --port 8080`.
up-backend:
	docker compose --profile backend up --build -d

up-dev-frontend:
	@echo "will not run pnpm as nonAdmin user; run command manually."
	cd containers/frontend && pnpm run dev --host --port 8080

# Just the database, for integration tests (starts it if needed, waits until healthy).
up-db:
	docker compose up -d --wait db

follow:
	docker compose --profile '*' logs -f

down:
	docker compose --profile '*' down --volumes

migrate: migrate-booking

migrate-booking:
	docker compose run --rm --build booking-migrate

# Shared docker network so the gateway can reach services by container name.
NETWORK := heatmap

venv:
	python -m venv ./venv

install-python-dependencies: install-booking install-vehicle

install-%: venv
	@echo "will not run pip as nonAdmin user; run command manually."
	. ./venv/bin/activate && pip install --no-cache-dir -r ./containers/$(subst -,_,$*)/requirements-dev.txt

test: test-booking test-frontend # test-vehicle

test-booking: install-booking up-db
	cd containers/booking && ../../venv/bin/python -m pytest

# vehicle has no tests yet
# test-vehicle: install-vehicle up-db
# 	cd containers/vehicle && ../../venv/bin/python -m pytest

test-frontend:
	@echo "will not run pnpm as nonAdmin user; run command manually."
	cd containers/frontend && pnpm install --frozen-lockfile && pnpm run typecheck

arm-docker-postgis:
	cd docker-postgis && \
	make build VERSION=18-3.6 VARIANT=default

