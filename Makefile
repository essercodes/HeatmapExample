main:
	@echo "no default"

# Shared docker network so the gateway can reach services by container name.
NETWORK := understory

.PHONY: network up down

network:
	docker network inspect $(NETWORK) >/dev/null 2>&1 || docker network create $(NETWORK)

up: db-up booking-up vehicle-up gateway-up

down: gateway-down vehicle-down booking-down db-down

DB_IMAGE := understory-db
DB_CONTAINER := understory-db
DB_PASSWORD ?= understory
DATABASE_URL := postgresql://understory:$(DB_PASSWORD)@$(DB_CONTAINER):5432/understory

.PHONY: db-build db-up db-down db-psql

db-build:
	docker build -t $(DB_IMAGE) backend/database

db-up: db-build network
	docker run -d --name $(DB_CONTAINER) --network $(NETWORK) \
		-e POSTGRES_PASSWORD=$(DB_PASSWORD) \
		-p 5432:5432 \
		-v understory-db-data:/var/lib/postgresql/data \
		$(DB_IMAGE)

db-down:
	-docker rm -f $(DB_CONTAINER)

db-psql:
	PGPASSWORD=$(DB_PASSWORD) psql -h localhost -U understory -d understory

BOOKING_IMAGE := understory-booking
BOOKING_CONTAINER := understory-booking

.PHONY: booking-build booking-up booking-down

booking-build:
	docker build -t $(BOOKING_IMAGE) backend/booking

booking-up: booking-build network
	docker run -d --name $(BOOKING_CONTAINER) --network $(NETWORK) \
		-e DATABASE_URL=$(DATABASE_URL) \
		-p 8000:8000 $(BOOKING_IMAGE)

booking-down:
	-docker rm -f $(BOOKING_CONTAINER)

VEHICLE_IMAGE := understory-vehicle
VEHICLE_CONTAINER := understory-vehicle

.PHONY: vehicle-build vehicle-up vehicle-down

vehicle-build:
	docker build -t $(VEHICLE_IMAGE) backend/vehicle

vehicle-up: vehicle-build network
	docker run -d --name $(VEHICLE_CONTAINER) --network $(NETWORK) \
		-e DATABASE_URL=$(DATABASE_URL) \
		-p 8001:8000 $(VEHICLE_IMAGE)

vehicle-down:
	-docker rm -f $(VEHICLE_CONTAINER)

GATEWAY_IMAGE := understory-gateway
GATEWAY_CONTAINER := understory-gateway
GATEWAY_PORT ?= 8081

.PHONY: gateway-build gateway-up gateway-down

gateway-build:
	docker build -t $(GATEWAY_IMAGE) backend/api_gateway

gateway-up: gateway-build network
	docker run -d --name $(GATEWAY_CONTAINER) --network $(NETWORK) -p $(GATEWAY_PORT):80 $(GATEWAY_IMAGE)

gateway-down:
	-docker rm -f $(GATEWAY_CONTAINER)
