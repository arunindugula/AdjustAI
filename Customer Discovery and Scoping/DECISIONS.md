# Architectural Decision Records

This file is opened at Milestone 1 and updated throughout the engagement. Each entry records a significant design decision, the reasoning behind it, the alternatives considered, and the consequences it commits the system to.

---

## ADR-001 — Access control implemented in deterministic code, not a model instruction

**Date:** 2026-10-10
**Status:** Decided

**Context:**
The co-pilot serves multiple adjusters, each entitled to see only the claims assigned to them. A user not entitled to a claim must receive a refusal with no claim data returned. The system needs a mechanism to enforce this boundary on every request.

**Decision:**
Access control is implemented as deterministic code that runs before any agent is invoked. A request is checked against the entitlement store; if the user is not entitled to the claim, the request is refused and the refusal is written to the audit trail. No agent receives the claim data.

**Reasoning:**
The alternative was a prompt instruction — telling the model to only return data for claims the user is entitled to. That approach is unsafe. A model instruction can be overridden by a sufficiently crafted user input; a code check cannot. In a regulated environment where a data leak carries legal consequences, the trust boundary must be enforced by something that cannot be prompted around. Code is exact and testable; a model instruction is neither.

**Alternatives considered:**
- Model instruction: "Only return claim data if the requesting user is entitled to this claim." Rejected — model instructions are not a security boundary. They can be circumvented through prompt injection or adversarial inputs.
- Middleware firewall on the API gateway: viable but moves the enforcement further from the data, creating a gap if the agent is ever called directly. Deterministic code co-located with the agent invocation is the tightest boundary.

**Consequences:**
Every route in the system must call the access control check before invoking any agent. This must be tested explicitly with a two-user test — one entitled, one not — on the same claim. A route that bypasses the check is a security defect, not a missing feature.

---

## ADR-002 — OpenAI Agents SDK over a custom orchestration layer

**Date:** 2026-10-10
**Status:** Decided

**Context:**
The co-pilot requires multiple agents working in sequence: one to gather the file, one to check coverage, one to assess risk, and one to draft the decision. These agents need to hand off structured data between them, call tools deterministically, and produce typed outputs that distinguish model judgment from deterministic computation.

**Decision:**
The agent pipeline is built on the OpenAI Agents SDK rather than a hand-rolled orchestration layer.

**Reasoning:**
The SDK provides three things that would otherwise require significant engineering effort: typed tool definitions that enforce output structure, a built-in handoff mechanism between agents, and tracing that records what each agent did and why. The capstone rubric specifically requires that model-generated verdicts be distinguishable from deterministic fallback output — the SDK's structured output support makes this straightforward. Building a custom orchestration layer would replicate this infrastructure without improving it.

**Alternatives considered:**
- Custom agent loop with raw API calls: gives maximum flexibility but requires building output validation, handoff logic, and tracing from scratch. The engineering cost is high and the risk of subtle bugs in the orchestration layer is significant.
- LangChain: mature but adds a large abstraction layer between the code and the model. Debugging failures in a LangChain chain is harder than debugging failures in code that calls the SDK directly.

**Consequences:**
All agents must use the SDK's typed output mechanism. Outputs that bypass typing — free-form strings passed between agents — are not permitted. The evaluation gate must verify that outputs carry the correct structure before the image is pushed.

---

## ADR-003 — BM25 lexical retrieval over the policy corpus for the pilot; vector search deferred

**Date:** 2026-10-10
**Status:** Decided

**Context:**
Coverage assessment requires the model to read the relevant policy clause and apply it to the claim narrative. The pilot policy corpus is the AutoSure policy manual: 12 clauses with exact, stable clause IDs (`CLS-COLL-001` through `CLS-PAY-012`). The system must retrieve the right clause for each claim and cite its ID in every coverage statement.

**Decision:**
Retrieval is implemented as BM25 lexical (keyword) search over the 12-clause corpus. Vector (embedding) search is deferred until the corpus grows to approximately 140 clauses or until lexical retrieval demonstrably fails on a class of claims.

**Reasoning:**
With 12 clauses and exact clause IDs, lexical retrieval is precise and fully explainable — the retrieved clause ID is deterministic for a given query. Embedding-based retrieval adds an opaque similarity step, a versioned index that must be rebuilt on model change, and latency overhead, without improving recall at this corpus size. The decision defers that complexity until it earns its place. The key invariant that both approaches must satisfy is that coverage output cites a retrieved clause ID and never paraphrases a clause from model memory.

**Alternatives considered:**
- Vector (embedding) search: appropriate at larger corpus scale where vocabulary mismatch between claim language and policy language becomes a problem. Deferred to ~140 clauses — revisit trigger documented as DEC-011.
- Full policy text in context window: removes the retrieval step entirely. Works at 12 clauses but breaks as the corpus grows, and eliminates the ability to cite specific clause IDs.

**Consequences:**
The policy corpus must be loaded and indexed as BM25 before the pipeline runs. Coverage output must cite the clause identifier from the retrieved document, not a paraphrase from model memory. A validator enforces this at output — a coverage statement without a retrieved clause ID is rejected before the adjuster sees it. Vector search is the expected upgrade path once the corpus exceeds pilot scale.

---

## ADR-004 — No write path in the pilot

**Date:** 2026-10-10
**Status:** Decided

