"""
Mock API Server — ClaimSense Co-pilot
======================================
Stands in for the three client systems (CMS, PAS, Document Store) during
development and testing. Serves the session_pack synthetic dataset through
the same endpoint shapes the production pipeline will call.

Data source
-----------
  session_pack/data/claimsense_claims.csv    — 20 claims
  session_pack/data/claimsense_policies.csv  — 15 policies
  session_pack/data/claimsense_documents.csv — 71 document records

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

  uvicorn mock_api:app --reload --port 8000

  # OpenAPI docs:
  http://localhost:8000/docs

Notes
-----
- All data is loaded from session_pack/data/ at startup.
- The /search endpoint uses BM25 keyword matching over the 12-clause
  AutoSure policy manual. Replace with PDF extraction + real BM25 in M3.
- The CMS write endpoint enforces idempotency via an in-memory store.
"""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from IO_CONTRACTS import (
    CMSClaimRecord,
    CMSDecisionRecord,
    DocStorePolicySearchResponse,
    PolicyClauseChunk,
)
from SYNTHETIC_DATA import _det_id, POLICY_CLAUSE_TEXT

app = FastAPI(
    title="ClaimSense Mock API",
    description="Mock server for CMS, PAS, and Document Store — session_pack data.",
    version="2.0.0",
)

SESSION_PACK = Path(__file__).parent.parent / "ClaimsData" / "data"

# ---------------------------------------------------------------------------
# Load CSVs at startup
# ---------------------------------------------------------------------------

def _load_claims() -> dict[str, dict]:
    out: dict[str, dict] = {}
    with open(SESSION_PACK / "claimsense_claims.csv", newline="") as f:
        for row in csv.DictReader(f):
            out[row["claim_id"]] = row
    return out


def _load_policies() -> dict[str, dict]:
    out: dict[str, dict] = {}
    with open(SESSION_PACK / "claimsense_policies.csv", newline="") as f:
        for row in csv.DictReader(f):
            out[row["policy_id"]] = row
    return out


def _load_documents() -> dict[str, list[dict]]:
    """Returns {claim_id: [doc_row, ...]}."""
    out: dict[str, list[dict]] = {}
    with open(SESSION_PACK / "claimsense_documents.csv", newline="") as f:
        for row in csv.DictReader(f):
            out.setdefault(row["claim_id"], []).append(row)
    return out


_CLAIMS    = _load_claims()
_POLICIES  = _load_policies()
_DOCUMENTS = _load_documents()

# In-memory idempotency store for CMS writes
_decision_store: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# CSV → TypedDict converters
# ---------------------------------------------------------------------------

def _claim_to_record(row: dict) -> dict:
    return CMSClaimRecord(
        claim_id=row["claim_id"],
        policy_id=row["policy_id"],
        incident_date=row["incident_date"],
        incident_type=row["incident_type"],
        incident_description=row["incident_description"],
        vehicle_vin=row["vehicle_vin"],
        vehicle_year=int(row["vehicle_year"]),
        vehicle_make=row["vehicle_make"],
        vehicle_model=row["vehicle_model"],
        vehicle_acv_usd=float(row["vehicle_acv_usd"]),
        repair_estimate_usd=float(row["repair_estimate_usd"]),
        damage_description=row["damage_description"],
        injuries_reported=row["injuries_reported"] == "Yes",
        police_report_filed=row["police_report_filed"] == "Yes",
        assigned_adjuster=row["assigned_adjuster"],
        prior_claims_12mo=int(row["prior_claims_12mo"]),
        fraud_risk_score=float(row["fraud_risk_score"]),
        claim_status=row["claim_status"],
        prior_claims_same_vin=[],
        total_loss_flag=False,
    )


def _policy_to_record(row: dict) -> dict:
    liability_only = row["coverage_type"] == "Liability Only"
    return dict(
        policy_id=row["policy_id"],
        holder_first=row["holder_first"],
        holder_last=row["holder_last"],
        vehicle_vin=row["vehicle_vin"],
        vehicle_year=int(row["vehicle_year"]),
        vehicle_make=row["vehicle_make"],
        vehicle_model=row["vehicle_model"],
        vehicle_acv_usd=float(row["vehicle_acv_usd"]),
        coverage_type=row["coverage_type"],
        collision_coverage=row["collision_coverage"] == "Yes",
        comprehensive_coverage=row["comprehensive_coverage"] == "Yes",
        collision_deductible_usd=(
            None if liability_only else float(row["collision_deductible_usd"])
        ),
        comprehensive_deductible_usd=(
            None if liability_only else float(row["comprehensive_deductible_usd"])
        ),
        liability_limit=row["liability_limit"],
        medpay_limit_usd=(
            float(row["medpay_limit_usd"]) if row["medpay_limit_usd"] != "0" else None
        ),
        policy_status=row["policy_status"],
        policy_period_start=row["policy_start"],
        policy_period_end=row["policy_end"],
        clause_text=POLICY_CLAUSE_TEXT,
    )


def _docs_to_record(claim_id: str, rows: list[dict]) -> dict:
    documents = [
        dict(
            document_id=row["document_id"],
            claim_id=row["claim_id"],
            document_type=row["document_type"],
            description=row["description"],
            ocr_status=row["ocr_status"],
            content_text="",  # PDF content extracted in M3
            uploaded_at=row["upload_date"] + "T09:00:00Z",
        )
        for row in rows
    ]
    return dict(claim_id=claim_id, documents=documents)


