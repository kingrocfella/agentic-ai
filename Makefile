# Agentic AI — developer commands.
# `make up` builds and runs the API and Redis in Docker.
#
# NOTE: this app does NOT run its own Ollama daemon on the shared VPS. Lost
# Vowels runs the single daemon there and this API reaches it over the private
# `word-games-ollama` network, exactly as Letterbolt does. The local `ollama`
# service is behind an opt-in profile for development machines only:
#   docker compose --profile ollama up -d

.PHONY: up down restart logs ps rebuild sh check-env init-env ensure-ollama-network \
	ensure-app-network install-dev format format-check lint type-check test check clean help

COMPOSE = docker compose --env-file .env
LOG_TAIL ?= 200

help:
	@echo "Stack:   make up | down | restart | logs | ps | rebuild | sh"
	@echo "Env:     make check-env | init-env"
	@echo "Ollama:  make ensure-ollama-network   (shared Lost Vowels daemon)"
	@echo "Quality: make format | format-check | lint | type-check | test | check"
	@echo "         make install-dev | clean"

# ---------------------------------------------------------------------------
# Stack
# ---------------------------------------------------------------------------

## Create the private cross-project network the single shared Ollama daemon
## lives on. Idempotent; Lost Vowels and Letterbolt create the same network.
ensure-ollama-network:
	@docker network inspect word-games-ollama >/dev/null 2>&1 || \
		docker network create --driver bridge --internal word-games-ollama >/dev/null

## Create the private network the Next.js client (agentic-ai-client) uses to
## reach this API. Idempotent; that repo's Makefile creates the same network.
ensure-app-network:
	@docker network inspect agentic-ai >/dev/null 2>&1 || \
		docker network create --driver bridge --internal agentic-ai >/dev/null

## Start the API + Redis in the background (builds if needed).
up: ensure-ollama-network ensure-app-network
	chmod 600 .env
	$(MAKE) check-env
	$(COMPOSE) up -d --build

## Stop and remove the containers. Named volumes survive; `down -v` clears them.
down:
	$(COMPOSE) down

## Restart the API container.
restart:
	$(COMPOSE) restart app

## Follow API logs. Override history with LOG_TAIL=500 or LOG_TAIL=all.
logs:
	$(COMPOSE) logs --follow --tail=$(LOG_TAIL) app

## Show container status.
ps:
	$(COMPOSE) ps

## Rebuild the API image from scratch (no cache).
rebuild:
	$(COMPOSE) build --no-cache app

## Open a shell in the API container.
sh:
	$(COMPOSE) exec app sh

# ---------------------------------------------------------------------------
# Env
# ---------------------------------------------------------------------------

## .env is the only environment file allowed anywhere in this repo, it must
## be mode 0600, and it must carry exactly one entry for every key init-env
## emits — so a variable the code starts reading can never be silently absent.
check-env:
	@test -f .env || (echo "check-env: .env is missing; run 'make init-env'" >&2; exit 1)
	@extra=$$(find . -name '.env' -o -name '.env.*' 2>/dev/null \
		| grep -Ev '(^|/)(node_modules|\.git|\.venv|venv|\.next|\.claude)/' \
		| grep -v '^\./.env$$' || true); \
	if [ -n "$$extra" ]; then \
		echo "check-env: only .env is allowed; remove:" >&2; echo "$$extra" | sed 's/^/  /' >&2; exit 1; \
	fi
	@mode=$$(stat -c '%a' .env 2>/dev/null || stat -f '%Lp' .env); \
	if [ "$$mode" != "600" ]; then \
		echo "check-env: .env permissions are $$mode; expected 600" >&2; exit 1; \
	fi
	@bad=$$(grep -oE "^[[:space:]]+['\"][A-Z][A-Z0-9_]*=" Makefile | grep -oE "[A-Z][A-Z0-9_]*" | sort -u \
		| while read -r key; do \
			[ "$$(grep -c "^$$key=" .env)" -eq 1 ] || echo "  $$key"; \
		done); \
	if [ -n "$$bad" ]; then \
		echo "check-env: .env needs exactly one entry per init-env key; missing or duplicated:" >&2; \
		echo "$$bad" >&2; exit 1; \
	fi
	@echo "check-env: clean — .env is complete and mode 0600"

## Create the one canonical .env with safe local defaults (only if missing).
## REDIS_SECRET_KEY is generated; WEATHER_API_KEY must be filled in by hand —
## app/config.py refuses to start on a `change-me` placeholder, by design.
init-env:
	@if [ -f .env ]; then \
		echo "init-env: .env already exists; leaving it untouched"; \
	else \
		printf '%s\n' \
			'ENVIRONMENT=development' \
			"REDIS_SECRET_KEY=$$(openssl rand -hex 32)" \
			'REDIS_URL=redis://redis:6379/0' \
			'REDIS_HOST_PORT=6380' \
			'API_HOST_PORT=9000' \
			'ACCESS_TOKEN_EXPIRE_MINUTES=60' \
			'JWT_ISSUER=agentic-ai-api' \
			'JWT_AUDIENCE=agentic-ai-client' \
			'MAX_REQUEST_BODY_BYTES=65536' \
			'REQUEST_TIMEOUT_SECONDS=120' \
			'WEATHER_TIMEOUT_SECONDS=5' \
			'WEATHER_API_KEY=change-me' \
			'WEATHER_API_BASE_URL=https://api.weatherapi.com/v1' \
			'OLLAMA_HOST=http://ollama:11434' \
			'OLLAMA_MODEL=llama3.2:3b' \
			'OLLAMA_TIMEOUT_SECONDS=60' \
			'OLLAMA_KEEP_ALIVE=10m' \
			'OLLAMA_HOST_PORT=11436' \
			'REGISTER_RATE_LIMIT=5' \
			'REGISTER_RATE_WINDOW_SECONDS=3600' \
			'LOGIN_RATE_LIMIT=10' \
			'LOGIN_RATE_WINDOW_SECONDS=900' \
			'AGENT_RATE_LIMIT=60' \
			'AGENT_RATE_WINDOW_SECONDS=3600' \
			'AGENT_SLOT_TTL_SECONDS=180' \
			'LOG_LEVEL=INFO' \
			'LOG_DIR=/app/logs' > .env; \
		chmod 600 .env; \
		echo "init-env: wrote .env with safe local defaults"; \
		echo "init-env: set a real WEATHER_API_KEY before 'make up'"; \
	fi

# ---------------------------------------------------------------------------
# Quality / tests
# ---------------------------------------------------------------------------

install-dev:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

format:
	@echo "Running isort..."
	isort app/ tests/
	@echo "Running black..."
	black app/ tests/

format-check:
	@echo "Checking isort..."
	isort --check-only app/ tests/
	@echo "Checking black..."
	black --check app/ tests/

lint:
	@echo "Running flake8..."
	flake8 app/

type-check:
	@echo "Running mypy..."
	mypy app/

test:
	@echo "Running pytest..."
	pytest

check: format-check lint type-check test
	@echo "All checks passed!"

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ .coverage build/ dist/