**Context:**
The co-pilot reads from three client systems (CMS, PAS, Document Store) and produces a recommendation. A write-back to the CMS to record the confirmed decision was considered as part of the pilot scope.

**Decision:**
The pilot has no write tools. Every integration with a client system is read-only. The adjuster confirms the recommendation through the co-pilot UI, but the write to the CMS is the adjuster's own action in their existing system — the co-pilot does not perform it.

**Reasoning:**
A write integration requires a separate security review, a different set of IAM permissions, and a higher bar for the data-handling assessment. Adding writes to the pilot scope doubles the surface area Marcus Chen (CISO) must approve and increases the risk of a late-stage access block. The pilot's goal is to demonstrate decision quality and time saving; that goal does not require the co-pilot to write anything. Writes are the right scope for the production phase once the pilot has passed its acceptance criteria.

**Alternatives considered:**
- CMS write-back on adjuster confirmation: cleaner audit trail, but adds write permissions, rollback procedures, and idempotency requirements to the pilot scope. Deferred to production.

**Consequences:**
The MCP integration layer exposes read-only tools only. Any request to add a write tool goes through change control. The adjuster confirmation is recorded in the co-pilot's own audit log; the authoritative CMS record is the adjuster's own entry.

---

## ADR-005 — Deterministic code owns all arithmetic; the model never produces a dollar figure

**Date:** 2026-10-10
**Status:** Decided

**Context:**
The pipeline must compute the net payable amount (repair estimate minus deductible, capped at ACV) and the total-loss ratio (repair estimate divided by ACV) as part of the coverage assessment. These figures appear on the adjuster card and are referenced in the decision draft.

**Decision:**
Net payable and total-loss ratio are computed in deterministic Python before any agent runs. The computed figures are passed into the agent context as inputs. The model reads them and cites them; it does not calculate them.

**Reasoning:**
A model asked to compute `max(min(estimate, ACV) − deductible, 0)` will produce the right answer most of the time and a wrong answer some of the time — including on adversarial cases designed to surface arithmetic failures. A wrong figure on an adjuster card is a claims payment error, which carries financial and regulatory consequences. Deterministic code is exact, testable, and auditable in a way that model arithmetic is not. The W1 dry run demonstrated a $4,600 error when the formula was computed inside the Coverage Check agent.

**Alternatives considered:**
- Model computes the figures: simpler pipeline, but introduces non-determinism into a calculation that is contractually defined and must be exact.

**Consequences:**
The deterministic layer runs before any agent. Its outputs (net payable, TL ratio, in-force status, deductible by loss type) are passed to agents as read-only context. An output validator rejects any dollar figure in agent output that is not present in the dossier — this catches cases where the model invents a number rather than citing the one it was given.

---

## ADR-006 — Liability-only policy with a first-party claim routes to deny as a deterministic pre-check

**Date:** 2026-10-10
**Status:** Decided

**Context:**
Some policyholders carry liability-only coverage (no collision, no comprehensive). If a first-party collision or comprehensive claim is filed against a liability-only policy, the claim cannot be paid. This is a deterministic fact — it does not require model judgment to establish.

**Decision:**
Coverage type is checked in deterministic code as part of the pre-check layer. A first-party claim against a liability-only policy produces a `deny` recommendation without invoking any agent. The recommendation is labelled as a deterministic result and routed to a senior adjuster for confirmation — it is never auto-approved or auto-denied.

**Reasoning:**
Sending this case to the Coverage Check agent adds latency and model cost for a result that is computable from two fields in the policy record. More importantly, an agent could be prompted to reason around this constraint; a code check cannot. The deny is always a recommendation — the adjuster confirms it — consistent with the principle that no co-pilot output authorises a payment.

**Alternatives considered:**
- Let the Coverage Check agent handle it: the agent would likely reach the correct deny, but via model reasoning rather than a guaranteed code path. The deterministic route is cheaper, faster, and not subject to adversarial override.

**Consequences:**
The pre-check layer must read the coverage type from the PAS before invoking any agent. Liability-only deny cases must be represented in the evaluation set. The eval gate must verify these cases return `deny` with `model_generated: false` and `deterministic_checks_passed: true`.

---

## ADR-007 — No production data until a Data Processing Agreement is signed

**Date:** 2026-10-10
**Status:** Decided

**Context:**
The engagement requires claim, policy, and document data to build and test the pipeline. The client holds real policyholder data that would be the natural input for development.

**Decision:**
All development, testing, and demonstration activity uses the de-identified 20-claim export and the synthetic document set only. No production data — no real claim records, no PII — is introduced at any stage of the engagement. A transition to production data requires a signed Data Processing Agreement (DPA) and a Security review of the production data-handling architecture. Neither is in scope for the pilot.

**Reasoning:**
A regulated insurer's customer data carries legal obligations under state insurance law and applicable data-protection regulation. Processing it without a signed DPA creates regulatory exposure for both parties. The de-identified export is sufficient to build and validate the pipeline — the production data transition is a decision for the production phase.

**Alternatives considered:**
- Use anonymised production data under a verbal agreement: rejected — verbal agreements do not satisfy regulatory requirements at a regulated insurer.

**Consequences:**
The mock systems serve the de-identified export in the production data shape. When real CMS and PAS APIs replace the mocks, the contract shape stays the same and only the adapter changes. The DPA is a prerequisite for any production rollout, independent of the pilot's acceptance criteria.
