# Stakeholder Map and RACI

**Date:** 2026-10-10
**Engagement:** ClaimSense Claims Adjudication Co-pilot — Motor Insurer

---

## 1. Stakeholder Map

| Stakeholder | Role | What they care about in this engagement | Influence |
|---|---|---|---|
| VP of Claims Operations | Owns the claims function; accountable for decision quality, cost, and compliance | Whether the co-pilot reduces decision time and adjuster workload without introducing liability or regulatory risk | High |
| Senior Licensed Adjuster | Experienced adjuster who reviews and confirms every co-pilot recommendation; legally accountable for each outcome | Whether the co-pilot output is readable, well-reasoned, and trustworthy enough to put their name on | High |
| Claims Adjuster | Front-line worker who uses the co-pilot daily to work through the claims queue | Whether the co-pilot is fast, clear, and reduces the manual work of opening three systems by hand | Medium |
| IT Security & Compliance | Controls access to client systems and approves data-handling patterns for any new integration | Whether the co-pilot meets security, credential, and audit trail requirements before it touches production data | High |
| Legal / Regulatory Counsel | Advises on compliance obligations for AI-assisted claims decisions | Whether the use of AI in claims adjudication meets state insurance regulations and disclosure requirements | Medium–High |
| SIU Lead | Heads the Special Investigations Unit; receives fraud referrals routed by the co-pilot | Whether fraud routing is accurate — too many false positives waste investigator time; missed cases cost the insurer money | Medium |
| IT / Platform Engineering | Responsible for infrastructure provisioning, system integrations, and ongoing operational support | Whether the co-pilot integration is maintainable, containerised, and deployable without bespoke tooling | Medium |

---

## 2. The Four Key Roles

**Approver — VP of Claims Operations**
The VP of Claims owns the function and signs off on production rollout. They are the single person who can say "this goes live" or "this doesn't." Their approval is required at the end of the engagement, and their buy-in on the success criteria at the start is what makes the final evaluation meaningful. If the numbers don't move, the rollout doesn't happen.

**Reviewer of Co-pilot Output — Senior Licensed Adjuster**
Every recommendation the co-pilot produces is reviewed and confirmed by a Senior Licensed Adjuster before it becomes a decision. This is not a formality — the adjuster is legally accountable for every outcome under their licence. The co-pilot drafts; the adjuster decides. This role is also the primary acceptance tester during UAT: if the output isn't readable and trustworthy enough for a senior adjuster to put their name on, it isn't good enough.

**Daily User — Claims Adjuster**
The Claims Adjuster works through the queue using the co-pilot for every first-pass decision. They are the person whose daily experience determines whether the system gets used or worked around. Speed and clarity matter more to this role than to any other — a recommendation that takes three minutes to read is not faster than doing it manually.

**Rollout Blocker — IT Security & Compliance**
IT Security & Compliance can stop the engagement from going live regardless of what the VP of Claims wants. If the integration does not meet credential, audit trail, or data-handling requirements, access to the three client systems will not be provisioned. Engaging this stakeholder early — before the architecture is fixed — is the most effective way to avoid a late-stage block.

---

## 3. RACI Matrix

**Key:** R = Responsible (does the work) · A = Accountable (owns the outcome) · C = Consulted (input required) · I = Informed (kept up to date)

| Activity | VP of Claims | Senior Adjuster | Claims Adjuster | IT Security | Legal Counsel | SIU Lead |
|---|---|---|---|---|---|---|
| Define success criteria | A | C | C | C | C | C |
| Approve engagement charter and scope | A | C | I | C | C | I |
| Provision system access and credentials | I | I | I | A, R | I | I |
| Label evaluation cases (ground truth) | I | A, R | C | I | I | C |
| Review co-pilot output per claim | I | A, R | I | I | I | I |
| Confirm first decision per claim | I | A, R | R | I | I | I |
| Approve production rollout | A | C | C | C | C | I |
| Escalate a flagged claim manually | I | A, R | R | I | I | R |

---

## 4. Who Can Block Rollout

**IT Security & Compliance**
The most likely blocker at the technical level. If the co-pilot integration does not meet the insurer's credential management standards, data-handling requirements, or audit trail obligations, IT Security will not provision access to the three client systems. No access means no pipeline. This stakeholder must be engaged before the architecture is finalised, not after it is built.

**Legal / Regulatory Counsel**
Several states require insurers to disclose when an AI system assisted in a claims decision. If that disclosure mechanism is not implemented before go-live, Legal can block rollout until it is. Legal can also raise objections if the model's reasoning is not auditable — a black-box decision that cannot be explained to a regulator is a liability, not a feature.

**VP of Claims Operations**
The approver can also be a blocker. If the evaluation results do not meet the agreed success criteria, or if the adjuster confirmation workflow introduces unacceptable liability exposure, the VP will not approve rollout. This is why quantified success criteria agreed at the start of the engagement matter — they set the bar that both sides have already committed to.
