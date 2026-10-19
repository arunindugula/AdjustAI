# Risk Register

**Date:** 2026-10-18
**Engagement:** ClaimSense Claims Adjudication Co-pilot — Motor Insurer
**Vendor:** AdjustAI
**Document version:** 2.0

---

## Overview

This register records the top five risks to the engagement. Risks are scored on likelihood (L) and impact (I) on a 1–5 scale. Score = L × I. Any risk scoring 12 or above is reviewed at every weekly gate.

The register leads with **runtime and safety risks** — the failure modes that cause real harm once the system is in operation — followed by a watch list of delivery risks that are tracked but do not currently score in the top five.

Residual is the expected score after mitigation. A risk only moves to its residual score once its corresponding evaluation slice passes in CI.

---

## R1 — Model Hallucination

**Category:** Technical / Model safety

**Likelihood:** 4  **Impact:** 4  **Score:** 16

**Description:**
The adjuster card states a fact, figure, or document reference that is not in the claim file. The model invents a dollar amount, a clause it never retrieved, or a document ID that does not exist. On an adjuster card this is not a reasoning error — it is misinformation in a regulated decision.

**Mitigation:**
- Net payable, total-loss ratio, deductible, and in-force status are computed in deterministic Python before any agent runs and passed into the agent context as inputs (ADR-005). The model cites them; it does not compute them.
- An output validator rejects any dollar figure in agent output that is not present in the dossier, and any document ID not in the claim's document inventory.
- Structured output is enforced for each agent stage — free-form text that bypasses the schema is not accepted.
- If the model is unreachable, the card shows the deterministic baseline code labelled `engine: rules`, not a model-generated result.
- The evaluation set includes "invented figure" and "phantom document" adversarial cases. The CI gate blocks image push if any of these pass through.

**Early warning:** Output validator rejection rate > 2% of runs in CI.

**Residual:** 2 × 4 = 8

---

## R2 — Coverage Misread

**Category:** Technical / Model accuracy

**Likelihood:** 3  **Impact:** 5  **Score:** 15

**Description:**
A wrongful denial (litigation exposure) or wrongful approval (financial leakage). Concrete examples: approving a claim against a policy whose status field reads "Active" but whose loss date falls outside the coverage window; approving a first-party collision claim on a liability-only policy; citing a clause that does not apply to the loss type.

**Mitigation:**
- The in-force check runs on dates, not on the status field — the policy-period clause (CLS-PER-006) is the authority, not the CMS status string (ADR-003, W1 Finding 1).
- Liability-only policies with first-party claims are caught in the deterministic pre-check layer and routed to deny before any agent runs (ADR-006).
- Coverage Check must cite a retrieved clause ID for every coverage statement; the output validator enforces this. A coverage statement without a citation is rejected (AC-4).
- Zero false approves is a release gate condition (AC-7). Any false approve in CI fails the build.

**Early warning:** Any false approve in CI; citation coverage < 100%.

**Residual:** 1 × 5 = 5

---

## R3 — Auth Failure

**Category:** Security / Access control

**Likelihood:** 3  **Impact:** 5  **Score:** 15

**Description:**
An adjuster reads a claim not assigned to them — through the console, by prompting the model, or through a misconfigured data-access call. At a regulated insurer, an unauthorised read of a claim record is a data breach, not a UX bug.

**Mitigation:**
- Access control runs in deterministic code before any agent is invoked (ADR-001). The model never makes access decisions.
- The identity of the requesting user is derived from the verified JWT — it never comes from the request payload. A prompt saying "I am the senior adjuster" has nowhere to go.
- Every data-access call is audited, whether allowed or denied, with user ID, action, resource ID, and result (AC-6).
- The two-user RBAC test (AC-5) is a release gate: Alice (adjuster) must receive 403 on Bob's claim; Bob (senior) must receive 200.
- Adversarial eval cases include "act as senior adjuster" and cross-record leakage attempts (AC-7).

