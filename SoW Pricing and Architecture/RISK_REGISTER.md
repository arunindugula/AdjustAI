# Risk Register

**Date:** 2026-10-17
**Engagement:** ClaimSense Claims Adjudication Co-pilot — Motor Insurer
**Vendor:** AdjustAI
**Document version:** 1.0

---

## Overview

This register records five risks identified at the start of the engagement. Each entry states the risk, its likelihood and impact before mitigation, the mitigation action, and the residual risk that remains after mitigation. The register is a live document and is updated at each milestone if circumstances change.

Likelihood and impact are rated Low / Medium / High. The rating reflects conditions at the time of writing.

---

## R1 — Data-Access and Controls-Review Delay

**Category:** Organisational / Access politics

**Description:**
The client's CISO or security team delays or blocks access to one or more of the three client systems (CMS, PAS, Document Store) pending a controls review. At a regulated insurer, data-access approval typically takes significantly longer than the technical integration work it gates. This is the longest pole in the engagement and the largest driver of schedule risk.

**Likelihood:** High
**Impact:** High

**Mitigation:**
- All development and testing proceeds against synthetic data only, so the pipeline can be built and validated without requiring production system access
- Access requests are initiated at M1 (discovery), not M3 (integration), to maximise lead time
- The engagement charter and SoW explicitly document the three systems and their integration points so the controls review has a complete picture from day one
- The VP of Claims Operations is identified as the internal sponsor who can accelerate approval

**Residual risk:** Medium — synthetic data removes the build dependency, but the live demonstration and final acceptance criteria require real system connectivity. A prolonged controls review could delay M4 and M5.

---

## R2 — Model Accuracy Below Threshold

**Category:** Technical / Model performance

**Description:**
The agent pipeline fails to reach the 92% decision accuracy threshold (AC-1) on the holdout evaluation set. This can occur if the policy corpus retrieval returns the wrong clause, if the model reasons incorrectly from a correctly retrieved clause, or if adversarial cases in the evaluation set expose systematic failure modes.

**Likelihood:** Medium
**Impact:** High

**Mitigation:**
- The initial 20-case evaluation set (M1) is used to validate the pipeline during development, not just at the final gate
- Coverage output must cite the retrieved clause identifier — this makes retrieval failures visible and debuggable before the final evaluation
- Adversarial cases are included in the evaluation set from M1 so failure modes are surfaced early
- The CI evaluation gate blocks image push on a failing build, catching regressions before they reach production

**Residual risk:** Low-Medium — systematic retrieval or reasoning failures are detectable early. The residual risk is concentrated in edge cases not represented in the development evaluation set.

---

## R3 — Legacy System API Instability

**Category:** Technical / Integration

**Description:**
The CMS or PAS exposes undocumented rate limits, inconsistent response schemas, or intermittent availability that causes pipeline failures during integration and testing. Legacy insurance core systems are frequently built on middleware that was not designed for programmatic access at agent throughput.

**Likelihood:** Medium
**Impact:** Medium

**Mitigation:**
- All three client system integrations are built behind an abstraction layer so a schema change or rate limit breach is contained to one adapter, not the whole pipeline
- The pipeline implements exponential backoff and retry on all external API calls
- Typed input and output contracts (M2 deliverable) are agreed with the client before integration begins, creating a shared reference for what the API must return
- Integration is tested against synthetic stubs before live system access is available, so behaviour under failure conditions is understood early

**Residual risk:** Low — the abstraction layer and retry logic contain most failure modes. A hard rate limit below pipeline throughput requirements would require renegotiation with the client's systems team.

---

## R4 — Prompt Injection via Claim Documents

**Category:** Security / Adversarial input

**Description:**
A malicious or malformed document in the claim file — a police report, repair estimate, or witness statement — contains text designed to manipulate agent behaviour, override instructions, or cause the agent to return data outside its intended scope. This is a known attack vector when user-supplied documents are passed directly to a language model.

**Likelihood:** Low
**Impact:** High

**Mitigation:**
- Document content is passed to the model as data, not as part of the system prompt, reducing the surface area for instruction injection
- Input guardrails sanitise document text before it reaches the agent, flagging and quarantining chunks that match injection patterns
- The access control check runs in deterministic code before any agent is invoked — a successful injection cannot bypass the entitlement boundary because that boundary is not controlled by the model
- The evaluation suite (M5) includes a prompt injection adversarial family to verify that the guardrails hold under test conditions

**Residual risk:** Low-Medium — the deterministic access control boundary limits the blast radius of a successful injection. The residual risk is that a novel injection pattern bypasses the input guardrails before the eval suite detects it.

---

## R5 — Scope Creep

**Category:** Commercial / Engagement management

**Description:**
Once the pipeline is working and visible to the client at M3 or M4, the client requests features or integrations outside the scope defined in Section 1 of the SoW — for example, direct claimant communication, settlement calculation, or integration with additional systems. Requests arrive informally and without a change order, creating pressure to absorb them into the existing engagement.

**Likelihood:** Medium
**Impact:** Medium

**Mitigation:**
- The SoW (Section 1) explicitly names what is out of scope, giving both parties a written reference point when a request is evaluated
- The change control clause (Section 5) requires a written change order signed by both parties before any out-of-scope work begins
- The out-of-scope boundary is reviewed with the client at the M2 sign-off so there are no surprises when requests are declined mid-engagement
- The VP of Claims Operations is the named approver for any change order, ensuring informal requests from daily users do not bypass the commercial process

**Residual risk:** Low — the SoW and change control clause contain most scope creep risk. The residual risk is reputational: declining a request the client considers reasonable can damage the relationship even when the refusal is contractually correct.

---

## Summary

| ID | Risk | Likelihood | Impact | Residual |
|---|---|---|---|---|
| R1 | Data-access and controls-review delay | High | High | Medium |
| R2 | Model accuracy below threshold | Medium | High | Low-Medium |
| R3 | Legacy system API instability | Medium | Medium | Low |
| R4 | Prompt injection via claim documents | Low | High | Low-Medium |
| R5 | Scope creep | Medium | Medium | Low |
