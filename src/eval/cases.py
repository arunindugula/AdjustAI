"""
src/eval/cases.py
=================
21 eval cases covering all four decision outcomes and every pre-check path.

Case distribution
-----------------
  Deny            7  (4 × Liability Only, 2 × Expired, 1 × net-payable floor)
  Refer-Fraud     4  (fraud_risk_score ≥ 0.42 in each)
  Refer-Adjuster  2  (injuries + total loss in each)
  Approve         8  (fraud < 0.35, no injuries, full coverage, in-force)
  Total          21

Cases that use real claim_ids are fetched from the running API.
Case EVAL-SYNTH-001 injects dicts directly — no DynamoDB entry needed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal


@dataclass
class EvalCase:
    case_id:                   str
    description:               str
    expected_verdict:          str   # Approve | Deny | Refer-Fraud | Refer-Adjuster
    expected_model_generated:  bool

    # Real claims — pipeline fetches from API when claim_id is set
    claim_id: str | None = None

    # Synthetic claims — injected directly into run_pipeline() when set
    claim:     dict | None = None
    policy:    dict | None = None
    documents: list[dict] = field(default_factory=list)


# ===========================================================================
# DENY — Deterministic pre-checks (model_generated=False)
# ===========================================================================

_DENY_CASES: list[EvalCase] = [

    EvalCase(
        case_id="EVAL-001",
        description="Liability Only policy — hail damage not covered (CLM-2024-2019)",
        expected_verdict="Deny",
        expected_model_generated=False,
        claim_id="CLM-2024-2019",
    ),

    EvalCase(
        case_id="EVAL-002",
        description="Liability Only policy — garage fire not covered (CLM-2024-3114)",
        expected_verdict="Deny",
        expected_model_generated=False,
        claim_id="CLM-2024-3114",
    ),

    EvalCase(
        case_id="EVAL-003",
        description="Liability Only policy — animal strike not covered (CLM-2024-2238)",
        expected_verdict="Deny",
        expected_model_generated=False,
        claim_id="CLM-2024-2238",
    ),

    EvalCase(
        case_id="EVAL-004",
        description="Liability Only policy — multi-vehicle pileup not covered (CLM-2024-2676)",
        expected_verdict="Deny",
        expected_model_generated=False,
        claim_id="CLM-2024-2676",
    ),

    EvalCase(
        case_id="EVAL-005",
        description="Expired policy — backing accident 13 months after expiry (CLM-2024-2530)",
        expected_verdict="Deny",
        expected_model_generated=False,
        claim_id="CLM-2024-2530",
    ),

    EvalCase(
        case_id="EVAL-006",
        description="Expired policy — pothole damage 3 days after policy lapse (CLM-2024-2822)",
        expected_verdict="Deny",
        expected_model_generated=False,
        claim_id="CLM-2024-2822",
    ),

    EvalCase(
        case_id="EVAL-007",
        description="Net payable floor — repair ($150) below deductible ($500) [synthetic]",
        expected_verdict="Deny",
        expected_model_generated=False,
        claim_id=None,
        claim={
            "claim_id":             "EVAL-SYNTH-001",
            "policy_id":            "POL-SYNTH-001",
            "incident_date":        "2024-02-01",
            "incident_type":        "Parking lot collision",
            "incident_description": "Minor paint scuff from shopping cart in parking lot.",
            "damage_description":   "Light paint scratch on rear bumper. No structural damage.",
            "repair_estimate_usd":  Decimal("150"),
            "vehicle_acv_usd":      Decimal("25000"),
            "injuries_reported":    False,
            "police_report_filed":  False,
            "prior_claims_12mo":    0,
            "fraud_risk_score":     Decimal("0.02"),
            "vehicle_make":         "Honda",
            "vehicle_model":        "Civic",
            "vehicle_year":         2020,
        },
        policy={
            "policy_id":                    "POL-SYNTH-001",
            "coverage_type":                "Full Coverage",
            "collision_coverage":           True,
            "comprehensive_coverage":       True,
            "collision_deductible_usd":     Decimal("500"),
            "comprehensive_deductible_usd": Decimal("500"),
            "vehicle_acv_usd":              Decimal("25000"),
            "liability_only":               False,
            "in_force":                     True,
            "policy_status":                "Active",
            "policy_start":                 "2023-01-01",
            "policy_end":                   "2025-01-01",
        },
        documents=[],
    ),
]

# ===========================================================================
# REFER-FRAUD — fraud_risk_score ≥ 0.40 (model_generated=True)
# ===========================================================================

_FRAUD_CASES: list[EvalCase] = [

    EvalCase(
        case_id="EVAL-008",
        description="High fraud score 0.87 — single-vehicle 2AM no witnesses (CLM-2024-1873)",
        expected_verdict="Refer-Fraud",
        expected_model_generated=True,
        claim_id="CLM-2024-1873",
    ),

    EvalCase(
        case_id="EVAL-009",
        description="Borderline fraud score 0.42 — rollover with injuries (CLM-2024-2457)",
        expected_verdict="Refer-Fraud",
        expected_model_generated=True,
        claim_id="CLM-2024-2457",
    ),

    EvalCase(
        case_id="EVAL-010",
        description="High fraud score 0.78 — theft recovery, interior stripped (CLM-2024-2603)",
        expected_verdict="Refer-Fraud",
        expected_model_generated=True,
        claim_id="CLM-2024-2603",
    ),

    EvalCase(
        case_id="EVAL-011",
        description="High fraud score 0.65 — carjacking with injuries (CLM-2024-2968)",
        expected_verdict="Refer-Fraud",
        expected_model_generated=True,
        claim_id="CLM-2024-2968",
    ),
]

# ===========================================================================
# REFER-ADJUSTER — injuries + total loss (model_generated=True)
# ===========================================================================

_ADJUSTER_CASES: list[EvalCase] = [

    EvalCase(
        case_id="EVAL-012",
        description="T-bone with injuries; repair/ACV=127% (total loss) (CLM-2024-1946)",
        expected_verdict="Refer-Adjuster",
        expected_model_generated=True,
        claim_id="CLM-2024-1946",
    ),

    EvalCase(
        case_id="EVAL-013",
        description="Underride with injuries; repair/ACV=91.7% (total loss) (CLM-2024-3187)",
        expected_verdict="Refer-Adjuster",
        expected_model_generated=True,
        claim_id="CLM-2024-3187",
    ),
]

# ===========================================================================
# APPROVE — clean claims (model_generated=True)
# ===========================================================================

_APPROVE_CASES: list[EvalCase] = [

    EvalCase(
        case_id="EVAL-014",
        description="Clean approve — parking lot, fraud=0.05, no injuries (CLM-2024-1800)",
        expected_verdict="Approve",
        expected_model_generated=True,
        claim_id="CLM-2024-1800",
    ),

    EvalCase(
        case_id="EVAL-015",
        description="Clean approve — rear-end highway, fraud=0.08, no injuries (CLM-2024-2092)",
        expected_verdict="Approve",
        expected_model_generated=True,
        claim_id="CLM-2024-2092",
    ),

    EvalCase(
        case_id="EVAL-016",
        description="Approve — hit and run, fraud=0.22, no injuries (CLM-2024-2165)",
        expected_verdict="Approve",
        expected_model_generated=True,
        claim_id="CLM-2024-2165",
    ),

    EvalCase(
        case_id="EVAL-017",
        description="Approve — flood damage, fraud=0.31 (below 0.40 threshold), no injuries (CLM-2024-2311)",
        expected_verdict="Approve",
        expected_model_generated=True,
        claim_id="CLM-2024-2311",
    ),

    EvalCase(
        case_id="EVAL-018",
        description="Approve — vandalism, fraud=0.15, no injuries (CLM-2024-2384)",
        expected_verdict="Approve",
        expected_model_generated=True,
        claim_id="CLM-2024-2384",
    ),

    EvalCase(
        case_id="EVAL-019",
        description="Approve — side-swipe, fraud=0.09, no injuries (CLM-2024-2749)",
        expected_verdict="Approve",
        expected_model_generated=True,
        claim_id="CLM-2024-2749",
    ),

    EvalCase(
        case_id="EVAL-020",
        description="Approve — storm damage, fraud=0.07, no injuries (CLM-2024-2895)",
        expected_verdict="Approve",
        expected_model_generated=True,
        claim_id="CLM-2024-2895",
    ),

    EvalCase(
        case_id="EVAL-021",
        description="Approve — low-speed collision, fraud=0.11, no injuries (CLM-2024-3041)",
        expected_verdict="Approve",
        expected_model_generated=True,
        claim_id="CLM-2024-3041",
    ),
]

# ===========================================================================
# Full case list (21 total)
# ===========================================================================

ALL_CASES: list[EvalCase] = (
    _DENY_CASES +
    _FRAUD_CASES +
    _ADJUSTER_CASES +
    _APPROVE_CASES
)

assert len(ALL_CASES) == 21, f"Expected 21 cases, got {len(ALL_CASES)}"
