"""
Synthetic Data Shapes — ClaimSense Co-pilot
============================================
Factories that generate synthetic claim, policy, and document records
conforming to the typed contracts in IO_CONTRACTS.py.

All data is synthetic. No production data, no real claim records, and no
personally identifiable information is used at any stage.

Usage
-----
  from SYNTHETIC_DATA import make_claim, make_policy, make_documents

  # Generate a fixture set for a specific outcome
  claim  = make_claim("CLM-EXPIRE01", outcome="deny", reason="policy_expired")
  policy = make_policy("POL-EXPIRE001", expired=True)
  docs   = make_documents("CLM-EXPIRE01", doc_types=["police_report", "repair_estimate"])

  # Serialise to JSON for the eval suite
  import json
  with open("fixtures/deny_expired.json", "w") as f:
      json.dump({"claim": claim, "policy": policy, "documents": docs}, f, indent=2)

Design notes
------------
- Factories accept a `outcome` hint so eval fixtures are self-documenting.
- All IDs are deterministic from a seed string — the same seed always
  produces the same fixture, so eval cases are reproducible across runs.
- If external synthetic data is provided as part of the project, validate
  it against the IO_CONTRACTS TypedDicts; these factories conform to the
  same shapes and can coexist with externally provided fixtures.
"""

from __future__ import annotations
import hashlib
import json
from datetime import date, timedelta
from pathlib import Path
from typing import Literal

# Import the contracts this data must conform to
from IO_CONTRACTS import (
    CMSClaimRecord,
    PASPolicyRecord, PASCoverageItem,
    ClaimDocument, DocStoreClaimDocResponse,
)

