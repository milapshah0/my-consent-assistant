SHELL := /bin/bash

.PHONY: start start-be start-fe migrate

start-be:
	cd backend && poetry run uvicorn app.main:app --reload --port 8000

start-fe:
	cd frontend && ([ -d node_modules ] || npm install) && npm run dev

migrate:
	cd backend && poetry run alembic upgrade head

start:
	trap 'kill 0' INT TERM EXIT; \
	($(MAKE) start-be) & \
	($(MAKE) start-fe) & \
	wait
