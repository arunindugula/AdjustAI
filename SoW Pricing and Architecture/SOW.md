# Statement of Work

**Date:** 2026-10-17
**Engagement:** ClaimSense Claims Adjudication Co-pilot — Motor Insurer
**Vendor:** AdjustAI
**Document version:** 1.0

---

## Section 1 — Scope of Work

### In Scope

The vendor will design, build, and deliver a claims adjudication co-pilot for the client's motor insurance operations. The following are included in this engagement:

- A pipeline that reads claim, policy, and document data from the client's three systems (CMS, PAS, Document Store) and produces a structured first decision with verdict, reasoning, and evidence citations
- A co-pilot UI through which a licensed adjuster reads, confirms, or rejects the recommendation
- A single write-back to the CMS upon adjuster confirmation, recording the verdict, reasoning summary, and evidence citations
- Access control enforced in deterministic code on every route, with refusals logged to the audit trail
- An append-only audit record for every call — granted or denied — carrying user, action, and resource
- A CI pipeline with an evaluation gate that blocks image push on a failing build
- An operational dashboard and runbook sufficient for a first-time operator

### Out of Scope

The following are explicitly excluded and remain the client's responsibility:

- Settlement calculation and payment authorisation
- Claimant or third-party communications
- Ingestion of new documents into the Document Store
- Modifications to policy records in the PAS
- Replacement of the adjuster's full desktop environment or claims workflow UI

---

## Section 2 — Acceptance Criteria

The engagement is complete when all three criteria below pass. Each is verified by the vendor on the final submitted commit in the deployed production environment. Results are included in the handover pack.

**AC-1 Decision Accuracy**
The co-pilot's first decision must match the outcome a panel of senior adjusters would reach on the same file at a rate of ≥ 92%, measured against a holdout evaluation set of 150 cases the system was never tuned against. Cases are labelled by two senior adjusters independently; a third breaks any tie.

**AC-2 Pipeline Latency**
End-to-end time from claim submission to first decision output must satisfy p95 ≤ 90 seconds and p50 ≤ 45 seconds, measured across 500 consecutive pipeline runs against the evaluation set in the production environment. Both thresholds must pass independently.

**AC-3 Fraud Routing Accuracy**
Precision of fraud referral routing must be ≥ 88% and recall ≥ 80%, measured against the SIU Lead's ground-truth labels on the evaluation set. Both thresholds must pass independently.

**AC-4 Coverage Grounding**
Every coverage statement produced by the pipeline must cite a clause identifier retrieved from the policy corpus. Zero citations from model memory are permitted. Verified by scanning all coverage output across the evaluation set; any uncited coverage statement fails the criterion.

**AC-5 Two-User Access Control**
Alice (a claims adjuster) and Bob Reyes (a senior adjuster) both request the same unassigned claim. Alice must receive a 403 Forbidden response. Bob must receive a 200 OK response. Both results are required; either failing the other fails the criterion.

**AC-6 Audit Trail Completeness**
Every data-access call made during the AC-5 test must be logged with user ID, action, resource ID, and result. Zero unlogged calls are permitted. Verified by inspecting the audit log after the AC-5 test run.

**AC-7 Adversarial Safety**
The adversarial slice of the evaluation set covers prompt injection attempts, forced auto-decision attempts, and cross-record leakage attempts. All adversarial cases must pass. Zero false approves are permitted across the full evaluation set. Zero system-initiated claim state changes are permitted — every state change requires adjuster confirmation.

**AC-8 Operability**
An error is injected into the running system during a live drill. The error must be visible on the operational dashboard within 60 seconds. A rollback to the previous image must complete successfully. A written incident report must be filed within 24 hours of the drill.

**AC-9 Handover**
All four procedures in the runbook (add a user, roll back the image, escalate a claim manually, update the policy corpus) must be executed once by client staff during the handover session. Vendor assistance is permitted for guidance but not for execution.

**Warranty — Adjuster Confirmation Rate**
Adjuster confirmation rate (recommendations confirmed without modification) must reach ≥ 85% over the first 30 days of live operation with a minimum of 200 confirmations recorded. This criterion is enforced as a post-handover warranty condition. If the threshold is not met within the warranty period, the vendor commits to one remediation cycle at no additional cost.

---

## Section 3 — Intellectual Property

All custom code, agent definitions, prompt logic, embeddings, and evaluation cases produced during this engagement transfer to the client upon final payment. The client retains full ownership of all source data, including claims records, policy documents, and any embeddings derived from them.

The vendor retains ownership of pre-existing frameworks, tooling, and methodologies that are not specific to this engagement and were not created using the client's data. No pre-existing vendor IP is embedded in the deliverables in a way that would restrict the client's ability to operate, modify, or transfer the system after handover.

---

## Section 4 — Data Handling

All development, testing, and demonstration activity uses synthetic data only. No production data, no real claim records, and no personally identifiable information are introduced at any stage of the engagement.

Synthetic data is stored in the vendor's AWS sandbox account, isolated from any other engagement. Data is retained only for the duration of the engagement. Within 14 days of final handover, the vendor will delete all synthetic data from the sandbox environment and provide written confirmation of deletion to the client.

All model inference is performed on Amazon Bedrock within the AWS environment. No claim data, policy data, or document content — synthetic or otherwise — is transmitted to any external model API. The inference boundary does not leave AWS at any point during the engagement.

The vendor engages the following subprocessors in the delivery of this engagement:

- **Amazon Web Services** — compute, storage, container hosting, and model inference

The vendor will not engage additional subprocessors without 30 days' prior written notice to the client.

---

## Section 5 — Change Control

Any work outside the scope defined in Section 1 constitutes a change. Changes are initiated by written request from either party. The vendor will provide a written estimate of effort, cost, and timeline impact within five business days. Work on a change does not begin until both parties have signed a change order. Approved changes that add scope extend the delivery date by the estimated effort, unless both parties agree otherwise in writing.

---

## Section 6 — Timeline

The engagement runs across five milestones. All deliverables are committed to the capstone repository at the close of each milestone week.

| Milestone | Delivery | Description |
|---|---|---|
| M1 — Discovery and Scoping | Week 1 | Engagement charter, stakeholder map and RACI, success criteria, architectural decisions, initial evaluation cases |
| M2 — Statement of Work, Pricing and Architecture | Week 2 | This document, architecture diagram, pricing model, risk register, typed I/O contracts, synthetic data shapes, cloud account provisioned |
| M3 — Production Agents | Week 3 | Agent pipeline on OpenAI Agents SDK, containerised stack, retrieval over policy corpus, CI evaluation gate |
| M4 — Integration and Access Control | Week 4 | Authentication, access control enforced in code, audit trail, two-user access test |
| M5 — Evaluation, Observability and Handover | Week 5 | 150-case evaluation suite, operational dashboard, incident drill, runbook, client presentation, handover pack |

The warranty period for adjuster confirmation rate (Section 2) begins on the date of go-live following M5 handover and runs for 30 days.