Outcome = Literal["approve", "flag", "siu_route", "deny"]
DenyReason = Literal["policy_expired", "total_loss_vin", "premium_lapsed"]
FlagReason = Literal["estimate_anomaly", "low_confidence_coverage"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _det_id(seed: str, prefix: str, length: int = 8) -> str:
    """Deterministic ID derived from seed — same input always gives same ID."""
    h = hashlib.sha256(seed.encode()).hexdigest()[:length].upper()
    return f"{prefix}{h}"


BASE_DATE = date(2026, 9, 1)   # loss date anchor for all fixtures


# ---------------------------------------------------------------------------
# 1. Claim factory
# ---------------------------------------------------------------------------

def make_claim(
    claim_id: str,
    outcome: Outcome,
    reason: DenyReason | FlagReason | None = None,
) -> CMSClaimRecord:
    """
    Generate a synthetic CMSClaimRecord.

    outcome / reason combinations that exercise each decision path:

      approve          reason=None     — clean claim, active policy, normal estimate
      flag             reason="estimate_anomaly"    — repair estimate 40% above market
      flag             reason="low_confidence_coverage" — ambiguous coverage clause
      siu_route        reason=None     — narrative inconsistency across documents
      deny             reason="policy_expired"  — loss date outside coverage window
      deny             reason="total_loss_vin"  — VIN has prior total-loss settlement
      deny             reason="premium_lapsed"  — policy payment status lapsed
    """
    policy_id = _det_id(claim_id + "policy", "POL-")
    vin       = _det_id(claim_id + "vin",    "VIN-")
    claimant  = _det_id(claim_id + "person", "CLT-")

    # Loss date: default is within policy period
    loss_date = BASE_DATE

    # For policy_expired: push loss date 5 days after policy end
    if reason == "policy_expired":
        loss_date = BASE_DATE + timedelta(days=5)

    # Prior total-loss record on the VIN
    prior_total_loss = reason == "total_loss_vin"

    # Damage estimate: flag cases use an anomalously high estimate
    damage_estimate = 4_200.00    # normal
    if reason == "estimate_anomaly":
        damage_estimate = 18_500.00   # ~340% of market rate for described damage

    return CMSClaimRecord(
        claim_id=claim_id,
        policy_id=policy_id,
        incident_date=loss_date.isoformat(),
        incident_description=_incident_description(outcome, reason),
        vehicle_vin=vin,
        claimant_id=claimant,
        damage_estimate_usd=damage_estimate,
        repair_history=[],
        claim_status="under_review",
        prior_claims_same_vin=(
            [_det_id(claim_id + "prior", "CLM-")] if prior_total_loss else []
        ),
        prior_claims_same_claimant=[],
        total_loss_flag=prior_total_loss,
    )


def _incident_description(outcome: Outcome, reason: DenyReason | FlagReason | None) -> str:
    descriptions = {
        ("approve",    None):                    "Rear-end collision at traffic lights. Third party at fault. Vehicle sustained rear bumper and boot damage. Police report filed.",
        ("flag",       "estimate_anomaly"):      "Minor parking lot scrape on driver-side door. No third party present. Claimant reports scratches and a small dent.",
        ("flag",       "low_confidence_coverage"): "Hail damage to roof and bonnet during severe weather event. Meteorological data available. Coverage depends on endorsement wording.",
        ("siu_route",  None):                    "Vehicle reported stolen from residential address overnight. Owner states no witnesses. GPS telemetry data available for review.",
        ("deny",       "policy_expired"):        "Single-vehicle collision with kerb. Tyre blowout reported as cause. No third parties involved.",
        ("deny",       "total_loss_vin"):        "Flood damage to engine bay following heavy rain. Vehicle submerged for approximately four hours.",
        ("deny",       "premium_lapsed"):        "Rear-end collision on motorway. Third party vehicle involved. Whiplash injury reported by claimant.",
    }
    return descriptions.get((outcome, reason), "Incident description not specified for this outcome/reason combination.")


# ---------------------------------------------------------------------------
# 2. Policy factory
# ---------------------------------------------------------------------------

def make_policy(
    policy_id: str,
    expired: bool = False,
    lapsed: bool = False,
    coverage_types: list[str] | None = None,
) -> PASPolicyRecord:
    """
    Generate a synthetic PASPolicyRecord.

      expired=True  — policy period ends before BASE_DATE (exercises policy-period check)
      lapsed=True   — premium_payment_status is "lapsed" (exercises payment check)
      coverage_types — override default coverage list for specific scenarios
    """
    if coverage_types is None:
        coverage_types = ["comprehensive", "third_party_liability"]

    period_start = date(2025, 9, 1)
    # expired policy ends before the loss date anchor
    period_end = date(2026, 8, 27) if expired else date(2027, 8, 31)

    coverages: list[PASCoverageItem] = [
        PASCoverageItem(
            coverage_type=ct,
            limit_usd=50_000.00,
            deductible_usd=500.00,
            exclusions=["racing", "deliberate_damage", "unlicensed_driver"],
        )
        for ct in coverage_types
    ]

    return PASPolicyRecord(
        policy_id=policy_id,
        named_insured_id=_det_id(policy_id + "insured", "INS-"),
        covered_vins=[_det_id(policy_id + "vin", "VIN-")],
        policy_period_start=period_start.isoformat(),
        policy_period_end=period_end.isoformat(),
        premium_payment_status="lapsed" if lapsed else "current",
        coverages=coverages,
        endorsements=["END-HAIL-001"] if not expired and not lapsed else [],
        clause_text=_policy_clause_text(coverage_types),
    )


def _policy_clause_text(coverage_types: list[str]) -> str:
    """
    Minimal synthetic policy clause text.
    The Coverage Agent reads and cites identifiers from this text.
    Clause IDs follow the pattern SECTION-CLAUSE-SUBCLAUSE.
    """
    return """
POLICY CLAUSE TEXT — SYNTHETIC

[COMP-14.1] Comprehensive Coverage
The insurer agrees to indemnify the insured against accidental loss or damage
to the insured vehicle arising from any cause not otherwise excluded, subject
to the terms, conditions, and exclusions of this policy.

[COMP-14.2] Hail and Weather Events
Loss or damage caused directly by hail, windstorm, or flood is covered under
comprehensive coverage provided the loss date falls within the policy period
defined in the Schedule and premium payments are current as of the loss date.

[COMP-14.3] Policy Period — Coverage Window
Coverage applies only to losses occurring on or after the policy period start
date and on or before the policy period end date as stated in the Schedule.
A loss occurring outside this window is not covered regardless of whether the
policy is otherwise active in the insurer's systems.

[TPL-07.1] Third-Party Liability
The insurer will indemnify the insured in respect of legal liability for
bodily injury or property damage caused to a third party by or arising out of
the use of the insured vehicle, up to the limit stated in the Schedule.

[GEN-02.4] Exclusions — General
This policy does not cover loss or damage arising from: deliberate or wilful
acts by the insured; use of the vehicle in any race, trial, or contest; or
operation of the vehicle by a person not holding a valid driving licence.

[GEN-03.1] Total Loss — Prior Settlement
Where a vehicle identified by its VIN has been the subject of a prior
total-loss settlement under any policy issued by the insurer, any subsequent
claim relating to the same VIN must be referred to the Special Investigations
Unit prior to any decision being made.
"""


# ---------------------------------------------------------------------------
# 3. Document factory
# ---------------------------------------------------------------------------

def make_documents(
    claim_id: str,
    doc_types: list[Literal[
        "police_report", "repair_estimate", "medical_record",
        "witness_statement", "photograph", "prior_correspondence"
    ]] | None = None,
    narrative_consistent: bool = True,
) -> DocStoreClaimDocResponse:
    """
    Generate a synthetic DocStoreClaimDocResponse.

      doc_types           — which document types to include (default: police + estimate)
      narrative_consistent=False — generates contradictory content across documents,
                                   exercising the Risk/Fraud Agent's inconsistency detection
    """
    if doc_types is None:
        doc_types = ["police_report", "repair_estimate"]

    documents: list[ClaimDocument] = []
    for doc_type in doc_types:
        doc_id = _det_id(claim_id + doc_type, "DOC-")
        documents.append(ClaimDocument(
            document_id=doc_id,
            claim_id=claim_id,
            document_type=doc_type,
            content_text=_document_content(doc_type, narrative_consistent),
            uploaded_at="2026-09-03T09:00:00Z",
        ))

    return DocStoreClaimDocResponse(
        claim_id=claim_id,
        documents=documents,
    )


def _document_content(
    doc_type: str,
    consistent: bool,
) -> str:
    consistent_content = {
        "police_report": (
            "SYNTHETIC POLICE REPORT\n"
            "Attending officer: PC synthetic-001\n"
            "Incident location: High Street junction, postcode SY1 1AA\n"
            "Date and time: 2026-09-01 14:32\n"
            "Description: Rear-end collision. Vehicle A (insured) stationary at red "
            "light. Vehicle B struck rear of Vehicle A at low speed. Driver of Vehicle B "
            "accepted responsibility at scene. No injuries reported. Photographs taken."
        ),
        "repair_estimate": (
            "SYNTHETIC REPAIR ESTIMATE\n"
            "Workshop: Approved Panel Repairer No. APR-0042\n"
            "Date: 2026-09-02\n"
            "Described damage: Rear bumper, boot lid, reversing sensors.\n"
            "Parts: £1,850  Labour: £720  Paint: £480  VAT: £610\n"
            "Total estimate: £3,660\n"
            "Note: Estimate within market range for described damage."
        ),
        "witness_statement": (
            "SYNTHETIC WITNESS STATEMENT\n"
            "Witness: synthetic-witness-001\n"
            "Statement: I observed the insured vehicle stationary at the traffic "
            "light on High Street. A second vehicle travelling northbound failed to "
            "stop and collided with the rear of the stationary vehicle. The impact "
            "appeared moderate. Both drivers exchanged details."
        ),
        "photograph": (
            "SYNTHETIC PHOTOGRAPH METADATA\n"
            "File: IMG_SYNTH_001.jpg\n"
            "Timestamp: 2026-09-01 14:45 (14 minutes after reported incident)\n"
            "Location EXIF: 52.7081° N, 2.7549° W (consistent with reported location)\n"
            "Description: Rear bumper damage consistent with rear-end impact."
        ),
        "medical_record": (
            "SYNTHETIC MEDICAL RECORD\n"
            "Patient: CLT-synthetic-001\n"
            "Attending: Dr synthetic-gp\n"
            "Date of attendance: 2026-09-02\n"
            "Presenting complaint: Neck stiffness following road traffic incident on 2026-09-01.\n"
            "Assessment: Mild whiplash. Conservative management advised."
        ),
        "prior_correspondence": (
            "SYNTHETIC PRIOR CORRESPONDENCE\n"
            "Date: 2026-08-15\n"
            "Re: Renewal reminder — Policy POL-synthetic\n"
            "Dear Policyholder, your policy is due for renewal on 2026-08-31."
        ),
    }

    # Inconsistent variants exercise the Risk/Fraud Agent
    inconsistent_overrides = {
        "police_report": (
            "SYNTHETIC POLICE REPORT\n"
            "Attending officer: PC synthetic-001\n"
            "Incident location: High Street junction, postcode SY1 1AA\n"
            "Date and time: 2026-09-01 14:32\n"
            "Description: Rear-end collision reported. However, attending officer "
            "notes that damage pattern on Vehicle A is inconsistent with a rear "
            "impact — damage appears to the front-left quarter panel, not the rear."
        ),
        "repair_estimate": (
            "SYNTHETIC REPAIR ESTIMATE\n"
            "Workshop: Non-panel repairer (not on approved list)\n"
            "Date: 2026-09-02\n"
            "Described damage: Rear bumper, boot lid, reversing sensors.\n"
            "Parts: £7,200  Labour: £4,100  Paint: £2,800  VAT: £2,820\n"
            "Total estimate: £16,920\n"
            "Note: Estimate is approximately 362% of market rate for described damage. "
            "Workshop not on approved panel."
        ),
        "photograph": (
            "SYNTHETIC PHOTOGRAPH METADATA\n"
            "File: IMG_SYNTH_001.jpg\n"
            "Timestamp: 2026-09-01 14:45\n"
            "Location EXIF: 52.8034° N, 2.1122° W (does NOT match reported incident location)\n"
            "Description: Damage visible on front-left quarter panel. Inconsistent "
            "with rear-end impact described in police report."
        ),
    }

    if not consistent and doc_type in inconsistent_overrides:
        return inconsistent_overrides[doc_type]
    return consistent_content.get(doc_type, f"SYNTHETIC DOCUMENT — type: {doc_type}")


# ---------------------------------------------------------------------------
# Fixture set builder — serialises to JSON for the eval suite
# ---------------------------------------------------------------------------

FIXTURE_SPECS: list[dict] = [
    # Approve cases
    {"claim_id": "CLM-APPROVE1", "outcome": "approve",   "reason": None,                    "expired": False, "lapsed": False, "consistent": True,  "docs": ["police_report", "repair_estimate", "witness_statement"]},
    {"claim_id": "CLM-APPROVE2", "outcome": "approve",   "reason": None,                    "expired": False, "lapsed": False, "consistent": True,  "docs": ["police_report", "repair_estimate", "photograph"]},
    # Flag cases
    {"claim_id": "CLM-FLAG001",  "outcome": "flag",      "reason": "estimate_anomaly",       "expired": False, "lapsed": False, "consistent": True,  "docs": ["repair_estimate"]},
    {"claim_id": "CLM-FLAG002",  "outcome": "flag",      "reason": "low_confidence_coverage","expired": False, "lapsed": False, "consistent": True,  "docs": ["police_report", "repair_estimate"]},
    # SIU route cases
    {"claim_id": "CLM-SIU0001",  "outcome": "siu_route", "reason": None,                    "expired": False, "lapsed": False, "consistent": False, "docs": ["police_report", "repair_estimate", "photograph"]},
    {"claim_id": "CLM-SIU0002",  "outcome": "siu_route", "reason": None,                    "expired": False, "lapsed": False, "consistent": False, "docs": ["police_report", "witness_statement", "photograph"]},
    # Deny cases
    {"claim_id": "CLM-DENY001",  "outcome": "deny",      "reason": "policy_expired",         "expired": True,  "lapsed": False, "consistent": True,  "docs": ["police_report", "repair_estimate"]},
    {"claim_id": "CLM-DENY002",  "outcome": "deny",      "reason": "total_loss_vin",          "expired": False, "lapsed": False, "consistent": True,  "docs": ["police_report", "repair_estimate"]},
    {"claim_id": "CLM-DENY003",  "outcome": "deny",      "reason": "premium_lapsed",          "expired": False, "lapsed": True,  "consistent": True,  "docs": ["police_report", "repair_estimate"]},
]


def build_fixtures(output_dir: str = "fixtures") -> None:
    """
    Generate all fixture sets and write them to output_dir as JSON files.
    Each file is named {claim_id}.json and contains claim, policy, and documents.

    Run this once before M3 development to populate the test fixture directory.
    If external synthetic data is provided, place it in the same directory
    using the same schema — the pipeline loads fixtures by claim_id regardless
    of how they were generated.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    for spec in FIXTURE_SPECS:
        claim_id = spec["claim_id"]
        policy_id = _det_id(claim_id + "policy", "POL-")

        claim  = make_claim(claim_id, spec["outcome"], spec["reason"])
        policy = make_policy(policy_id, expired=spec["expired"], lapsed=spec["lapsed"])
        docs   = make_documents(claim_id, spec["docs"], narrative_consistent=spec["consistent"])

        fixture = {
            "claim_id":       claim_id,
            "expected_outcome": spec["outcome"],
            "deny_reason":    spec.get("reason"),
            "claim":          claim,
            "policy":         policy,
            "documents":      docs,
        }

        filepath = out / f"{claim_id}.json"
        with open(filepath, "w") as f:
            json.dump(fixture, f, indent=2)

        print(f"  wrote {filepath}")

    print(f"\n{len(FIXTURE_SPECS)} fixtures written to {output_dir}/")


if __name__ == "__main__":
    build_fixtures()
