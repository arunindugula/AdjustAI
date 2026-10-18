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
    agent: Literal["coverage", "risk_fraud", "decision_drafter"]
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
    incident_description: str
    vehicle_vin: str
    claimant_id: str
    damage_estimate_usd: float
    repair_history: list[str]               # list of prior repair IDs
    claim_status: Literal[
        "open", "under_review", "pending_decision", "closed"
    ]
    prior_claims_same_vin: list[str]        # list of prior claim IDs for VIN
    prior_claims_same_claimant: list[str]   # list of prior claim IDs for claimant
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
    """Structured per-agent findings in pipeline order: coverage → risk_fraud
    → decision_drafter. Stored for audit, compliance, and regulator requests.
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
    named_insured_id: str
    covered_vins: list[str]
    policy_period_start: str               # ISO 8601: YYYY-MM-DD
    policy_period_end: str                 # ISO 8601: YYYY-MM-DD
    premium_payment_status: Literal["current", "lapsed", "cancelled"]
    coverages: list[PASCoverageItem]
    endorsements: list[str]                # endorsement identifiers
    clause_text: str
    """Full policy clause text as a single string. Passed verbatim to the
    Coverage Agent for reading and citation. The model cites clause
    identifiers from this text; it does not paraphrase from memory."""


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
        "police_report",
        "repair_estimate",
        "medical_record",
        "witness_statement",
        "photograph",
        "prior_correspondence",
    ]
    content_text: str
    """Extracted text content. Used by the Risk Agent; never used to
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
    """Stable identifier for this clause chunk. Must be cited in any
    coverage output that relies on this chunk."""
    clause_text: str
    relevance_score: float                  # cosine similarity, 0.0–1.0


class DocStorePolicySearchResponse(TypedDict):
    """Returned by POST /search."""
    query_text: str
    results: list[PolicyClauseChunk]
    embedding_model_version: str
    """Version of the embedding model used to build the index.
    A version change invalidates the existing index and requires
    a full re-index before search results are trusted."""


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
