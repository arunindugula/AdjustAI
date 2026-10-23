"""
seed_dynamo.py — Load CSV data into DynamoDB
=============================================
Reads the three source CSVs from ClaimsData/data/ and writes every row
into the corresponding DynamoDB table.

Safe to run multiple times — DynamoDB PutItem with the same partition key
simply overwrites the existing item, so there is no duplication.

Usage
-----
  # Local (DynamoDB Local must be running via docker compose up -d)
  python src/seed/seed_dynamo.py

  # Against a real AWS environment (uses AWS credentials from ~/.aws)
  ENV=staging python src/seed/seed_dynamo.py

Environment variables (set automatically by Makefile / env.local.json)
---------------------------------------------------------------------
  DYNAMODB_ENDPOINT   http://localhost:8001 for local; empty for real AWS
  CLAIMS_TABLE        table name for claims
  POLICIES_TABLE      table name for policies
  DOCUMENTS_TABLE     table name for documents
  AWS_DEFAULT_REGION  us-east-1
"""

import csv
import os
from decimal import Decimal
from pathlib import Path

import boto3

# ---------------------------------------------------------------------------
# Configuration — reads from environment, falls back to local defaults
# ---------------------------------------------------------------------------

ENDPOINT    = os.environ.get("DYNAMODB_ENDPOINT", "http://localhost:8001")
REGION      = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
CLAIMS_TABLE    = os.environ.get("CLAIMS_TABLE",    "claimsense-claims-dev")
POLICIES_TABLE  = os.environ.get("POLICIES_TABLE",  "claimsense-policies-dev")
DOCUMENTS_TABLE = os.environ.get("DOCUMENTS_TABLE", "claimsense-documents-dev")

# CSVs live in ClaimsData/data/ relative to the project root
DATA_DIR = Path(__file__).parent.parent.parent / "ClaimsData" / "data"


# ---------------------------------------------------------------------------
# DynamoDB client
#
# When ENDPOINT is set (local dev), boto3 points at DynamoDB Local.
# When ENDPOINT is empty (real AWS), boto3 uses the normal AWS endpoint.
# The Lambda code uses the same pattern — one code path for both.
# ---------------------------------------------------------------------------

def get_dynamo_resource():
    kwargs = dict(region_name=REGION)
    if ENDPOINT:
        kwargs["endpoint_url"] = ENDPOINT
        # DynamoDB Local requires non-empty credentials even though it
        # doesn't validate them. These values are intentionally fake.
        kwargs["aws_access_key_id"]     = os.environ.get("AWS_ACCESS_KEY_ID", "local")
        kwargs["aws_secret_access_key"] = os.environ.get("AWS_SECRET_ACCESS_KEY", "local")
    return boto3.resource("dynamodb", **kwargs)


# ---------------------------------------------------------------------------
# Type helpers
#
# DynamoDB via boto3 accepts Python native types:
#   str   → String (S)
#   bool  → Boolean (BOOL)
#   int   → Number (N)
#   Decimal → Number (N)   ← boto3 requires Decimal, not float
#
# We convert every numeric CSV value to Decimal and every Yes/No field
# to bool before writing. This keeps the data clean and avoids type
# mismatches when the Lambda reads it back.
# ---------------------------------------------------------------------------

def to_decimal(value: str) -> Decimal:
    """Convert a numeric string to Decimal. Returns Decimal('0') for N/A."""
    if not value or value.strip().upper() in ("N/A", ""):
        return Decimal("0")
    return Decimal(value.strip())

def to_bool(value: str) -> bool:
    return value.strip().lower() in ("yes", "true", "1")

def to_int(value: str) -> int:
    return int(value.strip()) if value.strip().lstrip("-").isdigit() else 0


# ---------------------------------------------------------------------------
# Seed functions — one per table
# ---------------------------------------------------------------------------

