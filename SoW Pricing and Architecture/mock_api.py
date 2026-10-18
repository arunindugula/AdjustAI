"""
Mock API Server — ClaimSense Co-pilot
======================================
Stands in for the three client systems (CMS, PAS, Document Store) during
development and testing. Serves synthetic data through the same endpoints
the production pipeline will call.

Endpoints
---------
  CMS
    GET  /claims/{claim_id}            → CMSClaimRecord
    POST /claims/{claim_id}/decision   → CMSDecisionRecord (idempotent)

  PAS
    GET  /policies/{policy_id}         → PASPolicyRecord

  Document Store
    GET  /documents/{claim_id}         → DocStoreClaimDocResponse
    POST /search                       → DocStorePolicySearchResponse

Run
---
  pip install fastapi uvicorn

  # Generate fixtures first (if not already done)
  python SYNTHETIC_DATA.py

  # Start the server
  uvicorn mock_api:app --reload --port 8000

  # OpenAPI docs available at:
  http://localhost:8000/docs

Notes
-----
- Loads fixtures from the fixtures/ directory when available.
- Falls back to factory functions for claim IDs not in fixtures.
- The /search endpoint uses keyword matching as a stand-in for
  vector search. Replace with a real embedding search in M3.
- The CMS write endpoint enforces idempotency via an in-memory store.
  In production this is handled by the CMS itself.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from IO_CONTRACTS import (
    CMSClaimRecord,
    CMSDecisionWriteRequest,
    CMSDecisionRecord,
    PASPolicyRecord,
    DocStoreClaimDocResponse,
    DocStorePolicySearchRequest,
    DocStorePolicySearchResponse,
    PolicyClauseChunk,
)
from SYNTHETIC_DATA import (
    make_claim,
    make_policy,
    make_documents,
    _det_id,
    _policy_clause_text,
)

app = FastAPI(
    title="ClaimSense Mock API",
    description="Mock server for CMS, PAS, and Document Store — synthetic data only.",
    version="1.0.0",
)

FIXTURES_DIR = Path("fixtures")

# In-memory idempotency store for CMS writes: {idempotency_key: CMSDecisionRecord}
_decision_store: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_fixture(claim_id: str) -> dict | None:
    """Load a fixture JSON file if it exists."""
    path = FIXTURES_DIR / f"{claim_id}.json"
    if path.exists():
        return json.loads(path.read_text())
    return None


def _policy_id_for_claim(claim_id: str) -> str:
    return _det_id(claim_id + "policy", "POL-")


# ---------------------------------------------------------------------------
# CMS — GET /claims/{claim_id}
# ---------------------------------------------------------------------------

@app.get(
    "/claims/{claim_id}",
    response_model=None,
    summary="Read a claim record",
    tags=["CMS"],
)
def get_claim(
    claim_id: str,
    x_adjuster_id: str = Header(..., description="Adjuster making the request (OBO identity)"),
) -> JSONResponse:
    """
    Returns the claim record for the given claim_id.

    In production the service token is validated and the adjuster's
    entitlement is checked before this data is returned. In the mock,
    any adjuster ID is accepted.
    """
    fixture = _load_fixture(claim_id)
    if fixture:
        return JSONResponse(content=fixture["claim"])

    # Fall back to factory — default to an approve scenario
    claim = make_claim(claim_id, outcome="approve")
    return JSONResponse(content=claim)


# ---------------------------------------------------------------------------
# CMS — POST /claims/{claim_id}/decision
# ---------------------------------------------------------------------------

class DecisionPayload(BaseModel):
    """Request body for the CMS decision write endpoint."""
    adjuster_id: str
    verdict: str
    reasoning_summary: str
    reasoning_chain: list[dict]
    citations: list[dict]
    deterministic_checks_passed: bool
    model_generated: bool
    pipeline_run_id: str


@app.post(
    "/claims/{claim_id}/decision",
    response_model=None,
    status_code=status.HTTP_201_CREATED,
    summary="Write a confirmed decision to the CMS",
    tags=["CMS"],
)
def post_decision(
    claim_id: str,
    payload: DecisionPayload,
    idempotency_key: str = Header(..., description="SHA-256(claim_id:adjuster_id:verdict)"),
) -> JSONResponse:
    """
    Writes a confirmed decision record to the CMS.

    Idempotency:
      If the Idempotency-Key header matches an existing record, returns
      409 Conflict with the original record — the co-pilot treats this
      as success and does not surface an error to the adjuster.

    Validation:
      The server recomputes the expected key and rejects requests where
      the provided key does not match SHA-256(claim_id:adjuster_id:verdict).
    """
    # Validate idempotency key
    expected_key = hashlib.sha256(
        f"{claim_id}:{payload.adjuster_id}:{payload.verdict}".encode()
    ).hexdigest()

    if idempotency_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Idempotency-Key does not match expected value. "
                f"Derive key as SHA-256(claim_id:adjuster_id:verdict)."
            ),
        )

    # Duplicate write — return original record
    if idempotency_key in _decision_store:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=_decision_store[idempotency_key],
        )

    # First write — create and store the record
    record: CMSDecisionRecord = CMSDecisionRecord(
        decision_id=_det_id(idempotency_key, "DEC-"),
        claim_id=claim_id,
        adjuster_id=payload.adjuster_id,
        verdict=payload.verdict,                        # type: ignore[arg-type]
        reasoning_summary=payload.reasoning_summary,
        reasoning_chain=payload.reasoning_chain,        # type: ignore[arg-type]
        citations=payload.citations,                    # type: ignore[arg-type]
        deterministic_checks_passed=payload.deterministic_checks_passed,
        model_generated=payload.model_generated,
        pipeline_run_id=payload.pipeline_run_id,
        confirmed_at="2026-09-03T10:00:00Z",
        idempotency_key=idempotency_key,
    )

    _decision_store[idempotency_key] = record
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=record)


# ---------------------------------------------------------------------------
# PAS — GET /policies/{policy_id}
# ---------------------------------------------------------------------------

@app.get(
    "/policies/{policy_id}",
    response_model=None,
    summary="Read a policy record",
    tags=["PAS"],
)
def get_policy(policy_id: str) -> JSONResponse:
    """
    Returns the policy record for the given policy_id.

    Looks up the fixture whose claim's policy_id matches. Falls back
    to the policy factory for unknown policy IDs.
    """
    # Search fixtures for a matching policy_id
    if FIXTURES_DIR.exists():
        for path in FIXTURES_DIR.glob("*.json"):
            fixture = json.loads(path.read_text())
            if fixture.get("policy", {}).get("policy_id") == policy_id:
                return JSONResponse(content=fixture["policy"])

    # Fall back to factory
    policy = make_policy(policy_id)
    return JSONResponse(content=policy)


# ---------------------------------------------------------------------------
# Document Store — GET /documents/{claim_id}
# ---------------------------------------------------------------------------

@app.get(
    "/documents/{claim_id}",
    response_model=None,
    summary="List documents for a claim",
    tags=["Document Store"],
)
def get_documents(claim_id: str) -> JSONResponse:
    """
    Returns all documents associated with the given claim_id.
    """
    fixture = _load_fixture(claim_id)
    if fixture:
        return JSONResponse(content=fixture["documents"])

    # Fall back to factory
    docs = make_documents(claim_id)
    return JSONResponse(content=docs)


# ---------------------------------------------------------------------------
# Document Store — POST /search
# ---------------------------------------------------------------------------

class SearchPayload(BaseModel):
    query_text: str
    top_k: int = 5


@app.post(
    "/search",
    response_model=None,
    summary="Vector search over the policy corpus",
    tags=["Document Store"],
)
def search_policy_corpus(payload: SearchPayload) -> JSONResponse:
    """
    Returns the top-k policy clause chunks most relevant to the query.

    In production this performs vector (embedding) search over the indexed
    policy corpus. In the mock, it uses keyword matching as a stand-in.
    Replace with a real embedding search in M3.

    Every coverage output must cite the clause_id from the returned chunks —
    the model never paraphrases policy terms from memory.
    """
    clause_text = _policy_clause_text(["comprehensive", "third_party_liability"])

    # Parse clause text into chunks by [CLAUSE-ID] markers
    chunks: list[PolicyClauseChunk] = []
    current_id: str | None = None
    current_lines: list[str] = []

    for line in clause_text.strip().splitlines():
        line = line.strip()
        if line.startswith("[") and "]" in line:
            if current_id and current_lines:
                chunks.append(_score_chunk(current_id, "\n".join(current_lines), payload.query_text))
            bracket_end = line.index("]")
            current_id = line[1:bracket_end]
            current_lines = [line[bracket_end + 1:].strip()]
        elif line and current_id is not None:
            current_lines.append(line)

    if current_id and current_lines:
        chunks.append(_score_chunk(current_id, "\n".join(current_lines), payload.query_text))

    # Sort by relevance score descending, return top_k
    chunks.sort(key=lambda c: c["relevance_score"], reverse=True)
    top = chunks[:payload.top_k]

    result: DocStorePolicySearchResponse = DocStorePolicySearchResponse(
        query_text=payload.query_text,
        results=top,
        embedding_model_version="mock-keyword-v1",
    )
    return JSONResponse(content=result)


def _score_chunk(clause_id: str, clause_text: str, query: str) -> PolicyClauseChunk:
    """Keyword-based relevance score — stand-in for cosine similarity."""
    query_terms = set(query.lower().split())
    text_terms  = set(clause_text.lower().split())
    overlap = len(query_terms & text_terms)
    score = min(round(overlap / max(len(query_terms), 1), 2), 1.0)
    return PolicyClauseChunk(
        clause_id=clause_id,
        clause_text=clause_text,
        relevance_score=score,
    )


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health", tags=["Meta"])
def health() -> dict:
    return {
        "status": "ok",
        "fixtures_loaded": len(list(FIXTURES_DIR.glob("*.json"))) if FIXTURES_DIR.exists() else 0,
        "decisions_in_memory": len(_decision_store),
    }
