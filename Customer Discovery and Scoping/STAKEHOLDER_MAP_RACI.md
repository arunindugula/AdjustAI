# Stakeholder Map and RACI

**Date:** 2026-10-10
**Engagement:** ClaimSense Claims Adjudication Co-pilot — Motor Insurer

---

## 1. Stakeholder Map

| Stakeholder | Name | Role | What they care about in this engagement | Influence |
|---|---|---|---|---|
| Claims Director | Dana Whitfield | Engagement sponsor; owns the claims function; accountable for decision quality, cost, and compliance | Whether the co-pilot reduces decision time and adjuster workload without introducing liability or regulatory risk | High |
| CFO | Richard Oyelaran | Financial approver for the engagement; needs a cost ceiling before signing | Whether the pricing model is predictable and the pilot pays back within a measurable timeframe | High |
| Legal & Procurement | Elena Vasquez | Reviews the SoW and data-handling terms; must co-sign before work starts | Whether data handling, IP terms, and AI-disclosure obligations are met | Medium–High |
| CISO | Marcus Chen | Approves the architecture and data-access pattern before any system integration | Whether the co-pilot meets credential, audit trail, and data-handling requirements | High |
| IT / API access owner | Tom Ngata | Provisions AWS account, system credentials, and API specs for CMS, PAS, and Document Store | Whether the integration is maintainable and deployable without bespoke tooling | Medium |
| Senior Licensed Adjuster | Bob Reyes | Reviews and confirms every co-pilot recommendation; labels the evaluation set (2 hrs/week) | Whether the output is readable, well-reasoned, and trustworthy enough to put their name on | High |
| Claims Adjuster | (Daily users) | Front-line workers who use the co-pilot to work through the claims queue | Whether the co-pilot is fast, clear, and reduces the manual work of opening three systems | Medium |
| SIU Lead | (TBC) | Heads the Special Investigations Unit; receives fraud referrals routed by the co-pilot | Whether fraud routing is accurate — false positives waste investigator time; misses cost money | Medium |
| Policy manual owner | Grace Liu | Owns the policy corpus; must freeze the manual for the pilot duration | Whether the corpus is stable and any changes are communicated with enough lead time | Medium |

---

## 2. The Key Roles

**Sponsor and Approver — Dana Whitfield (Claims Director)**
Dana owns the claims function and signs off on production rollout. She is the single person who can say "this goes live" or "this doesn't." Her buy-in on the success criteria at the start is what makes the final evaluation meaningful. If the numbers don't move, rollout doesn't happen.

**Financial Approver — Richard Oyelaran (CFO)**
Richard approves the commercial terms. He needs a cost ceiling before the SoW is signed and wants to understand the break-even case for the pilot in terms of time saved per claim.

**Eval Labeller and Output Reviewer — Bob Reyes (Senior Licensed Adjuster)**
Every recommendation the co-pilot produces is reviewed and confirmed by Bob before it becomes a decision. Bob is legally accountable for every outcome under his licence. He also labels the evaluation set (2 hrs/week) — his labels are the ground truth the system is measured against.

**Daily Users — Claims Adjusters**
The claims adjusters work through the queue using the co-pilot for every first-pass decision. Speed and clarity matter more to this group than to any other — a recommendation that takes three minutes to read is not faster than doing it manually.

**Rollout Blocker — Marcus Chen (CISO)**
Marcus can stop the engagement from going live regardless of what Dana wants. If the integration does not meet credential, audit trail, or data-handling requirements, Marcus will not approve system access. He must be engaged before the architecture is finalised, not after it is built. He reviews the architecture at W2 and the integration at W4.

**Dependency Owner — Tom Ngata (IT)**
Tom provisions the AWS account, API credentials, and CMS/PAS/Document Store API specs. Every milestone that touches a live system depends on Tom having provisioned the access. He is the most time-sensitive dependency in the engagement.

**Corpus Owner — Grace Liu**
Grace owns the policy manual. The retrieval layer is indexed against a fixed corpus; a clause change without notice breaks the citation mapping. Grace must confirm the manual is frozen for the pilot duration, and give at least 2 business days' notice of any change.

---

## 3. RACI Matrix

**Key:** R = Responsible (does the work) · A = Accountable (owns the outcome) · C = Consulted (input required) · I = Informed (kept up to date)

| Activity | Dana Whitfield | Bob Reyes | Adjusters | Marcus Chen | Tom Ngata | Elena Vasquez | Grace Liu | SIU Lead |
|---|---|---|---|---|---|---|---|---|
| Define success criteria | A | C | C | C | I | C | I | C |
| Approve engagement charter and SoW | A | I | I | C | I | A, R | I | I |
| Provision AWS account and API access | I | I | I | C | A, R | I | I | I |
| Freeze policy manual for pilot | I | I | I | I | I | I | A, R | I |
| Label evaluation cases (ground truth) | I | A, R | C | I | I | I | C | C |
| Review architecture (W2, W4) | C | I | I | A, R | C | I | I | I |
| Review co-pilot output per claim | I | A, R | I | I | I | I | I | I |
| Confirm first decision per claim | I | A, R | R | I | I | I | I | I |
| Route SIU referrals | I | C | C | I | I | I | I | A, R |
| Approve production rollout | A | C | C | C | C | C | I | I |
| Escalate a flagged claim manually | I | A, R | R | I | I | I | I | R |

---

## 4. Who Can Block Rollout

**Marcus Chen (CISO)**
The most likely blocker at the technical level. If the integration does not meet credential management standards, data-handling requirements, or audit trail obligations, Marcus will not provision access to the three client systems. No access means no pipeline. He must review the architecture at W2 — not W4 when it is already built.

**Elena Vasquez (Legal & Procurement)**
Several states require insurers to disclose when an AI system assisted in a claims decision. If that disclosure mechanism is not implemented before go-live, Elena can block rollout until it is. She can also raise objections if the model's reasoning is not auditable — a black-box decision that cannot be explained to a regulator is a liability, not a feature.

**Dana Whitfield (Claims Director)**
The sponsor can also be a blocker. If the evaluation results do not meet the agreed success criteria, or if the adjuster confirmation workflow introduces unacceptable liability exposure, Dana will not approve rollout. Quantified success criteria agreed at the start of the engagement are what make the final evaluation objective — they set the bar that both sides have already committed to.
