# ClaimSense — Engagement Charter

**Date:** 2026-10-10
**Engagement:** Claims Adjudication Co-pilot — Motor Insurer

---

## 1. Problem Statement

A motor insurer's adjusters complete every first-pass claim decision by hand. A single adjuster opens three separate systems — a claims management system, a policy administration system, and a document store — re-keys data between them, reads coverage terms from a PDF, checks a fraud score threshold, and writes a decision whose reasoning is never recorded in a structured form.

The adjuster is the integration layer. The queue waits on one pair of hands, decisions vary between adjusters on identical files, and fraud referral fires on a numeric score rather than a reading of the narrative. When a rule table checks a status field that says "Active" but the loss date falls three days after the policy expired, it approves. A reader catches it. The current system has no reader.

The engagement delivers a co-pilot that reads the complete claim file, checks coverage against the policy clause text, assesses fraud and total-loss exposure, and drafts a first decision with citations — in minutes, with a licensed adjuster confirming every outcome.

The system recommends. It never decides.

---

## 2. The Three Client Systems

### Claims Management System (CMS)

The CMS is the system of record for every claim from first notice of loss through settlement. It holds the claim ID, incident date and description, vehicle information, claimant identity, damage estimate, repair history, claim status, and prior claim history for the same vehicle and policyholder.

The co-pilot reads claim records from the CMS via a read-only API authenticated with a short-lived service token. Once a licensed adjuster confirms the co-pilot's recommendation, the co-pilot writes one structured record back to the CMS: the first-decision output containing the verdict, reasoning summary, and evidence citations. It does not write to any other field. Claim status, payout amounts, and coverage flags remain the responsibility of the CMS and the adjuster.

### Policy Administration System (PAS)

The PAS is the authoritative source for all policy terms, coverage conditions, endorsements, and effective dates. It holds the policy number, named insured, covered vehicles, policy period, coverage types and limits, exclusions, endorsements, and premium payment status.

The co-pilot reads policy records from the PAS via a read-only API. Policy-period validation — whether the loss date falls within the coverage window — and premium-payment status are computed deterministically in code before any model is invoked. The model receives the raw policy clause text so it can read and cite the actual wording; it does not receive pre-computed coverage booleans. The co-pilot never writes to the PAS.

### Document Store

The document store holds all files associated with a claim: police reports, repair estimates, medical records, witness statements, photographs, and prior claim correspondence. Policy clause text is also indexed here as a searchable corpus for retrieval.

The co-pilot retrieves documents by claim ID and performs vector search over the policy clause corpus. Every coverage statement in the output must cite the clause identifiers actually retrieved — the model does not paraphrase policy terms from memory. The co-pilot never writes to the document store.

---

## 3. Integration Map

```
┌─────────────────────┐
│  Claims Management  │──── claim ID, incident data,
│       System        │     damage estimate, claim history ────►┐
└─────────────────────┘                                         │
                                                                │
┌─────────────────────┐                                         ▼
│      Policy         │──── policy clause text,          ┌───────────┐
│  Administration     │     coverage dates, limits ──────►│           │
│       System        │                                   │ Co-pilot  │
└─────────────────────┘                                   │           │
                                                          └─────┬─────┘
┌─────────────────────┐                                         │
│    Document Store   │──── police reports, photos,             │
│  (+ policy corpus)  │     medical records, estimates ────────►│
└─────────────────────┘                                         │
                                                                │ verdict + reasoning
                                                                │ + citations
                                                                │ (post adjuster confirmation)
                                                                ▼
                                                   ┌─────────────────────┐
                                                   │  Claims Management  │
                                                   │       System        │
                                                   └─────────────────────┘
```

**What is deterministic code — never delegated to a model:**
- Identity and access control: who may see this claim
- Policy-period check: does the loss date fall within the coverage window
- Monetary calculations: repair-to-value ratio, coverage limit arithmetic
- Claim deduplication: has this VIN appeared in a prior total-loss settlement

**What is model judgment — always cited:**
- Coverage assessment: does the policy clause respond to this type of loss
- Fraud and risk assessment: is the narrative consistent across all documents
- Injury and total-loss exposure: qualitative reading of the file
- First-decision draft: approve, flag for review, route to SIU, or deny

---

## 4. Scope Boundaries

**In scope:**
- Reading claim, policy, and document data from the three client systems
- Producing a structured first decision with verdict, reasoning, and evidence citations
- A co-pilot UI where the adjuster reads the recommendation and confirms or rejects it
- Writing the confirmed decision record back to the CMS after adjuster confirmation
- Refusing requests from users not entitled to the claim, with refusals recorded in the audit trail
- An audit record for every call — granted or denied — carrying user, action, and resource

**Out of scope:**
- Settlement calculation and payment authorisation — these remain CMS business logic
- Communicating with claimants or third parties — that is the adjuster's responsibility
- Ingesting new documents into the document store — documents are assumed already stored
- Modifying policy records in the PAS — the co-pilot is read-only against the PAS
- The broader adjuster workstation or claims workflow UI — the co-pilot screen is not a replacement for the adjuster's full desktop environment

---

## 5. Fixed Constraints

These constraints are not subject to design. They apply to every decision made across all five milestones.

**1. Deterministic operations are implemented in code.**
Identity, access control, policy dates, and monetary calculations are never delegated to a model. A model cannot decide who may see a claim, whether a loss date falls within a coverage window, or what a repair-to-value ratio is. These are exact computations and must behave exactly.

**2. Every model judgment is cited.**
The co-pilot does not assert coverage or flag fraud from memory. Every judgment names the evidence it relied on — the retrieved clause identifier, the document it read, the field it compared. An output without citations is not a valid output.

**3. Synthetic data only.**
No production data, no personally identifiable information, and no real claim records are introduced at any stage of the engagement — including development, testing, and demonstration. All fixtures are synthetic.