# ---------------------------------------------------------------------------
# CMS — GET /claims/{claim_id}
# ---------------------------------------------------------------------------

@app.get("/claims/{claim_id}", response_model=None, tags=["CMS"],
         summary="Read a claim record")
def get_claim(
    claim_id: str,
    x_adjuster_id: str = Header(..., description="Adjuster making the request"),
) -> JSONResponse:
    """
    Returns the claim record for the given claim_id.

    In production, the JWT is verified and the adjuster's entitlement is
    checked before this data is returned. In the mock, any adjuster ID is
    accepted — RBAC is implemented in the MCP layer in M4.
    """
    row = _CLAIMS.get(claim_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found.")
    return JSONResponse(content=_claim_to_record(row))


# ---------------------------------------------------------------------------
# CMS — POST /claims/{claim_id}/decision
# ---------------------------------------------------------------------------

class DecisionPayload(BaseModel):
    adjuster_id: str
    verdict: str
    reasoning_summary: str
    reasoning_chain: list[dict]
    citations: list[dict]
    deterministic_checks_passed: bool
    model_generated: bool
    pipeline_run_id: str


@app.post("/claims/{claim_id}/decision", response_model=None, tags=["CMS"],
          status_code=status.HTTP_201_CREATED,
          summary="Write a confirmed decision to the CMS")
def post_decision(
    claim_id: str,
    payload: DecisionPayload,
    idempotency_key: str = Header(..., description="SHA-256(claim_id:adjuster_id:verdict)"),
) -> JSONResponse:
    """
    Writes a confirmed decision record to the CMS.

    Returns 409 Conflict with the original record on a duplicate key.
    The co-pilot treats 409 as success.
    """
    expected_key = hashlib.sha256(
        f"{claim_id}:{payload.adjuster_id}:{payload.verdict}".encode()
    ).hexdigest()

    if idempotency_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Idempotency-Key does not match SHA-256(claim_id:adjuster_id:verdict).",
        )

    if idempotency_key in _decision_store:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=_decision_store[idempotency_key],
        )

    record = CMSDecisionRecord(
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
        confirmed_at="2026-10-18T10:00:00Z",
        idempotency_key=idempotency_key,
    )
    _decision_store[idempotency_key] = record
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=record)


# ---------------------------------------------------------------------------
# PAS — GET /policies/{policy_id}
# ---------------------------------------------------------------------------

@app.get("/policies/{policy_id}", response_model=None, tags=["PAS"],
         summary="Read a policy record")
def get_policy(policy_id: str) -> JSONResponse:
    row = _POLICIES.get(policy_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Policy {policy_id} not found.")
    return JSONResponse(content=_policy_to_record(row))


# ---------------------------------------------------------------------------
# Document Store — GET /documents/{claim_id}
# ---------------------------------------------------------------------------

@app.get("/documents/{claim_id}", response_model=None, tags=["Document Store"],
         summary="List documents for a claim")
def get_documents(claim_id: str) -> JSONResponse:
    rows = _DOCUMENTS.get(claim_id)
    if rows is None:
        raise HTTPException(status_code=404, detail=f"No documents for claim {claim_id}.")
    return JSONResponse(content=_docs_to_record(claim_id, rows))


# ---------------------------------------------------------------------------
# Document Store — POST /search  (BM25 keyword stub)
# ---------------------------------------------------------------------------

class SearchPayload(BaseModel):
    query_text: str
    top_k: int = 5


@app.post("/search", response_model=None, tags=["Document Store"],
          summary="BM25 search over the policy corpus")
def search_policy_corpus(payload: SearchPayload) -> JSONResponse:
    """
    Returns the top-k policy clause chunks most relevant to the query.

    Uses BM25 keyword matching over the 12-clause AutoSure policy manual
    (CLS-COLL-001 through CLS-PAY-012). Replace with PDF extraction +
    real BM25 index in M3.

    Every coverage output must cite the clause_id from the returned chunks.
    """
    chunks: list[PolicyClauseChunk] = []
    current_id: Optional[str] = None
    current_lines: list[str] = []

    for line in POLICY_CLAUSE_TEXT.strip().splitlines():
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

    chunks.sort(key=lambda c: c["relevance_score"], reverse=True)

    result = DocStorePolicySearchResponse(
        query_text=payload.query_text,
        results=chunks[:payload.top_k],
        retrieval_method="bm25-lexical",
    )
    return JSONResponse(content=result)


def _score_chunk(clause_id: str, clause_text: str, query: str) -> PolicyClauseChunk:
    query_terms = set(query.lower().split())
    text_terms  = set(clause_text.lower().split())
    overlap = len(query_terms & text_terms)
    score = min(round(overlap / max(len(query_terms), 1), 2), 1.0)
    return PolicyClauseChunk(clause_id=clause_id, clause_text=clause_text, relevance_score=score)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health", tags=["Meta"])
def health() -> dict:
    return {
        "status": "ok",
        "claims_loaded": len(_CLAIMS),
        "policies_loaded": len(_POLICIES),
        "document_records_loaded": sum(len(v) for v in _DOCUMENTS.values()),
        "decisions_in_memory": len(_decision_store),
    }
