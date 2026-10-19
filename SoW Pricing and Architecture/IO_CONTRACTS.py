"""
Typed Input/Output Contracts — ClaimSense Co-pilot
===================================================
Defines the data shapes that cross each client system boundary.
All three systems are accessed via read-only APIs except for one
write operation: POST /claims/{id}/decision on the CMS.

Idempotency rule (CMS write only):
  The idempotency key is a SHA-256 hash of (claim_id + adjuster_id + verdict).
  The CMS must reject a second write with the same key and return the
  original record. The co-pilot treats a 409 Conflict response as a
  success and returns the original decision record to the caller.
  This guarantees that a network retry or double-confirmation by the
  adjuster produces exactly one decision record per claim.
"""

from __future__ import annotations
from typing import Literal, Optional
from typing_extensions import TypedDict


# ---------------------------------------------------------------------------
# Shared primitives
# ---------------------------------------------------------------------------

Verdict = Literal["approve", "flag", "siu_route", "deny"]
"""The four decision outcomes the co-pilot can return."""


class EvidenceCitation(TypedDict):
    source_type: Literal["policy_clause", "claim_document", "claim_field"]
    source_id: str
    """Clause identifier, document ID, or CMS field name — never free text."""
    excerpt: str
    """The exact text or value the judgment relied on."""


# ---------------------------------------------------------------------------
# Shared reasoning primitives
# ---------------------------------------------------------------------------

class AgentFinding(TypedDict):
    """The conclusion reached by one agent in the pipeline."""
    agent: Literal["document_intake", "coverage", "risk_fraud", "decision_drafter"]
    finding: str
    """What this agent concluded in plain language."""
    confidence: Literal["high", "medium", "low"]
    """The agent's self-reported confidence in this finding.
    Low confidence findings are flagged to the adjuster for closer review."""
    citations: list[EvidenceCitation]
    """Evidence this specific agent relied on. Must be non-empty."""


# ---------------------------------------------------------------------------
# 1. Claims Management System (CMS)
# ---------------------------------------------------------------------------
# Endpoint: GET  /claims/{claim_id}          — read claim record
# Endpoint: POST /claims/{claim_id}/decision — write confirmed decision
#
# Authentication: short-lived service token (Bearer), scoped to the
# requesting adjuster's entitlement set. Token is obtained from the
# identity service before any CMS call; it is not stored.
# ---------------------------------------------------------------------------

class CMSClaimRequest(TypedDict):
    """Sent as path and query parameters to GET /claims/{claim_id}."""
    claim_id: str
    """Unique claim identifier. Format: CLM-{8 alphanumeric chars}."""
    requesting_adjuster_id: str
    """The adjuster on whose behalf the request is made (OBO identity)."""


class CMSClaimRecord(TypedDict):
    """Returned by GET /claims/{claim_id}."""
    claim_id: str
    policy_id: str
    incident_date: str                      # ISO 8601: YYYY-MM-DD
    incident_type: str
    incident_description: str
    vehicle_vin: str
    vehicle_year: int
    vehicle_make: str
    vehicle_model: str
    vehicle_acv_usd: float                  # actual cash value at inception
    repair_estimate_usd: float
    damage_description: str
    injuries_reported: bool
    police_report_filed: bool
    assigned_adjuster: str                  # adjuster username, e.g. "alice"
    prior_claims_12mo: int                  # number of prior claims in last 12 months
    fraud_risk_score: float                 # vendor score 0.0–1.0; treated as input, not decision
    claim_status: Literal[
        "Approved", "Under Investigation", "Escalated", "Pending Review"
    ]
    prior_claims_same_vin: list[str]        # list of prior claim IDs for this VIN
    total_loss_flag: bool                   # true if VIN has a prior total-loss settlement


