"""
Agent 3 — Claim Assessment
===========================
Assesses fraud risk and injury complexity using the deterministic arithmetic
values computed by checks.py (net_payable, total_loss_ratio, fraud_risk_score).

The model must echo net_payable_usd and total_loss_flag from the prompt —
it must NOT recompute them (ADR-005). The pipeline validates they match.

Input:  claim, CheckResult arithmetic, CoverageCheckOutput
Output: ClaimAssessmentOutput
"""

from __future__ import annotations

import os

from openai import AsyncOpenAI

from schemas import ClaimAssessmentOutput, CoverageCheckOutput

_client = AsyncOpenAI()
_MODEL  = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

_SYSTEM = """\
You are the Claim Assessment agent for an insurance claims adjudication system.

Your responsibilities:
1. Assess fraud risk based on: fraud_risk_score, prior_claims_12mo, inconsistencies \
   between reported damage and incident description, and timing patterns.
   - fraud_risk_score >= 0.7  → likely "high"
   - fraud_risk_score 0.4–0.7 → likely "moderate"
   - fraud_risk_score < 0.4   → likely "low"
   List specific fraud_indicators observed; an empty list is valid for low-risk claims.

2. Assess injury complexity:
   - "none"    → injuries_reported = No
   - "minor"   → injuries_reported = Yes, no structural involvement
   - "complex" → injuries_reported = Yes with structural damage or multiple parties

3. Echo net_payable_usd and total_loss_flag EXACTLY as given in the prompt.
   Do NOT recompute them. These are deterministic values from the system.

Be specific and factual. Do not recommend a verdict — that is the Decision Draft agent's job.\
"""


async def run_claim_assessment(
    claim:    dict,
    checks,                      # CheckResult from deterministic/checks.py
    coverage: CoverageCheckOutput,
) -> ClaimAssessmentOutput:
    user_msg = _build_prompt(claim, checks, coverage)

    result = await _client.beta.chat.completions.parse(
        model=_MODEL,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user",   "content": user_msg},
        ],
        response_format=ClaimAssessmentOutput,
        temperature=0,
    )
    output = result.choices[0].message.parsed

    # Guard: ensure model echoed deterministic values correctly (ADR-005)
    output.net_payable_usd = float(checks.net_payable_usd)
    output.total_loss_flag = checks.total_loss_flag

    return output


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def _build_prompt(claim: dict, checks, coverage: CoverageCheckOutput) -> str:
    clauses = "; ".join(c.clause_id for c in coverage.cited_clauses)

    return (
        f"CLAIM:\n"
        f"  Claim ID:           {claim.get('claim_id')}\n"
        f"  Incident type:      {claim.get('incident_type')}\n"
        f"  Incident date:      {claim.get('incident_date')}\n"
        f"  Incident desc:      {claim.get('incident_description')}\n"
        f"  Damage desc:        {claim.get('damage_description')}\n"
        f"  Injuries reported:  {'Yes' if claim.get('injuries_reported') else 'No'}\n"
        f"  Police report:      {'Yes' if claim.get('police_report_filed') else 'No'}\n"
        f"  Prior claims 12mo:  {claim.get('prior_claims_12mo', 0)}\n"
        f"  Fraud risk score:   {float(claim.get('fraud_risk_score', 0)):.2f}\n\n"
        f"DETERMINISTIC ARITHMETIC (DO NOT RECOMPUTE — echo these exactly):\n"
        f"  net_payable_usd:    ${float(checks.net_payable_usd):,.2f}\n"
        f"  deductible_usd:     ${float(checks.deductible_usd):,.2f} ({checks.deductible_applied})\n"
        f"  total_loss_flag:    {checks.total_loss_flag}\n"
        f"  total_loss_ratio:   {float(checks.total_loss_ratio):.1%}\n\n"
        f"COVERAGE CHECK RESULT:\n"
        f"  coverage_applicable: {coverage.coverage_applicable}\n"
        f"  coverage_type:       {coverage.coverage_type}\n"
        f"  cited_clauses:       {clauses}\n"
        f"  exclusions:          {'; '.join(coverage.exclusions_identified) or 'none'}\n"
    )
