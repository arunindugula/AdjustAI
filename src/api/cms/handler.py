"""
CMS Lambda — Claims Management System
======================================
Handles two routes:
  GET  /claims/{claim_id}           → return a claim record from DynamoDB
  POST /claims/{claim_id}/decision  → write a confirmed decision (idempotent)

The POST is the only write path in the entire system (ADR-004).
Idempotency is enforced via the Idempotency-Key header —
a duplicate POST returns the existing record rather than writing again.

Environment variables (injected by SAM / template.yaml)
--------------------------------------------------------
  CLAIMS_TABLE      DynamoDB table name for claims
  DECISIONS_TABLE   DynamoDB table name for decisions
  DYNAMODB_ENDPOINT empty on AWS; http://host.docker.internal:8001 locally
"""

import hashlib
import json
import os
from datetime import datetime, timezone
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key

# ---------------------------------------------------------------------------
# DynamoDB setup — same pattern as seed_dynamo.py
# ---------------------------------------------------------------------------

def _get_table(name: str):
    kwargs = dict(region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))
    endpoint = os.environ.get("DYNAMODB_ENDPOINT", "")
    if endpoint:
        kwargs["endpoint_url"] = endpoint
        kwargs["aws_access_key_id"]     = os.environ.get("AWS_ACCESS_KEY_ID", "local")
        kwargs["aws_secret_access_key"] = os.environ.get("AWS_SECRET_ACCESS_KEY", "local")
    return boto3.resource("dynamodb", **kwargs).Table(name)


CLAIMS_TABLE    = os.environ.get("CLAIMS_TABLE",    "claimsense-claims-dev")
DECISIONS_TABLE = os.environ.get("DECISIONS_TABLE", "claimsense-decisions-dev")


# ---------------------------------------------------------------------------
# Response helpers
#
# API Gateway expects a dict with statusCode, headers, and a JSON string body.
# DynamoDB returns Decimal for all numbers — json.dumps can't serialise those
# by default, so we convert them to float before responding.
# ---------------------------------------------------------------------------

class _DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


def _response(status: int, body: dict) -> dict:
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body, cls=_DecimalEncoder),
    }


def _error(status: int, message: str) -> dict:
    return _response(status, {"error": message})


# ---------------------------------------------------------------------------
# GET /claims/{claim_id}
#
# Reads the claim record from DynamoDB and returns it.
# The X-Adjuster-Id header is required — Cognito has already verified the
# JWT before this Lambda fires, so we trust the header value here.
# ---------------------------------------------------------------------------

def get_claim(claim_id: str, adjuster_id: str) -> dict:
    table = _get_table(CLAIMS_TABLE)
    result = table.get_item(Key={"claim_id": claim_id})
    item = result.get("Item")

    if not item:
        return _error(404, f"Claim {claim_id} not found.")

    # Attach any existing decision so the frontend can show it
    decision = _get_existing_decision(claim_id)
    if decision:
        item["decision"] = decision

    return _response(200, item)


def _get_existing_decision(claim_id: str) -> dict | None:
    """Return the most recent confirmed decision for this claim, if any."""
    table = _get_table(DECISIONS_TABLE)
    result = table.query(
        IndexName="claim_id-index",
        KeyConditionExpression=Key("claim_id").eq(claim_id),
        Limit=1,
        ScanIndexForward=False,
    )
    items = result.get("Items", [])
    return items[0] if items else None


# ---------------------------------------------------------------------------
# POST /claims/{claim_id}/decision
#
# Writes a confirmed decision record.
# Idempotency key = SHA-256(claim_id:adjuster_id:verdict)
#
# Returns:
#   201 Created    — new decision written
#   409 Conflict   — duplicate key; returns the original record (treat as success)
#   400 Bad Request — malformed payload or mismatched idempotency key
# ---------------------------------------------------------------------------

def post_decision(claim_id: str, body: dict, idempotency_key: str) -> dict:
    # Validate required fields
    required = ["adjuster_id", "verdict", "reasoning_summary",
                "reasoning_chain", "citations",
                "deterministic_checks_passed", "model_generated", "pipeline_run_id"]
    missing = [f for f in required if f not in body]
    if missing:
        return _error(400, f"Missing fields: {', '.join(missing)}")

    # Verify the idempotency key matches what we'd compute
    expected_key = hashlib.sha256(
        f"{claim_id}:{body['adjuster_id']}:{body['verdict']}".encode()
    ).hexdigest()

    if idempotency_key != expected_key:
        return _error(400, "Idempotency-Key does not match SHA-256(claim_id:adjuster_id:verdict).")

    table = _get_table(DECISIONS_TABLE)

    # Check for existing record with this key — return it without writing again
    existing = table.get_item(Key={"idempotency_key": idempotency_key}).get("Item")
    if existing:
        return _response(409, existing)

    # Build and write the decision record
    record = {
        "idempotency_key":             idempotency_key,
        "claim_id":                    claim_id,
        "adjuster_id":                 body["adjuster_id"],
        "verdict":                     body["verdict"],
        "reasoning_summary":           body["reasoning_summary"],
        "reasoning_chain":             body["reasoning_chain"],
        "citations":                   body["citations"],
        "deterministic_checks_passed": body["deterministic_checks_passed"],
        "model_generated":             body["model_generated"],
        "pipeline_run_id":             body["pipeline_run_id"],
        "confirmed_at":                datetime.now(timezone.utc).isoformat(),
    }

    table.put_item(Item=record)
    return _response(201, record)


# ---------------------------------------------------------------------------
# Lambda entry point
#
# API Gateway passes an event dict. We pull the HTTP method and path
# parameters from it, then dispatch to the right handler.
# ---------------------------------------------------------------------------

def lambda_handler(event: dict, context) -> dict:
    method     = event.get("httpMethod", "")
    params     = event.get("pathParameters") or {}
    headers    = event.get("headers") or {}
    claim_id   = params.get("claim_id", "")

    # Adjuster identity comes from the verified Cognito JWT header
    adjuster_id = headers.get("X-Adjuster-Id") or headers.get("x-adjuster-id", "")

    if not claim_id:
        return _error(400, "Missing claim_id in path.")

    if method == "GET":
        if not adjuster_id:
            return _error(400, "Missing X-Adjuster-Id header.")
        return get_claim(claim_id, adjuster_id)

    if method == "POST":
        idempotency_key = headers.get("Idempotency-Key") or headers.get("idempotency-key", "")
        if not idempotency_key:
            return _error(400, "Missing Idempotency-Key header.")

        try:
            body = json.loads(event.get("body") or "{}")
        except json.JSONDecodeError:
            return _error(400, "Request body is not valid JSON.")

        return post_decision(claim_id, body, idempotency_key)

    return _error(405, f"Method {method} not allowed.")
