COMPOSE := docker compose -f infrastructure/compose/docker-compose.yml --env-file .env
API := $(COMPOSE) exec -T api
WEB := $(COMPOSE) exec -T web

.DEFAULT_GOAL := help
.PHONY: help up down restart build logs ps shell migrate sync-rbac sync-rbac-purge revision downgrade seed seed-demo seed-commission-demo seed-leadership-demo seed-settlement-demo import-dry-run import-dry-run-mysql test test-unit test-integration lint format typecheck web-test web-build openapi clean

help: ## lista os alvos disponíveis
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

## ---------- ambiente ----------

up: ## sobe o ambiente completo
	$(COMPOSE) up -d
	@echo "api  -> http://localhost:8000/docs"
	@echo "web  -> http://localhost:5173"
	@echo "minio-> http://localhost:9001"

down: ## derruba os containers (preserva os volumes)
	$(COMPOSE) down

restart: ## reinicia api, worker e scheduler
	$(COMPOSE) restart api worker scheduler

build: ## reconstrói as imagens
	$(COMPOSE) build

logs: ## acompanha os logs (make logs s=api)
	$(COMPOSE) logs -f $(or $(s),)

ps: ## estado dos containers
	$(COMPOSE) ps

shell: ## shell no container da api
	$(COMPOSE) exec api bash

## ---------- banco ----------

migrate: ## aplica as migrações e sincroniza o RBAC com o catálogo
	$(API) alembic upgrade head
	$(API) python -m app.platform.db.sync_rbac

sync-rbac: ## reaplica só o catálogo de permissões e papéis
	$(API) python -m app.platform.db.sync_rbac

sync-rbac-purge: ## idem, removendo papéis que sumiram do catálogo (nunca os que têm conta)
	$(API) python -m app.platform.db.sync_rbac --purgar

revision: ## cria migração (make revision m="descricao")
	$(API) alembic revision --autogenerate -m "$(m)"

downgrade: ## desfaz a última migração
	$(API) alembic downgrade -1

seed: ## cria permissões, papéis e as contas mínimas de operação
	$(API) python -m app.platform.db.seed

seed-demo: ## massa de teste: uma pessoa por perfil e função (idempotente)
	$(API) python -m app.platform.db.seed_demo

seed-commission-demo: ## propostas e recebimentos para homologar comissões (idempotente)
	$(API) python -m app.platform.db.seed_commission_demo

seed-leadership-demo: ## equipes e comissões de liderança para homologação
	$(API) python -m app.platform.db.seed_leadership_demo

seed-settlement-demo: ## ajustes, carryover e pagamentos para homologar fechamentos
	$(API) python -m app.platform.db.seed_settlement_demo

## ---------- migração do legado ----------

import-dry-run: ## importador legado em dry-run (make import-dry-run d=/dados/legado)
	$(API) python -m app.modules.legacy.entrypoints.import_legacy --csv $(or $(d),/dados/legado)

import-dry-run-mysql: ## idem, lendo LEGACY_DATABASE_URL (usuário somente-leitura)
	$(API) python -m app.modules.legacy.entrypoints.import_legacy --mysql

## ---------- qualidade ----------

test: test-unit web-test ## testes que não exigem infraestrutura

test-unit: ## testes unitários do backend
	$(API) pytest tests/unit

test-integration: ## testes de integração (MySQL e Redis reais)
	$(API) pytest tests/integration -m integration

lint: ## ruff
	$(API) ruff check app worker tests

format: ## ruff format
	$(API) ruff format app worker tests

typecheck: ## mypy
	$(API) mypy app

web-test: ## vitest
	$(WEB) npm run test

web-build: ## typecheck + build do frontend
	$(WEB) npm run build

openapi: ## exporta o contrato OpenAPI
	$(API) python -c "import json;from app.main import criar_app;print(json.dumps(criar_app().openapi(),indent=2))" > openapi.json

clean: ## derruba tudo e apaga os volumes (PERDE OS DADOS LOCAIS)
	$(COMPOSE) down -v