class CMSDecisionWriteRequest(TypedDict):
    """
    Body of POST /claims/{claim_id}/decision.

    Idempotency:
      Include header Idempotency-Key: SHA-256(claim_id + adjuster_id + verdict)
      The CMS returns 201 Created on first write, 409 Conflict on a duplicate.
      The co-pilot treats 409 as success and returns the original record.
      The co-pilot never writes without prior adjuster confirmation.
    """
    claim_id: str
    adjuster_id: str
    """The licensed adjuster who confirmed this decision."""
    verdict: Verdict
    reasoning_summary: str
    """Plain-language summary of why this verdict was reached. Max 500 chars.
    Shown in the adjuster UI — written for a human reader, not a machine."""
    reasoning_chain: list[AgentFinding]
    """Structured per-agent findings in pipeline order: document_intake →
    coverage → risk_fraud → decision_drafter. Stored for audit, compliance,
    and regulator requests.
    Allows reconstruction of exactly what each agent found and what evidence
    it relied on, independently of the rolled-up summary."""
    citations: list[EvidenceCitation]
    """Consolidated evidence list across all agents. Must be non-empty.
    Derived from the citations within reasoning_chain — provided at the
    top level for fast lookup without iterating the full chain."""
    deterministic_checks_passed: bool
    """True if all deterministic pre-checks (policy-period, monetary,
    deduplication) passed before the model was invoked. False indicates
    the decision originated from the deterministic fallback path."""
    model_generated: bool
    """True if verdict came from the model pipeline. False if verdict
    came from the deterministic fallback (e.g. policy-period denial)."""
    pipeline_run_id: str
    """Unique ID of the pipeline run that produced this decision.
    Used to correlate with the audit trail and observability logs."""


class CMSDecisionRecord(TypedDict):
    """
    Returned by POST /claims/{claim_id}/decision (201 Created or 409 Conflict).
    """
    decision_id: str
    claim_id: str
    adjuster_id: str
    verdict: Verdict
    reasoning_summary: str
    reasoning_chain: list[AgentFinding]
    citations: list[EvidenceCitation]
    deterministic_checks_passed: bool
    model_generated: bool
    pipeline_run_id: str
    confirmed_at: str                       # ISO 8601 datetime
    idempotency_key: str                    # echoed back for audit correlation


# ---------------------------------------------------------------------------
# 2. Policy Administration System (PAS)
# ---------------------------------------------------------------------------
# Endpoint: GET /policies/{policy_id}  — read policy record
#
# Read-only. The co-pilot never writes to the PAS.
# Policy-period validation (is the loss date within the coverage window?)
# is computed in deterministic code from the fields below; the model
# receives the raw clause text and never a pre-computed coverage boolean.
# ---------------------------------------------------------------------------

class PASPolicyRequest(TypedDict):
    """Sent as path parameter to GET /policies/{policy_id}."""
    policy_id: str
    """Format: POL-{10 alphanumeric chars}."""


class PASCoverageItem(TypedDict):
    coverage_type: str                      # e.g. "comprehensive", "third_party_liability"
    limit_usd: float
    deductible_usd: float
    exclusions: list[str]                   # plain-text exclusion descriptions


class PASPolicyRecord(TypedDict):
    """Returned by GET /policies/{policy_id}."""
    policy_id: str
    holder_first: str
    holder_last: str
    """Holder name is available here for identity verification only.
    It is stripped from the dossier before any model call — the model
    never receives the policyholder's name (ADR-007, DEC-005)."""
    vehicle_vin: str
    vehicle_year: int
    vehicle_make: str
    vehicle_model: str
    vehicle_acv_usd: float
    coverage_type: Literal["Full Coverage", "Liability Only"]
    """Top-level coverage class. Liability Only means no collision or
    comprehensive cover — a first-party claim is a deterministic deny (ADR-006)."""
    collision_coverage: bool
    comprehensive_coverage: bool
    collision_deductible_usd: Optional[float]      # None for Liability Only
    comprehensive_deductible_usd: Optional[float]  # None for Liability Only
    liability_limit: str                           # e.g. "300000/100000"
    medpay_limit_usd: Optional[float]
    policy_status: Literal["Active", "Expired", "Cancelled"]
    policy_period_start: str               # ISO 8601: YYYY-MM-DD
    policy_period_end: str                 # ISO 8601: YYYY-MM-DD
    clause_text: str
    """Full policy clause text from the AutoSure policy manual
    (clauses CLS-COLL-001 through CLS-PAY-012). Passed verbatim to
    the Coverage agent for reading and citation. The model cites clause
    identifiers from this text; it never paraphrases from memory."""


