"""
src/agents/pipeline.py
======================
Orchestrates the full ClaimSense AI adjudication pipeline:

  1. Fetch claim, policy, documents from the Lambda APIs
  2. Run deterministic pre-checks (checks.py)
     → hard_deny: emit DENY immediately, skip all agents
  3. Agent 1 — Document Intake
  4. Agent 2 — Coverage Check  (calls Bedrock KB via DocStore API)
  5. Agent 3 — Claim Assessment
  6. Agent 4 — Decision Draft
  7. Return PipelineResult

Usage
-----
  import asyncio
  from pipeline import run_pipeline
  result = asyncio.run(run_pipeline("CLM-2024-1800"))
"""

from __future__ import annotations

import asyncio
import os
import sys
import uuid
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import httpx

# Ensure src/ is on the path so deterministic.checks is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from deterministic.checks import run_checks, CheckResult

# Agent modules live in the same directory; add it to path
sys.path.insert(0, str(Path(__file__).parent))

from schemas import (
    DocumentIntakeOutput,
    CoverageCheckOutput,
    ClaimAssessmentOutput,
    DecisionDraftOutput,
)
from document_intake import run_document_intake
from coverage_check  import run_coverage_check
from claim_assessment import run_claim_assessment
from decision_draft   import run_decision_draft

_BASE     = os.getenv("API_BASE_URL", "http://localhost:3000")
_ADJUSTER = os.getenv("MCP_ADJUSTER_ID", "mcp-agent")


# ---------------------------------------------------------------------------
# Pipeline result
# ---------------------------------------------------------------------------

@dataclass
class PipelineResult:
    claim_id:        str
    pipeline_run_id: str

    # Final decision fields (always populated)
    verdict:          str          # Approve | Deny | Refer-Fraud | Refer-Adjuster
    model_generated:  bool
    reasoning_summary: str
    reasoning_chain:  list[str]
    citations:        list[str]

    # Whether a hard deny fired before agents ran
    hard_deny:        bool
    deny_reason:      str | None

    # Deterministic arithmetic (always populated)
    net_payable_usd:    float
    deductible_usd:     float
    deductible_applied: str
    total_loss_flag:    bool
    total_loss_ratio:   float

    # Agent outputs (None when hard_deny=True)
    intake:     DocumentIntakeOutput  | None
    coverage:   CoverageCheckOutput   | None
    assessment: ClaimAssessmentOutput | None
    decision:   DecisionDraftOutput   | None

    # Confidence from Decision Draft (None for deterministic denies)
    confidence: str | None


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

async def run_pipeline(
    claim_id: str,
    *,
    claim:     dict | None = None,
    policy:    dict | None = None,
    documents: list[dict] | None = None,
) -> PipelineResult:
    """
    Run the full adjudication pipeline for a claim.

    Parameters
    ----------
    claim_id    Claim to adjudicate (e.g. "CLM-2024-1800")
    claim       Pre-fetched claim dict; fetched from CMS API if None
    policy      Pre-fetched policy dict (with in_force / liability_only);
                fetched from PAS API if None
    documents   Pre-fetched document list; fetched from DocStore API if None
    """
    pipeline_run_id = str(uuid.uuid4())

    # --- Fetch data if not supplied ----------------------------------------
    with httpx.Client(base_url=_BASE, timeout=30.0) as c:
        if claim is None:
            r = c.get(f"/claims/{claim_id}", headers={"X-Adjuster-Id": _ADJUSTER})
            r.raise_for_status()
            claim = r.json()

        policy_id     = claim["policy_id"]
        incident_date = claim.get("incident_date", "")

        if policy is None:
            r = c.get(f"/policies/{policy_id}", params={"incident_date": incident_date})
            r.raise_for_status()
            policy = r.json()

        if documents is None:
            r = c.get("/documents", params={"claim_id": claim_id})
            r.raise_for_status()
            documents = r.json().get("documents", [])

    # --- Deterministic pre-checks ------------------------------------------
    checks: CheckResult = run_checks(claim, policy)

    if checks.hard_deny:
        return PipelineResult(
            claim_id=claim_id,
            pipeline_run_id=pipeline_run_id,
            verdict="Deny",
            model_generated=False,
            reasoning_summary=checks.deny_reason or "Denied by deterministic pre-check.",
            reasoning_chain=[checks.deny_reason or ""],
            citations=[],
            hard_deny=True,
            deny_reason=checks.deny_reason,
            net_payable_usd=float(checks.net_payable_usd),
            deductible_usd=float(checks.deductible_usd),
            deductible_applied=checks.deductible_applied,
            total_loss_flag=checks.total_loss_flag,
            total_loss_ratio=float(checks.total_loss_ratio),
            intake=None,
            coverage=None,
            assessment=None,
            decision=None,
            confidence=None,
        )

    # --- Agent pipeline ----------------------------------------------------
    # Agents run sequentially; each receives the outputs of prior agents

    intake: DocumentIntakeOutput = await run_document_intake(claim, documents)

    coverage: CoverageCheckOutput = await run_coverage_check(claim, policy, intake)

    assessment: ClaimAssessmentOutput = await run_claim_assessment(claim, checks, coverage)

    decision: DecisionDraftOutput = await run_decision_draft(
        claim, checks, intake, coverage, assessment, pipeline_run_id
    )

    return PipelineResult(
        claim_id=claim_id,
        pipeline_run_id=pipeline_run_id,
        verdict=decision.verdict,
        model_generated=True,
        reasoning_summary=decision.reasoning_summary,
        reasoning_chain=decision.reasoning_chain,
        citations=decision.citations,
        hard_deny=False,
        deny_reason=None,
        net_payable_usd=assessment.net_payable_usd,
        deductible_usd=float(checks.deductible_usd),
        deductible_applied=checks.deductible_applied,
        total_loss_flag=assessment.total_loss_flag,
        total_loss_ratio=float(checks.total_loss_ratio),
        intake=intake,
        coverage=coverage,
        assessment=assessment,
        decision=decision,
        confidence=decision.confidence,
    )


# ---------------------------------------------------------------------------
# Convenience sync wrapper for Lambda / scripts
# ---------------------------------------------------------------------------

def run_pipeline_sync(claim_id: str, **kwargs) -> PipelineResult:
    """Synchronous wrapper around run_pipeline for Lambda handlers and scripts."""
    return asyncio.run(run_pipeline(claim_id, **kwargs))


# ---------------------------------------------------------------------------
# CLI entry point: python pipeline.py CLM-2024-1800
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json

    if len(sys.argv) < 2:
        print("Usage: python pipeline.py <claim_id>")
        sys.exit(1)

    result = asyncio.run(run_pipeline(sys.argv[1]))

    print(f"\n{'='*60}")
    print(f"Claim:          {result.claim_id}")
    print(f"Pipeline run:   {result.pipeline_run_id}")
    print(f"Verdict:        {result.verdict}")
    print(f"Model gen:      {result.model_generated}")
    print(f"Hard deny:      {result.hard_deny}")
    print(f"Net payable:    ${result.net_payable_usd:,.2f}")
    print(f"Total loss:     {result.total_loss_flag}")
    print(f"Confidence:     {result.confidence}")
    print(f"\nReasoning summary:\n  {result.reasoning_summary}")
    print(f"\nReasoning chain:")
    for i, step in enumerate(result.reasoning_chain, 1):
        print(f"  {i}. {step}")
    print(f"\nCitations: {', '.join(result.citations) or 'none'}")
    print(f"{'='*60}\n")
