# ClaimSense AI — Developer Commands
#
# Every command accepts an ENV variable (default: dev).
#
#   make dev                   → local dev stack
#   make seed                  → seed local DynamoDB
#   make eval                  → run eval suite locally
#   make deploy ENV=staging    → deploy to AWS staging
#   make deploy ENV=prod       → deploy to AWS prod (prompts for confirmation)
#   make logs ENV=staging      → tail Lambda logs from staging
#   make destroy ENV=dev       → tear down a CloudFormation stack

.PHONY: dev seed eval tables deploy logs destroy frontend stop clean ingest mcp

# Default environment — override with ENV=staging or ENV=prod
ENV ?= dev

# ---------------------------------------------------------------------------
# LOCAL DEVELOPMENT
# ---------------------------------------------------------------------------

# Start the full local stack:
#   1. docker compose up -d   → DynamoDB Local + table creation
#   2. sleep 5                → waits for init container to finish
#   3. make seed              → loads CSV data into tables
#   4. sam local start-api    → Lambda + API Gateway on :3000
dev:
	@echo "==> Starting DynamoDB Local..."
	docker compose up -d
	@echo "==> Seeding data..."
	$(MAKE) seed
	@echo "==> Starting SAM local API on http://localhost:3000"
	sam local start-api \
		--env-vars env.local.json \
		--port 3000 \
		--warm-containers EAGER

# Reload CSV data into DynamoDB Local at any time.
# Also used after `docker compose down` wipes the in-memory tables.
seed:
	.venv/bin/python src/seed/seed_dynamo.py

# Run the 21-case evaluation suite.
# Exits non-zero if accuracy < 92% — this is the CI gate signal.
#
#   make eval                         → full suite (requires OPENAI_API_KEY)
#   make eval ARGS=--deterministic-only → only pre-check cases, no OpenAI calls
#   make eval ARGS=EVAL-001           → single case by case_id
eval:
	.venv/bin/python src/eval/run_eval.py $(ARGS)

# (Re)create DynamoDB Local tables without restarting everything.
tables:
	docker compose up dynamodb-init

# Start the React dev server (run in a separate terminal alongside `make dev`).
frontend:
	cd frontend && npm run dev

# Start the MCP server locally (stdio transport — for Claude Code integration).
# Run this after `make dev` so the API is up on :3000.
#
#   make mcp                         → stdio (Claude Code)
#   MCP_TRANSPORT=streamable-http make mcp  → HTTP on :8080
mcp:
	API_BASE_URL=http://localhost:3000 .venv/bin/python mcp-server/server.py

# Upload policy manual to S3 and trigger Bedrock ingestion.
# Run once after `sam deploy`, and again whenever the policy manual changes.
# Get KNOWLEDGE_BASE_ID and DOCS_BUCKET from `sam deploy` outputs.
#
#   make ingest ENV=dev KNOWLEDGE_BASE_ID=<id> DOCS_BUCKET=<bucket>
ingest:
	@echo "==> Uploading policy manual and triggering Bedrock ingestion ($(ENV))..."
	KNOWLEDGE_BASE_ID=$(KNOWLEDGE_BASE_ID) \
	DOCS_BUCKET=$(DOCS_BUCKET) \
	STAGE=$(ENV) \
	.venv/bin/python src/retrieval/ingest.py

# Stop running containers without removing them.
stop:
	docker compose stop

# Stop and remove all containers (data is wiped — run `make seed` after restart).
clean:
	docker compose down

# ---------------------------------------------------------------------------
# AWS DEPLOYMENTS
# ---------------------------------------------------------------------------

# Deploy to any environment.
# Uses the matching section in samconfig.toml.
#
#   make deploy            → deploys to dev
#   make deploy ENV=staging
#   make deploy ENV=prod
#
# First-time deploy for an environment needs an S3 bucket for SAM artifacts:
#   sam deploy --guided --config-env $(ENV)
deploy:
	@echo "==> Deploying to $(ENV)..."
	sam build
	sam deploy --config-env $(ENV)

# Tail Lambda logs from a deployed environment.
# Streams live CloudWatch logs for all three functions.
#
#   make logs ENV=staging
logs:
	@echo "==> Streaming logs from $(ENV)..."
	sam logs \
		--stack-name claimsense-$(ENV) \
		--tail \
		--region us-east-1

# Tear down a CloudFormation stack and all its resources.
# Prompts for confirmation — use with care in staging/prod.
#
#   make destroy ENV=dev
destroy:
	@echo "==> WARNING: This will delete all resources in claimsense-$(ENV)"
	@read -p "Type the environment name to confirm: " confirm; \
	[ "$$confirm" = "$(ENV)" ] || (echo "Aborted." && exit 1)
	aws cloudformation delete-stack \
		--stack-name claimsense-$(ENV) \
		--region us-east-1
