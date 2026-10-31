"""
src/deterministic/checks.py
============================
Pre-agent deterministic checks for the ClaimSense AI adjudication pipeline.

Runs before any agent fires. Responsibilities:

  1. Hard-deny cases no agent should touch (ADR-006, model_generated=False):
       - Liability Only policy + own-vehicle damage claim → DENY
       - Policy not in force on incident date → DENY
       - Repair estimate does not exceed deductible → DENY (net payable = $0)

  2. Deterministic arithmetic the model must never recompute (ADR-005):
       - deductible_usd       — collision or comprehensive deductible from policy
       - net_payable_usd      — repair_estimate minus deductible (floor $0)
       - total_loss_ratio     — repair_estimate / vehicle_acv
       - total_loss_flag      — True when ratio >= TOTAL_LOSS_THRESHOLD (75%)

All agents receive these as trusted numeric inputs and must not recalculate them.
"""

from dataclasses import dataclass
from decimal import Decimal

# ---------------------------------------------------------------------------
# Constants (ADR-005)
# ---------------------------------------------------------------------------

# Industry standard total-loss threshold: repair >= 75% of ACV → total loss
TOTAL_LOSS_THRESHOLD = Decimal("0.75")

# Incident keywords that map to comprehensive coverage (not collision)
_COMPREHENSIVE_KEYWORDS = frozenset({
    "hail", "flood", "fire", "theft", "vandalism", "weather",
    "falling", "animal", "glass", "comprehensive", "lightning",
    "earthquake", "riot",
})


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class CheckResult:
    """
    Output of run_checks(). The pipeline branches on hard_deny before agents.

    hard_deny=True  → emit a DENY decision immediately; do not call any agent.
    hard_deny=False → pass net_payable_usd, total_loss_flag, etc. to Agent 1.
    """

    # Hard-deny outcome
    hard_deny:   bool
    deny_reason: str | None       # human-readable reason; None when hard_deny=False

    # Deterministic arithmetic — agents receive these, never compute them
    net_payable_usd:    Decimal   # repair_estimate − deductible (floor $0)
    deductible_usd:     Decimal   # deductible that applies to this incident
    deductible_applied: str       # "collision" | "comprehensive" | "none"
    total_loss_ratio:   Decimal   # repair_estimate / vehicle_acv
    total_loss_flag:    bool      # True when ratio >= 75%

    # Policy state flags forwarded to agents
    liability_only: bool
    in_force:       bool

    # Deterministic denies are never model-generated (ADR-006)
    model_generated: bool = False


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_checks(claim: dict, policy: dict) -> CheckResult:
    """
    Run all deterministic pre-checks for a claim + policy pair.

    Parameters
    ----------
    claim   DynamoDB claim record from the CMS Lambda
    policy  DynamoDB policy record from the PAS Lambda, with the two computed
            fields the PAS Lambda attaches when incident_date is supplied:
              in_force       (bool) — was the policy active on the incident date?
              liability_only (bool) — is coverage_type "Liability Only"?

    Returns
    -------
    CheckResult
        hard_deny=True  → pipeline must emit DENY without calling any agent
        hard_deny=False → agents may proceed; use the computed arithmetic fields
    """
    liability_only = bool(policy.get("liability_only", False))
    in_force       = bool(policy.get("in_force", True))

    # --- Determine which deductible applies --------------------------------
    incident_type      = str(claim.get("incident_type", "")).lower()
    is_comprehensive   = _is_comprehensive_incident(incident_type)

    if liability_only:
        # Liability Only has no own-vehicle deductibles — moot, claim is denied
        deductible_applied = "none"
        deductible_usd     = Decimal("0")
    elif is_comprehensive:
        deductible_applied = "comprehensive"
        deductible_usd     = _to_decimal(policy.get("comprehensive_deductible_usd", "0"))
    else:
        deductible_applied = "collision"
        deductible_usd     = _to_decimal(policy.get("collision_deductible_usd", "0"))

    # --- Compute net payable and total-loss ratio --------------------------
    repair_estimate = _to_decimal(claim.get("repair_estimate_usd", "0"))
    vehicle_acv     = _to_decimal(policy.get("vehicle_acv_usd", "0"))

    net_payable_usd  = max(repair_estimate - deductible_usd, Decimal("0"))
    total_loss_ratio = (repair_estimate / vehicle_acv) if vehicle_acv > 0 else Decimal("0")
    total_loss_flag  = total_loss_ratio >= TOTAL_LOSS_THRESHOLD

    # --- Hard-deny checks (evaluated in priority order) --------------------

    # 1. Liability Only — own-vehicle damage not covered (ADR-006)
    if liability_only:
        return CheckResult(
            hard_deny=True,
            deny_reason=(
                f"Policy {policy.get('policy_id')} is Liability Only. "
                "Damage to the policyholder's own vehicle is not covered under "
                "this policy type."
            ),
            net_payable_usd=Decimal("0"),
            deductible_usd=Decimal("0"),
            deductible_applied="none",
            total_loss_ratio=total_loss_ratio,
            total_loss_flag=total_loss_flag,
            liability_only=True,
            in_force=in_force,
        )

    # 2. Policy not in force on incident date
    if not in_force:
        return CheckResult(
            hard_deny=True,
            deny_reason=(
                f"Policy {policy.get('policy_id')} was not in force on "
                f"{claim.get('incident_date', 'the incident date')}. "
                f"Policy period: {policy.get('policy_start')} – "
                f"{policy.get('policy_end')} (status: {policy.get('policy_status')})."
            ),
            net_payable_usd=Decimal("0"),
            deductible_usd=deductible_usd,
            deductible_applied=deductible_applied,
            total_loss_ratio=total_loss_ratio,
            total_loss_flag=total_loss_flag,
            liability_only=False,
            in_force=False,
        )

    # 3. Net payable floor — repair doesn't exceed deductible, nothing to pay
    if repair_estimate > 0 and net_payable_usd <= Decimal("0"):
        return CheckResult(
            hard_deny=True,
            deny_reason=(
                f"Repair estimate (${repair_estimate:,.2f}) does not exceed the "
                f"{deductible_applied} deductible (${deductible_usd:,.2f}). "
                "Net payable is $0.00."
            ),
            net_payable_usd=Decimal("0"),
            deductible_usd=deductible_usd,
            deductible_applied=deductible_applied,
            total_loss_ratio=total_loss_ratio,
            total_loss_flag=total_loss_flag,
            liability_only=False,
            in_force=True,
        )

    # --- Pass — agents may proceed with computed arithmetic ----------------
    return CheckResult(
        hard_deny=False,
        deny_reason=None,
        net_payable_usd=net_payable_usd,
        deductible_usd=deductible_usd,
        deductible_applied=deductible_applied,
        total_loss_ratio=total_loss_ratio,
        total_loss_flag=total_loss_flag,
        liability_only=False,
        in_force=True,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_comprehensive_incident(incident_type_lower: str) -> bool:
    """
    Returns True for incidents that fall under comprehensive coverage.
    All others (collision, rear-end, hit-and-run, single-vehicle) → collision.
    """
    return any(kw in incident_type_lower for kw in _COMPREHENSIVE_KEYWORDS)


def _to_decimal(value) -> Decimal:
    """Safely convert a DynamoDB value (Decimal, str, int, float) to Decimal."""
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal("0")
