# GPU SLA Escrow — common commands. Run `make` or `make help` for the list.
# Keys are read from .env only by the targets that need them (smoke, deploy, oracle).

SHELL   := /bin/bash
PY      := .venv/bin/python
PIP     := .venv/bin/pip
COMPOSE := docker compose -f docker/docker-compose.yml
ENV     := set -a; . ./.env; set +a;

.DEFAULT_GOAL := help
.PHONY: help venv install test test-contract test-oracle test-scripts abi \
        smoke deploy config nodes-up nodes-down nodes-ps \
        stop-a start-a stop-b start-b oracle ui ui-install ui-build ui-test demo-setup clean

help: ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

# ---------- setup ----------
venv: ## Create the Python virtualenv
	test -d .venv || python3 -m venv .venv

install: venv ## Install Python dependencies
	$(PIP) install -r requirements.txt

config: ## Create oracle/config.toml from the example (does not overwrite)
	@test -f oracle/config.toml && echo "oracle/config.toml already exists" || \
	  (cp oracle/config.example.toml oracle/config.toml && echo "created oracle/config.toml — fill in providers, node URLs and renter allow-list")

# ---------- tests (no keys, no network) ----------
test: test-contract test-oracle test-scripts ## Run all Python tests

test-contract: ## Contract tests
	$(PY) -m pytest -q -p no:warnings tests/

test-oracle: ## Oracle service tests
	$(PY) -m pytest -q -p no:warnings oracle/tests/

test-scripts: ## Deploy/demo script tests
	$(PY) -m pytest -q -p no:warnings scripts/

abi: ## Print the ABI diff vs shared/abi (should be empty)
	@.venv/bin/vyper -f abi contracts/GpuSlaEscrow.vy | $(PY) -c "import json,sys; a=json.load(sys.stdin); b=json.load(open('shared/abi/GpuSlaEscrow.json')); print('ABI identical' if a==b else 'ABI DIFFERS — run interface-sync')"

# ---------- testnet (needs .env) ----------
smoke: ## Day-0 check on Monad Testnet (Hello.vy deploy + block timing)
	$(ENV) $(PY) scripts/smoke_test.py

deploy: ## Deploy GpuSlaEscrow to Monad Testnet (writes shared/deployments/monad-testnet.json)
	$(ENV) $(PY) scripts/deploy.py

# ---------- demo nodes (Docker) ----------
nodes-up: ## Build and start node-a and node-b
	$(COMPOSE) up -d --build
	$(COMPOSE) ps

nodes-down: ## Stop and remove the demo nodes
	$(COMPOSE) down

nodes-ps: ## Show node status
	$(COMPOSE) ps

stop-a: ## Take node-a down (its slots become Down)
	$(COMPOSE) stop node-a

start-a: ## Bring node-a back
	$(COMPOSE) start node-a

stop-b: ## Take node-b down (the non-compliant demo run)
	$(COMPOSE) stop node-b

start-b: ## Bring node-b back
	$(COMPOSE) start node-b

# ---------- oracle ----------
oracle: ## Run the oracle service against the deployed contract (needs .env + oracle/config.toml)
	@test -f oracle/config.toml || (echo "missing oracle/config.toml — run: make config" && exit 1)
	$(ENV) $(PY) -m oracle

# ---------- frontend ----------
ui-install: ## Install frontend dependencies
	cd frontend && npm install

ui: ## Run the frontend dev server
	cd frontend && npm run dev

ui-build: ## Typecheck and production build
	cd frontend && npm run typecheck && npm run build

ui-test: ## Frontend tests
	cd frontend && npm test

# ---------- demo ----------
demo-setup: nodes-up ## Start nodes, then print the next steps
	@echo ""
	@echo "Nodes are up. Next, in separate terminals:"
	@echo "  make oracle     # watch probes and reports"
	@echo "  make ui         # open the app, create the rentals"
	@echo "During the run:  make stop-b   (keep it down for at least 2 slots)"

clean: ## Remove Python caches
	find . -path ./.venv -prune -o -name __pycache__ -type d -print -exec rm -rf {} +
	rm -rf .pytest_cache