# ---------------------------------------------------------------------------
# 3. Document Store
# ---------------------------------------------------------------------------
# Endpoint: GET  /documents/{claim_id}   — list documents for a claim
# Endpoint: POST /search                 — vector search over policy corpus
#
# Read-only. The co-pilot never writes to the Document Store.
# The policy corpus is pre-indexed; the co-pilot performs vector search
# at inference time. Every coverage output must cite the clause identifier
# returned by the search, not a paraphrase from model memory.
# ---------------------------------------------------------------------------

class DocStoreClaimDocRequest(TypedDict):
    """Sent as path parameter to GET /documents/{claim_id}."""
    claim_id: str


class ClaimDocument(TypedDict):
    document_id: str
    claim_id: str
    document_type: Literal[
        "FNOL_FORM",
        "POLICE_REPORT",
        "REPAIR_ESTIMATE",
        "MEDICAL_REPORT",
        "WITNESS_STATEMENT",
        "DAMAGE_PHOTOS",
        "RENTAL_RECEIPT",
    ]
    description: str
    ocr_status: Literal["Completed", "Pending"]
    """Pending means the document has not yet been OCR-processed.
    The pipeline must surface which documents are pending to the adjuster
    and note that coverage assessment is incomplete until they clear."""
    content_text: str
    """Extracted text content from OCR. Empty string when ocr_status is
    Pending. Used by Document Intake and Coverage agents; never used to
    override deterministic checks."""
    uploaded_at: str                        # ISO 8601 datetime


class DocStoreClaimDocResponse(TypedDict):
    """Returned by GET /documents/{claim_id}."""
    claim_id: str
    documents: list[ClaimDocument]


class DocStorePolicySearchRequest(TypedDict):
    """Body of POST /search — vector search over the policy corpus."""
    query_text: str
    """The claim narrative or coverage question the agent is resolving."""
    top_k: int
    """Number of clause chunks to return. Recommended: 5."""


class PolicyClauseChunk(TypedDict):
    clause_id: str
    """Stable identifier for this clause chunk (e.g. CLS-COLL-001).
    Must be cited in any coverage output that relies on this chunk.
    A coverage statement without a retrieved clause ID is rejected
    by the output validator."""
    clause_text: str
    relevance_score: float                  # BM25 score, higher = more relevant


class DocStorePolicySearchResponse(TypedDict):
    """Returned by POST /search."""
    query_text: str
    results: list[PolicyClauseChunk]
    retrieval_method: str
    """Retrieval method in use. 'bm25-lexical' for the pilot (12 clauses);
    upgrade path to vector search documented in ADR-003."""


# ---------------------------------------------------------------------------
# Idempotency rule — summary
# ---------------------------------------------------------------------------
#
# Only the CMS write (POST /claims/{claim_id}/decision) is a mutating
# operation. All other endpoints are read-only.
#
# Key derivation:
#   import hashlib
#   key = hashlib.sha256(
#       f"{claim_id}:{adjuster_id}:{verdict}".encode()
#   ).hexdigest()
#
# Sent as request header:
#   Idempotency-Key: <key>
#
# CMS behaviour:
#   201 Created   — first write, record stored
#   409 Conflict  — duplicate key, original record returned in body
#
# Co-pilot behaviour on 409:
#   Treat as success. Return the original CMSDecisionRecord to the caller.
#   Do not retry. Do not surface an error to the adjuster.
#   Log the duplicate attempt to the audit trail with event_type="duplicate_write".
#
# This guarantees exactly-once semantics for the decision record
# regardless of network retries or adjuster double-confirmation.
# ---------------------------------------------------------------------------
