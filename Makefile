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

.PHONY: dev seed eval tables deploy logs destroy frontend stop clean

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
	@echo "==> Waiting for tables..."
	sleep 5
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
	python src/seed/seed_dynamo.py

# Run the 21-case evaluation suite.
# Exits non-zero if accuracy < 92% — this is the CI gate signal.
eval:
	python src/eval/run_eval.py

# (Re)create DynamoDB Local tables without restarting everything.
tables:
	docker compose up dynamodb-init

# Start the React dev server (run in a separate terminal alongside `make dev`).
frontend:
	cd frontend && npm run dev

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
