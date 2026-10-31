"""
Strict Pydantic output schemas for the 4 ClaimSense AI agents.

Every agent uses OpenAI structured outputs (response_format=<PydanticModel>),
so the model is guaranteed to return a valid instance of each schema.
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Literal


# ---------------------------------------------------------------------------
# Agent 1 — Document Intake
# ---------------------------------------------------------------------------

class DocumentRecord(BaseModel):
    document_id:     str
    document_type:   str
    status:          Literal["ready", "pending_ocr"]
    content_summary: str   # one sentence; empty string for pending_ocr docs


class DocumentIntakeOutput(BaseModel):
    documents_ready:       list[DocumentRecord]
    documents_pending_ocr: list[str]    # document_ids still waiting for OCR
    key_facts:             list[str]    # facts extracted from docs relevant to the claim
    intake_notes:          str          # overall assessment (2-3 sentences)


# ---------------------------------------------------------------------------
# Agent 2 — Coverage Check
# ---------------------------------------------------------------------------

class ClauseReference(BaseModel):
    clause_id:          str   # e.g. CLS-COLL-001 — from search_policy_corpus results
    relevance_summary:  str   # one sentence: how this clause applies to this claim


class CoverageCheckOutput(BaseModel):
    coverage_applicable:    bool
    coverage_type:          str                          # "collision" | "comprehensive" | "none"
    cited_clauses:          list[ClauseReference] = Field(min_length=1)  # must cite at least one
    exclusions_identified:  list[str]                    # applicable policy exclusions, if any
    coverage_notes:         str


# ---------------------------------------------------------------------------
# Agent 3 — Claim Assessment
# ---------------------------------------------------------------------------

class ClaimAssessmentOutput(BaseModel):
    fraud_indicators:   list[str]                        # specific observed indicators
    fraud_assessment:   Literal["low", "moderate", "high"]
    injury_complexity:  Literal["none", "minor", "complex"]
    # Echo deterministic values — do not modify; the pipeline validates these match
    net_payable_usd:    float
    total_loss_flag:    bool
    assessment_notes:   str


# ---------------------------------------------------------------------------
# Agent 4 — Decision Draft
# ---------------------------------------------------------------------------

class DecisionDraftOutput(BaseModel):
    verdict:           Literal["Approve", "Deny", "Refer-Fraud", "Refer-Adjuster"]
    reasoning_summary: str                               # 1-2 sentences for the adjuster
    reasoning_chain:   list[str] = Field(min_length=3)  # ordered reasoning steps
    citations:         list[str]                         # clause_ids from CoverageCheckOutput
    confidence:        Literal["high", "medium", "low"]
    model_generated:   bool = True
