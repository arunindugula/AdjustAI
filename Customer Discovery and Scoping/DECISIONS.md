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

## ADR-003 — Vector search over the policy corpus rather than full-text keyword search

**Date:** 2026-10-10
**Status:** Decided

**Context:**
Coverage assessment requires the model to read the relevant policy clause and apply it to the claim narrative. The policy corpus contains many clauses; the system must retrieve the right one for each claim without knowing in advance which keyword will appear in both the claim and the clause.

**Decision:**
Policy clauses are indexed as vector embeddings. Retrieval is performed by semantic similarity search against the claim narrative and incident description.

**Reasoning:**
Coverage language and claim language do not share vocabulary. A policy clause might state "the vehicle must be in a roadworthy condition at the time of loss" without using the word "roadworthy" anywhere in the claim. A keyword search finds nothing; a semantic search finds the clause because the meaning is similar even if the words are not. The capstone requires coverage output to cite the clause identifiers actually retrieved — that citation is only meaningful if the retrieval found the right clause, not just a clause containing a matching word.

**Alternatives considered:**
- Full-text keyword search: fast and simple but fails on vocabulary mismatch between policy language and claim language. Too many relevant clauses would be missed.
- Providing the entire policy text to the model as context: removes the retrieval step but exceeds practical context limits for complex policies with many clauses and endorsements. It also prevents citation of specific clause identifiers, which the system requires.

**Consequences:**
The policy corpus must be embedded and indexed before the pipeline runs. The embedding model must be versioned — a change in the embedding model invalidates the existing index and requires a full re-index. Coverage output must include the clause identifier from the retrieved document, not a paraphrase of the clause from model memory.
