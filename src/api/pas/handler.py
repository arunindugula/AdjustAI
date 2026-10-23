"""
PAS Lambda — Policy Administration System
==========================================
Handles one route:
  GET /policies/{policy_id} → return a policy record from DynamoDB

Read-only. No write path exists in the PAS (ADR-004).

The coverage_type field drives the deterministic pre-checks:
  - "Liability Only" → deterministic deny before any agent runs (ADR-006)
  - "Full Coverage"  → proceed to agent pipeline

Environment variables
---------------------
  POLICIES_TABLE    DynamoDB table name for policies
  DYNAMODB_ENDPOINT empty on AWS; http://host.docker.internal:8001 locally
"""

import json
import os
from datetime import date
from decimal import Decimal

import boto3

# ---------------------------------------------------------------------------
# DynamoDB setup
# ---------------------------------------------------------------------------

def _get_table(name: str):
    kwargs = dict(region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))
    endpoint = os.environ.get("DYNAMODB_ENDPOINT", "")
    if endpoint:
        kwargs["endpoint_url"] = endpoint
        kwargs["aws_access_key_id"]     = os.environ.get("AWS_ACCESS_KEY_ID", "local")
        kwargs["aws_secret_access_key"] = os.environ.get("AWS_SECRET_ACCESS_KEY", "local")
    return boto3.resource("dynamodb", **kwargs).Table(name)


POLICIES_TABLE = os.environ.get("POLICIES_TABLE", "claimsense-policies-dev")


# ---------------------------------------------------------------------------
# Response helpers
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
# GET /policies/{policy_id}
#
# Returns the policy record and two computed fields the pipeline uses
# as deterministic inputs (ADR-005) so agents never compute them:
#
#   in_force  — whether the policy was active on the incident date
#               (passed as a query param so the check is date-aware)
#
#   liability_only — True when coverage_type == "Liability Only"
#                    Triggers deterministic deny before agents run (ADR-006)
# ---------------------------------------------------------------------------

def get_policy(policy_id: str, incident_date: str | None) -> dict:
    table = _get_table(POLICIES_TABLE)
    result = table.get_item(Key={"policy_id": policy_id})
    item = result.get("Item")

    if not item:
        return _error(404, f"Policy {policy_id} not found.")

    # Attach computed fields the pipeline uses as deterministic inputs.
    # These are computed here in Python — never by the model (ADR-005).
    item["liability_only"] = item.get("coverage_type") == "Liability Only"
    item["in_force"]       = _is_in_force(item, incident_date)

    return _response(200, item)


def _is_in_force(policy: dict, incident_date: str | None) -> bool:
    """
    Returns True if the policy was active on the incident date.

    Compares incident_date against policy_start and policy_end.
    If no incident_date is supplied, falls back to checking policy_status.
    This is deterministic Python arithmetic — not model judgment (ADR-005).
    """
    if policy.get("policy_status") != "Active":
        return False

    if not incident_date:
        return True  # no date to check against — assume in force

    try:
        incident  = date.fromisoformat(incident_date)
        start     = date.fromisoformat(policy["policy_start"])
        end       = date.fromisoformat(policy["policy_end"])
        return start <= incident <= end
    except (KeyError, ValueError):
        return False


# ---------------------------------------------------------------------------
# Lambda entry point
# ---------------------------------------------------------------------------

def lambda_handler(event: dict, context) -> dict:
    method  = event.get("httpMethod", "")
    params  = event.get("pathParameters") or {}
    qs      = event.get("queryStringParameters") or {}

    policy_id     = params.get("policy_id", "")
    incident_date = qs.get("incident_date")   # optional: ?incident_date=2024-02-14

    if not policy_id:
        return _error(400, "Missing policy_id in path.")

    if method == "GET":
        return get_policy(policy_id, incident_date)

    return _error(405, f"Method {method} not allowed.")
