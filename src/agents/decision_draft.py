"""
Agent 4 — Decision Draft
=========================
Synthesises all prior agent outputs into a final verdict.
This is the only agent that sets model_generated=True.

Verdict rules (the model must follow these):
  Approve         — coverage_applicable=True, fraud_assessment=low,
                    in_force=True, net_payable > 0, no complex injuries,
                    no total loss (or total loss with full coverage)
  Deny            — coverage not applicable (but this is rarely reached here;
                    hard denies are caught by pre-checks)
  Refer-Fraud     — fraud_risk_score >= 0.4 OR fraud_assessment=high/moderate
  Refer-Adjuster  — injuries_reported + injury_complexity=complex,
                    OR total_loss_flag=True with ambiguous coverage,
                    OR conflicting evidence

Input:  claim, checks, intake, coverage, assessment
Output: DecisionDraftOutput (model_generated=True)
"""

from __future__ import annotations

import os

from openai import AsyncOpenAI

from schemas import (
    DecisionDraftOutput, DocumentIntakeOutput,
    CoverageCheckOutput, ClaimAssessmentOutput,
)

_client = AsyncOpenAI()
_MODEL  = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

_SYSTEM = """\
You are the Decision Draft agent for an insurance claims adjudication system.

You receive a complete adjudication dossier: claim facts, deterministic arithmetic, \
coverage check results with cited policy clauses, and a fraud/injury assessment.

Your job is to produce the final verdict and reasoning chain that an adjuster will review.

VERDICT RULES (follow strictly):
  Refer-Fraud     → fraud_risk_score >= 0.4 OR fraud_assessment is "high" or "moderate"
                    Refer-Fraud takes priority over Approve.
  Refer-Adjuster  → injury_complexity is "complex", OR total_loss_flag=True with unclear \
                    coverage, OR conflicting evidence requires human judgment.
  Approve         → coverage_applicable=True, fraud_assessment="low", in_force=True, \
                    net_payable > 0, no complex injuries.
  Deny            → coverage_applicable=False (and not caught by pre-checks).

REASONING CHAIN: at least 3 ordered steps. Each step is one sentence explaining one \
decision factor. The last step must state the verdict and its primary reason.

CITATIONS: list the clause_ids from the coverage check that support your verdict.
Do not invent clause IDs. Use only what was retrieved.

Set confidence:
  "high"   → all signals agree, clear outcome
  "medium" → minor ambiguity or borderline score
  "low"    → conflicting evidence, unclear coverage, multiple plausible verdicts\
"""


async def run_decision_draft(
    claim:      dict,
    checks,                       # CheckResult
    intake:     DocumentIntakeOutput,
    coverage:   CoverageCheckOutput,
    assessment: ClaimAssessmentOutput,
    pipeline_run_id: str,
) -> DecisionDraftOutput:
    user_msg = _build_prompt(claim, checks, intake, coverage, assessment, pipeline_run_id)

    result = await _client.beta.chat.completions.parse(
        model=_MODEL,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user",   "content": user_msg},
        ],
        response_format=DecisionDraftOutput,
        temperature=0,
    )
    output = result.choices[0].message.parsed
    output.model_generated = True   # enforce — agents always set this
    return output


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def _build_prompt(
    claim: dict,
    checks,
    intake:     DocumentIntakeOutput,
    coverage:   CoverageCheckOutput,
    assessment: ClaimAssessmentOutput,
    pipeline_run_id: str,
) -> str:
    clauses    = "; ".join(c.clause_id for c in coverage.cited_clauses)
    exclusions = "; ".join(coverage.exclusions_identified) or "none"
    indicators = "; ".join(assessment.fraud_indicators) or "none"
    pending    = ", ".join(intake.documents_pending_ocr) or "none"

    return (
        f"PIPELINE RUN: {pipeline_run_id}\n\n"
        f"CLAIM:\n"
        f"  Claim ID:           {claim.get('claim_id')}\n"
        f"  Incident type:      {claim.get('incident_type')}\n"
        f"  Incident date:      {claim.get('incident_date')}\n"
        f"  Injuries reported:  {'Yes' if claim.get('injuries_reported') else 'No'}\n"
        f"  Police report:      {'Yes' if claim.get('police_report_filed') else 'No'}\n"
        f"  Prior claims 12mo:  {claim.get('prior_claims_12mo', 0)}\n"
        f"  Fraud risk score:   {float(claim.get('fraud_risk_score', 0)):.2f}\n\n"
        f"DETERMINISTIC ARITHMETIC:\n"
        f"  net_payable_usd:    ${assessment.net_payable_usd:,.2f}\n"
        f"  deductible:         ${float(checks.deductible_usd):,.2f} ({checks.deductible_applied})\n"
        f"  total_loss_flag:    {assessment.total_loss_flag}\n"
        f"  total_loss_ratio:   {float(checks.total_loss_ratio):.1%}\n\n"
        f"COVERAGE CHECK:\n"
        f"  coverage_applicable: {coverage.coverage_applicable}\n"
        f"  coverage_type:       {coverage.coverage_type}\n"
        f"  cited_clauses:       {clauses}\n"
        f"  exclusions:          {exclusions}\n\n"
        f"CLAIM ASSESSMENT:\n"
        f"  fraud_assessment:    {assessment.fraud_assessment}\n"
        f"  fraud_indicators:    {indicators}\n"
        f"  injury_complexity:   {assessment.injury_complexity}\n\n"
        f"DOCUMENT INTAKE:\n"
        f"  ready_docs:          {len(intake.documents_ready)}\n"
        f"  pending_ocr:         {pending}\n"
        f"  intake_notes:        {intake.intake_notes}\n\n"
        f"Produce your DecisionDraftOutput verdict and reasoning chain."
    )
