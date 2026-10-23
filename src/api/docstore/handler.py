"""
DocStore Lambda — Document Store
=================================
Handles two routes:
  GET  /documents/{claim_id}  → list all documents for a claim from DynamoDB
  POST /search                → query Bedrock Knowledge Base for policy clauses

The /search endpoint is what the Coverage Check agent calls.
Every result includes a clause_id so the agent can cite it in its verdict —
the agent must never state coverage from memory without a retrieved clause.

Environment variables
---------------------
  DOCUMENTS_TABLE     DynamoDB table name for documents
  KNOWLEDGE_BASE_ID   Bedrock Knowledge Base ID
  DYNAMODB_ENDPOINT   empty on AWS; http://host.docker.internal:8001 locally
  AWS_DEFAULT_REGION  us-east-1
"""

import json
import os
from decimal import Decimal

import boto3

from retrieval.bedrock_retrieval import retrieve

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


DOCUMENTS_TABLE = os.environ.get("DOCUMENTS_TABLE", "claimsense-documents-dev")


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
# GET /documents/{claim_id}
#
# Returns all document records for a claim.
#
# The documents table has a composite key: claim_id (partition) +
# document_id (sort). A DynamoDB Query on the partition key returns
# all documents for the claim in one call — no scan needed.
#
# Each document includes:
#   ocr_status    — "Completed" or "Pending"
#   content_text  — extracted PDF text (populated in Step 4)
#
# The Document Intake agent checks ocr_status — documents still
# "Pending" are flagged rather than processed (CLS-DOC-009).
# ---------------------------------------------------------------------------

def get_documents(claim_id: str) -> dict:
    table = _get_table(DOCUMENTS_TABLE)

    result = table.query(
        KeyConditionExpression=boto3.dynamodb.conditions.Key("claim_id").eq(claim_id)
    )
    items = result.get("Items", [])

    if not items:
        return _error(404, f"No documents found for claim {claim_id}.")

    # Summarise OCR status so the agent can see at a glance
    # how many documents are ready vs still pending
    pending  = [d["document_id"] for d in items if d.get("ocr_status") == "Pending"]
    complete = [d["document_id"] for d in items if d.get("ocr_status") == "Completed"]

    return _response(200, {
        "claim_id":          claim_id,
        "total_documents":   len(items),
        "ocr_complete":      len(complete),
        "ocr_pending":       len(pending),
        "pending_doc_ids":   pending,
        "documents":         items,
    })


# ---------------------------------------------------------------------------
# POST /search
#
# Queries the Bedrock Knowledge Base with a natural language question
# and returns the most relevant policy clause chunks.
#
# Request body:
#   query_text  string   the coverage question (required)
#   top_k       int      number of results to return (default 5, max 10)
#
# Response:
#   query_text        echoed back
#   retrieval_method  "bedrock-hybrid" — logged for audit
#   results[]
#     clause_id       e.g. "CLS-COLL-001" — what the agent cites
#     clause_text     the retrieved passage from the policy manual
#     source_uri      S3 location of the source PDF
#     score           relevance score 0.0–1.0
#
# The Coverage Check agent must include clause_id in every coverage
# statement. A verdict without a cited clause ID fails validation.
# ---------------------------------------------------------------------------

def search_policy_corpus(body: dict) -> dict:
    query_text = body.get("query_text", "").strip()
    if not query_text:
        return _error(400, "query_text is required.")

    top_k = min(int(body.get("top_k", 5)), 10)  # cap at 10

    try:
        results = retrieve(query_text=query_text, top_k=top_k)
    except ValueError as e:
        # KNOWLEDGE_BASE_ID not configured
        return _error(503, str(e))
    except Exception as e:
        return _error(502, f"Bedrock retrieval failed: {str(e)}")

    return _response(200, {
        "query_text":        query_text,
        "retrieval_method":  "bedrock-hybrid",
        "result_count":      len(results),
        "results":           results,
    })


# ---------------------------------------------------------------------------
# Lambda entry point
# ---------------------------------------------------------------------------

def lambda_handler(event: dict, context) -> dict:
    method = event.get("httpMethod", "")
    params = event.get("pathParameters") or {}
    path   = event.get("path", "")

    if method == "GET" and "claim_id" in params:
        claim_id = params["claim_id"]
        if not claim_id:
            return _error(400, "Missing claim_id in path.")
        return get_documents(claim_id)

    if method == "POST" and path.endswith("/search"):
        try:
            body = json.loads(event.get("body") or "{}")
        except json.JSONDecodeError:
            return _error(400, "Request body is not valid JSON.")
        return search_policy_corpus(body)

    return _error(405, f"Method {method} not allowed on path {path}.")
