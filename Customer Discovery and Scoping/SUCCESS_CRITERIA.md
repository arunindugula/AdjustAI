# Success Criteria

**Date:** 2026-10-10
**Engagement:** ClaimSense Claims Adjudication Co-pilot — Motor Insurer

---

## Overview

Four quantified success criteria are defined below. Each criterion names the metric, the threshold that passes or fails, and the method by which it will be measured. These criteria were set at the start of the engagement so that both parties have agreed on the bar before the system is built.

A number without a measurement method is an assertion, not a criterion. All four below are verifiable independently.

---

## 1. Decision Accuracy

**Metric:** Percentage of co-pilot first decisions that match the outcome a panel of senior adjusters would reach on the same file.

**Threshold:** ≥ 92% agreement on a holdout evaluation set.

**Measurement method:** A set of 150 evaluation cases — claims the system was never tuned against — is labelled by a panel of two senior adjusters working independently. Where the two adjusters disagree, a third adjuster breaks the tie. The co-pilot's verdict on each case is compared against the panel label. Agreement rate must reach 92% for this criterion to pass.

**Assumption:** Motor insurer adjusters working manually reach consistent decisions on approximately 80–85% of straightforward claims. 92% represents a meaningful and measurable improvement over that baseline, not a marginal one.

---

## 2. Pipeline Latency

**Metric:** End-to-end time from claim submission to first decision output delivered to the adjuster UI.

**Threshold:** p95 ≤ 90 seconds · p50 ≤ 45 seconds.

**Measurement method:** Latency is measured across 500 consecutive pipeline runs against the evaluation set in the production environment. p50 and p95 are calculated from the recorded timestamps. Both thresholds must pass independently.

**Assumption:** A manual first-pass decision currently takes 45–90 minutes. The co-pilot is not useful if it takes longer than a short conversation — 90 seconds at the 95th percentile is the threshold below which the time saving becomes operationally significant. An adjuster waiting more than 90 seconds on a single claim will route around the tool.

---

## 3. Adjuster Confirmation Rate

**Metric:** Percentage of co-pilot recommendations confirmed by the reviewing adjuster without modification.

**Threshold:** ≥ 85% over the first 30 days of live operation.

**Measurement method:** Confirmation events are recorded in the audit trail. Each event is tagged as confirmed-as-is or modified-before-confirmation. The rate is calculated as confirmed-as-is divided by total confirmations over the 30-day window. A minimum of 200 confirmations must be recorded before the rate is considered stable.

**Assumption:** An 85% confirmation rate indicates the output is genuinely trusted and useful. Below 70%, adjusters are effectively rewriting the recommendation on most claims — the co-pilot is providing a starting point, not a decision draft. The 30-day window and 200-confirmation minimum guard against a small early sample distorting the result.

---

## 4. Fraud Routing Accuracy

**Metric:** Precision and recall of the co-pilot's fraud referral routing against expert-labelled ground truth.

**Threshold:** Precision ≥ 88% · Recall ≥ 80%.

**Measurement method:** The 150-case evaluation set includes a representative proportion of fraud cases, labelled by the SIU Lead as ground truth. Precision is calculated as true fraud referrals divided by all referrals made. Recall is calculated as true fraud referrals divided by all actual fraud cases in the set. Both thresholds must pass independently.

**Assumption:** Precision and recall pull in opposite directions in fraud routing. A low-precision system floods the SIU with false positives and wastes investigator time. A low-recall system misses real fraud and costs the insurer money. The 88/80 split reflects a slight preference for precision — protecting SIU capacity — while keeping recall high enough to catch the majority of genuine fraud. The SIU Lead should validate these thresholds against their current referral workload before the evaluation set is finalised.
