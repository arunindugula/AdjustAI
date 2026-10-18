# Pricing Model

**Date:** 2026-10-17
**Engagement:** ClaimSense Claims Adjudication Co-pilot — Motor Insurer
**Vendor:** AdjustAI
**Document version:** 1.0

---

## Overview

This engagement is priced on a **fixed-price floor with an outcome bonus**. The fixed floor gives the client a cost ceiling for procurement sign-off. The outcome bonus aligns vendor incentives with client business value after go-live.

This model follows the principle that the early deal must survive the data-access and controls-review gate before expansion economics apply. The fixed floor is priced to survive that gate; the bonus is where the commercial upside lives once the system is in production.

---

## Assumptions

All pricing derives from the following stated assumptions. A change to any assumption changes the number.

| Assumption | Value | Basis |
|---|---|---|
| Blended day rate | $2,000/day | Fully-loaded engineer cost of ~$900/day at 2.2× margin |
| Fixed overhead | $12,000 | Tooling, AWS sandbox, eval-set authoring, project management |
| Working days per year | 220 | Standard, excluding public holidays and leave |
| Risk buffer — low risk | 1.10× | Well-understood work with no system dependencies |
| Risk buffer — integration risk | 1.35× | Legacy systems, rate limits, undocumented APIs |
| Risk buffer — access politics | 1.80× | Controls-review gate; data-access approval at a regulated client |

---

## Milestone Sizing

T-shirt sizes convert to day ranges. The risk buffer is applied per milestone based on its dominant risk class. The buffered high is the number used to set the fixed-price floor.

| Milestone | Size | Raw range (days) | Risk class | Buffer | Buffered high |
|---|---|---|---|---|---|
| M1 — Discovery and Scoping | S | 3–5 | Low | 1.10× | 5.5 |
| M2 — SoW, Pricing and Architecture | S | 3–5 | Low | 1.10× | 5.5 |
| M3 — Production Agents | L | 15–25 | Access politics | 1.80× | 45 |
| M4 — Integration and Access Control | M | 8–12 | Integration | 1.35× | 16 |
| M5 — Evaluation and Handover | L | 15–25 | Access politics | 1.80× | 45 |

**Total buffered days (high): 117 days**
**Total expected days (midpoints): 65 days**

---

## Engagement Cost

| Scenario | Engineering days | Day rate | Engineering cost | Overhead | **Total** |
|---|---|---|---|---|---|
| Low | 44 | $2,000 | $88,000 | $12,000 | **$100,000** |
| Expected | 65 | $2,000 | $130,000 | $12,000 | **$142,000** |
| High (buffered) | 117 | $2,000 | $234,000 | $12,000 | **$246,000** |

---

## Fixed-Price Floor

The fixed-price floor is set at the expected total: **$142,000**.

This is the amount invoiced regardless of actual days spent, provided the scope in Section 1 of the SoW is delivered and all three acceptance criteria pass. The floor protects the client from cost overrun up to the expected scenario; the vendor absorbs delivery risk above the expected and below the buffered high.

**Payment schedule:**

| Milestone | Amount | Trigger |
|---|---|---|
| M2 — SoW and Architecture signed off | $28,400 (20%) | Both parties sign this document |
| M3 — Production agents delivered | $42,600 (30%) | Agent pipeline passes CI evaluation gate |
| M4 — Integration and access control delivered | $28,400 (20%) | Two-user access test passes |
| M5 — Final handover | $42,600 (30%) | All three acceptance criteria pass |

---

## Outcome Bonus

The outcome bonus applies post-handover once the system is in live operation. It is not part of the fixed-price floor and does not affect the acceptance criteria or the engagement timeline.

**Trigger:** ≥ 500 adjuster-confirmed claims processed by the co-pilot in a calendar month.

**Rate:** $5 per confirmed claim above the 500-claim threshold.

**Cap:** $25,000 per calendar month.

**Measurement:** Confirmed claim count is drawn from the audit trail. A confirmed claim is one where the adjuster confirmed the co-pilot recommendation without modification.

| Monthly confirmed claims | Bonus payable |
|---|---|
| < 500 | $0 |
| 1,000 | $2,500 |
| 3,000 | $12,500 |
| 5,500+ | $25,000 (cap) |

The outcome bonus is invoiced monthly in arrears. Either party may terminate the bonus arrangement with 30 days' written notice without affecting the fixed-price floor or the warranty obligations.

---

## Pricing Model Selection — Rationale

Three models were evaluated:

| Model | Considered | Rejected because |
|---|---|---|
| T&M with a cap | Yes | Shifts too much risk to the client; procurement at a regulated insurer prefers a fixed ceiling |
| Fixed-price only | Yes | No alignment incentive post-handover; vendor has no stake in adoption |
| Outcome-based only | Yes | Too much variance for a first pilot; access-politics risk means early revenue is unpredictable |
| **Fixed floor + outcome bonus** | **Selected** | Fixed floor survives procurement; bonus aligns vendor with client value post-handover |

The access-politics risk (1.80× buffer on M3 and M5) is the largest single driver of the high-end estimate. This reflects the reality that data-access approval at a regulated insurer typically takes 8–12 weeks per week of value delivery. The fixed floor is priced to absorb this risk; the outcome bonus is where economics improve once access is established.