**Early warning:** Any 200 response for a cross-assignment read in the AC-5 matrix test.

**Residual:** 1 × 5 = 5

---

## R4 — Data Leak

**Category:** Security / Data handling

**Likelihood:** 2  **Impact:** 5  **Score:** 10

**Description:**
Claimant data reaches the model vendor, an application log, another user's session, or a CI artifact. This covers PII in model inputs, holder names in audit logs, and JWT secrets in image layers or CI environment variables.

**Mitigation:**
- The de-identified 20-claim export is used for all development and testing. No production data, no real PII is introduced before a Data Processing Agreement is signed (ADR-007).
- The policy holder's name is dropped by the data contract before any model call — it is never sent to the inference layer.
- The dossier passed to agents carries one claim only; nothing crosses records.
- Audit logs record IDs and actions, not content.
- Secrets are kept in AWS SSM Parameter Store as SecureString. No credential is in code, images, or CI logs.
- CI and CloudWatch logs are scanned for holder-name patterns at every gate.

**Early warning:** Grep of CI or CloudWatch logs finds a holder name or JWT token.

**Residual:** 1 × 5 = 5

---

## R5 — Scope Creep

**Category:** Commercial / Engagement management

**Likelihood:** 4  **Impact:** 3  **Score:** 12

**Description:**
Once the pipeline is visible at W3 or W4, the client requests features outside the scope defined in Section 1 of the SoW — auto-approval, write-back to CMS, rental adjudication, or production data access within the five weeks. Requests arrive informally and without a change order.

**Mitigation:**
- Section 3 of the SoW explicitly names every exclusion, giving both parties a written reference when a request is evaluated.
- Section 8 (Change Control) requires a written impact assessment and sponsor sign-off before any out-of-scope work begins.
- ADR-004 (no write path) documents the reasoning for one of the most likely creep vectors, so "not now" comes with a documented rationale.
- Every gate opens by reading SoW Section 2 aloud. Any new item that is not on the list triggers a formal change request.

**Early warning:** Any request that starts with "while you're in there…" or names a deliverable not in SoW Section 2.

**Residual:** 2 × 3 = 6

---

## Watch List — Delivery Risks

These risks are tracked but currently score below the top five. They are reviewed at each gate and promoted if their score rises.

| ID | Risk | L × I | Mitigation summary |
|---|---|---|---|
| W1 | Data-access and controls-review delay (CISO gate) | 4 × 4 = 16 | All development proceeds against the de-identified export; access requests initiated at W1 to maximise lead time; Marcus Chen identified as reviewer |
| W2 | Legacy API instability — undocumented rate limits or schema changes | 3 × 3 = 9 | Abstraction layer behind each adapter; retry with exponential backoff; typed contracts agreed before integration begins |
| W3 | OCR backlog — repair estimates remain Pending; cards cannot be completed | 3 × 2 = 6 | Card names the specific pending document and why it matters; Tom Ngata to report the OCR queue SLA |
| W4 | Latency misses p95 < 90 s with four sequential agent calls | 3 × 2 = 6 | Measure at W3; if missed, run Coverage Check and Claim Assessment in parallel (both depend only on Document Intake output) |
| W5 | Label disagreement — Bob Reyes and Grace Liu reach different verdicts on a deny case | 2 × 3 = 6 | Disagreement resolved by Bob and logged in DECISIONS.md; Grace consulted on coverage-denial cases |

---

## Summary

| ID | Risk | L | I | Score | Residual |
|---|---|---|---|---|---|
| R1 | Model hallucination | 4 | 4 | 16 | 8 |
| R2 | Coverage misread — wrongful denial or approval | 3 | 5 | 15 | 5 |
| R3 | Auth failure — adjuster reads wrong claim | 3 | 5 | 15 | 5 |
| R4 | Data leak to vendor, log, or other session | 2 | 5 | 10 | 5 |
| R5 | Scope creep | 4 | 3 | 12 | 6 |
