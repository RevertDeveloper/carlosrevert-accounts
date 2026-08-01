COMPOSE := docker compose -f compose.yaml

.PHONY: up down update status db-up db-down db-status

up:
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

update: db-up
	$(COMPOSE) up -d --build --no-deps web

status:
	$(COMPOSE) ps

db-up:
	$(COMPOSE) up -d postgres

db-down:
	$(COMPOSE) stop postgres

db-status:
	$(COMPOSE) ps postgres