def seed_claims(table):
    """
    Writes 20 claim records to the claims table.

    Key fields converted:
      vehicle_year, prior_claims_12mo → int
      vehicle_acv_usd, repair_estimate_usd, fraud_risk_score → Decimal
      injuries_reported, police_report_filed → bool
    """
    path = DATA_DIR / "claimsense_claims.csv"
    count = 0
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            table.put_item(Item={
                "claim_id":              row["claim_id"],
                "policy_id":             row["policy_id"],
                "vehicle_vin":           row["vehicle_vin"],
                "vehicle_year":          to_int(row["vehicle_year"]),
                "vehicle_make":          row["vehicle_make"],
                "vehicle_model":         row["vehicle_model"],
                "vehicle_acv_usd":       to_decimal(row["vehicle_acv_usd"]),
                "incident_date":         row["incident_date"],
                "incident_type":         row["incident_type"],
                "incident_description":  row["incident_description"],
                "damage_description":    row["damage_description"],
                "repair_estimate_usd":   to_decimal(row["repair_estimate_usd"]),
                "injuries_reported":     to_bool(row["injuries_reported"]),
                "police_report_filed":   to_bool(row["police_report_filed"]),
                "assigned_adjuster":     row["assigned_adjuster"],
                "prior_claims_12mo":     to_int(row["prior_claims_12mo"]),
                "fraud_risk_score":      to_decimal(row["fraud_risk_score"]),
                "claim_status":          row["claim_status"],
                "created_at":            row["created_at"],
            })
            count += 1
    return count


def seed_policies(table):
    """
    Writes 15 policy records to the policies table.

    Liability Only policies have no collision/comprehensive deductibles —
    those fields are stored as Decimal('0') rather than None so the
    Lambda never has to handle a missing attribute.
    """
    path = DATA_DIR / "claimsense_policies.csv"
    count = 0
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            liability_only = row["coverage_type"] == "Liability Only"
            table.put_item(Item={
                "policy_id":                    row["policy_id"],
                "holder_first":                 row["holder_first"],
                "holder_last":                  row["holder_last"],
                "vehicle_vin":                  row["vehicle_vin"],
                "vehicle_year":                 to_int(row["vehicle_year"]),
                "vehicle_make":                 row["vehicle_make"],
                "vehicle_model":                row["vehicle_model"],
                "vehicle_acv_usd":              to_decimal(row["vehicle_acv_usd"]),
                "coverage_type":                row["coverage_type"],
                "collision_coverage":           to_bool(row["collision_coverage"]),
                "comprehensive_coverage":       to_bool(row["comprehensive_coverage"]),
                "collision_deductible_usd":     Decimal("0") if liability_only else to_decimal(row["collision_deductible_usd"]),
                "comprehensive_deductible_usd": Decimal("0") if liability_only else to_decimal(row["comprehensive_deductible_usd"]),
                "liability_limit":              row["liability_limit"],
                "medpay_limit_usd":             to_decimal(row["medpay_limit_usd"]),
                "policy_status":                row["policy_status"],
                "policy_start":                 row["policy_start"],
                "policy_end":                   row["policy_end"],
            })
            count += 1
    return count


def seed_documents(table):
    """
    Writes 74 document records to the documents table.

    The table has a composite key: claim_id (partition) + document_id (sort).
    This lets the Lambda fetch all documents for a claim in one query,
    or a single document by both keys.

    content_text is empty for now — filled in Step 4 (PDF extraction).
    """
    path = DATA_DIR / "claimsense_documents.csv"
    count = 0
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            table.put_item(Item={
                "claim_id":      row["claim_id"],
                "document_id":   row["document_id"],
                "document_type": row["document_type"],
                "description":   row["description"],
                "upload_date":   row["upload_date"],
                "page_count":    to_int(row["page_count"]),
                "ocr_status":    row["ocr_status"],
                "uploaded_by":   row["uploaded_by"],
                "content_text":  "",   # populated in Step 4 (PDF extraction)
            })
            count += 1
    return count


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print(f"Connecting to DynamoDB at {ENDPOINT or 'AWS'} ...")
    dynamo = get_dynamo_resource()

    print(f"\nSeeding {CLAIMS_TABLE} ...")
    n = seed_claims(dynamo.Table(CLAIMS_TABLE))
    print(f"  {n} claims written.")

    print(f"\nSeeding {POLICIES_TABLE} ...")
    n = seed_policies(dynamo.Table(POLICIES_TABLE))
    print(f"  {n} policies written.")

    print(f"\nSeeding {DOCUMENTS_TABLE} ...")
    n = seed_documents(dynamo.Table(DOCUMENTS_TABLE))
    print(f"  {n} document records written.")

    print("\nDone. Run `make dev` to start the API.")


if __name__ == "__main__":
    main()
