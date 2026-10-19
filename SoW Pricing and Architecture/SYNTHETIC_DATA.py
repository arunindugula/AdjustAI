"""
Synthetic Data Utilities — ClaimSense Co-pilot
===============================================
The ClaimsData folder provides the authoritative synthetic dataset for this engagement:

  ClaimsData/data/claimsense_claims.csv    — 20 claims
  ClaimsData/data/claimsense_policies.csv  — 15 policies
  ClaimsData/data/claimsense_documents.csv — 71 document records
  ClaimsData/synthetic_documents/          — PDFs for all claims and policies
  ClaimsData/synthetic_documents/AutoSure_Policy_Manual_CLS-001-012.pdf

mock_api.py reads from these CSVs directly. This file retains only the
utilities that mock_api.py still needs.
"""

from __future__ import annotations
import hashlib


# ---------------------------------------------------------------------------
# Deterministic ID helper
# ---------------------------------------------------------------------------

def _det_id(seed: str, prefix: str, length: int = 8) -> str:
    """Deterministic ID derived from seed — same input always gives same ID."""
    h = hashlib.sha256(seed.encode()).hexdigest()[:length].upper()
    return f"{prefix}{h}"


# ---------------------------------------------------------------------------
# Policy clause text — AutoSure policy manual (CLS-001 through CLS-012)
# ---------------------------------------------------------------------------
# These are the 12 clauses the BM25 search index is built from.
# Clause IDs match the AutoSure_Policy_Manual_CLS-001-012.pdf in
# ClaimsData/synthetic_documents/.
# In M3 this text is replaced by direct PDF extraction from the manual.
# ---------------------------------------------------------------------------

POLICY_CLAUSE_TEXT = """
[CLS-COLL-001] Collision Coverage
The insurer agrees to indemnify the insured for direct and accidental loss to
the insured vehicle caused by collision with another object or by upset,
subject to the collision deductible stated in the Declarations.

[CLS-COLL-002] Collision Exclusions
Collision coverage does not apply to loss caused by wear and tear, mechanical
breakdown, or gradual deterioration. Loss caused intentionally by the insured
is excluded.

[CLS-COMP-003] Comprehensive Coverage
The insurer agrees to indemnify the insured for direct and accidental loss to
the insured vehicle from any cause other than collision, including but not
limited to fire, theft, windstorm, hail, flood, vandalism, and contact with
an animal, subject to the comprehensive deductible stated in the Declarations.

[CLS-COMP-004] Hail and Weather Events
Loss or damage caused directly by hail, windstorm, or flood is covered under
comprehensive coverage provided the loss date falls within the policy period
and premium payments are current as of the loss date.

[CLS-LIAB-005] Third-Party Liability
The insurer will indemnify the insured in respect of legal liability for
bodily injury or property damage caused to a third party by or arising out of
the use of the insured vehicle, up to the limit stated in the Declarations.

[CLS-PER-006] Policy Period — Coverage Window
Coverage applies only to losses occurring on or after the policy period start
date and on or before the policy period end date as stated in the Declarations.
A loss occurring outside this window is not covered regardless of whether the
policy status field reads Active in the insurer's systems.

[CLS-EXCL-007] General Exclusions
This policy does not cover loss or damage arising from: deliberate or wilful
acts by the insured; use of the vehicle in any race, trial, or contest; or
operation of the vehicle by a person not holding a valid driving licence for
the class of vehicle.

[CLS-FRAUD-008] Fraudulent Claims
If the insured makes any claim knowing it to be false or fraudulent in any
respect, the insurer shall have no liability in respect of the claim and may
void the policy from inception.

[CLS-VIN-009] Prior Total-Loss Settlement
Where a vehicle identified by its VIN has been the subject of a prior
total-loss settlement under any policy issued by the insurer, any subsequent
claim relating to the same VIN must be referred to the Special Investigations
Unit prior to any decision being made.

[CLS-DOC-010] Supporting Documentation
The insured shall provide such information and documentation as the insurer
may reasonably require to investigate and assess the claim. Failure to provide
requested documentation within 30 days may result in the claim being closed.

[CLS-MED-011] Medical Payments Coverage
The insurer will pay reasonable medical expenses incurred within three years
of the loss date for bodily injury caused by a covered accident, up to the
medical payments limit stated in the Declarations.

[CLS-PAY-012] Claims Payment
No payment shall be made under this policy without the written confirmation of
a licensed adjuster. The co-pilot's recommendation is a draft for adjuster
review; it does not constitute a payment authorisation.
"""
