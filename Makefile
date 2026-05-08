.PHONY: dev up down logs api-test frontend-check seed doctor

dev:
	cp -n .env.example .env || true
	docker compose up --build

up:
	cp -n .env.example .env || true
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f api frontend postgres neo4j redis

api-test:
	cd apps/api && python -m pytest -q

frontend-check:
	pnpm check

doctor:
	@echo "API:      http://localhost:8000/health"
	@echo "Frontend: http://localhost:3000"
	@echo "Neo4j:    http://localhost:7474"
	@echo "Ollama esperado en host: http://localhost:11434"
