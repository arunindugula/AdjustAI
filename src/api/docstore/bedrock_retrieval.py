"""
bedrock_retrieval.py — Bedrock Knowledge Base retrieval helper
==============================================================
Called by the DocStore Lambda's POST /search endpoint.

Takes a natural language query, calls the Bedrock Knowledge Base,
and returns ranked policy clause chunks with source metadata.

Every chunk includes a source_uri pointing back to the policy manual PDF
in S3 and a score — the Coverage Check agent cites these in its verdict.

Environment variables
---------------------
  KNOWLEDGE_BASE_ID   Bedrock Knowledge Base ID (from template.yaml outputs)
  AWS_DEFAULT_REGION  us-east-1
"""

import os
import boto3

KNOWLEDGE_BASE_ID = os.environ.get("KNOWLEDGE_BASE_ID", "")
REGION            = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")


def get_bedrock_client():
    """
    Returns a bedrock-agent-runtime client.
    For local dev this points at real AWS Bedrock using ~/.aws credentials.
    No local emulator exists for Bedrock — real AWS is used in all environments.
    """
    return boto3.client("bedrock-agent-runtime", region_name=REGION)


def retrieve(query_text: str, top_k: int = 5) -> list[dict]:
    """
    Query the Bedrock Knowledge Base and return the top-k relevant chunks.

    Each returned chunk contains:
      clause_text     — the retrieved passage from the policy manual
      source_uri      — S3 location of the source PDF
      score           — relevance score (0.0 to 1.0)
      clause_id       — extracted from source metadata if available

    The Coverage Check agent uses clause_id for citations in its verdict.
    If clause_id cannot be extracted, the agent falls back to source_uri.
    """
    if not KNOWLEDGE_BASE_ID:
        raise ValueError(
            "KNOWLEDGE_BASE_ID environment variable is not set. "
            "Set it in env.local.json (local dev) or template.yaml (AWS)."
        )

    client = get_bedrock_client()

    response = client.retrieve(
        knowledgeBaseId=KNOWLEDGE_BASE_ID,
        retrievalQuery={"text": query_text},
        retrievalConfiguration={
            "vectorSearchConfiguration": {
                "numberOfResults": top_k,
                # OVERRIDDEN_SEARCH_TYPE uses hybrid search (semantic + keyword)
                # which works better than pure vector search for short clause IDs
                "overrideSearchType": "HYBRID",
            }
        },
    )

    results = []
    for item in response.get("retrievalResults", []):
        content    = item.get("content", {})
        location   = item.get("location", {})
        metadata   = item.get("metadata", {})
        score      = item.get("score", 0.0)

        clause_text = content.get("text", "")
        source_uri  = location.get("s3Location", {}).get("uri", "")

        # Attempt to extract the clause ID from metadata or from the text itself.
        # The policy manual prefixes each clause: "CLS-COLL-001 · Collision..."
        clause_id = metadata.get("clause_id") or _extract_clause_id(clause_text)

        results.append({
            "clause_id":   clause_id,
            "clause_text": clause_text,
            "source_uri":  source_uri,
            "score":       round(score, 4),
        })

    return results


def _extract_clause_id(text: str) -> str:
    """
    Extract the clause ID from the beginning of a policy clause chunk.
    The policy manual format is: 'CLS-XXXX-NNN · Description...'
    Returns empty string if no clause ID is found.
    """
    import re
    match = re.match(r"(CLS-[A-Z]+-\d+)", text.strip())
    return match.group(1) if match else ""
