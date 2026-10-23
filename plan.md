# ClaimSense AI — Assignment 3 Plan

**Engagement:** AutoSure (Houston TX) · Claims Adjudication Co-pilot  
**Assignment:** Building Production Agents + Platform Engineering  
**Stack:** React + TypeScript · Python · AWS Lambda · DynamoDB · Cognito · SAM

---

## Architecture

```
                    ┌─────────────────┐
  Adjuster browser  │  CloudFront +   │  ← React app (static, ~$0 at rest)
       ──────────►  │  S3 bucket      │
                    └────────┬────────┘
                             │ JWT (Cognito)
                    ┌────────▼────────┐
                    │  API Gateway    │  ← Cognito authorizer validates JWT
                    └──┬──────┬───┬──┘     before any Lambda fires
                       │      │   │
              ┌────────▼┐ ┌───▼┐ ┌▼────────┐
              │  CMS    │ │PAS │ │DocStore │  ← 3 Lambda functions
              │ Lambda  │ │    │ │ Lambda  │
              └────┬────┘ └──┬─┘ └────┬────┘
                   └─────────┴────────┘
                             │
                    ┌────────▼────────┐
                    │   DynamoDB      │  ← Pay per request, zero at rest
                    └─────────────────┘
```

---

## Folder Structure

```
AdjustAI/
├── frontend/                          # React + TypeScript (Vite)
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Login.tsx              # Cognito auth
│   │   │   ├── Dashboard.tsx          # Claims overview + KPI tiles
│   │   │   ├── ClaimDetail.tsx        # Full claim + docs + pipeline output
│   │   │   ├── DecisionReview.tsx     # Adjuster confirms/overrides co-pilot draft
│   │   │   └── AuditLog.tsx           # Pipeline run history
│   │   ├── components/
│   │   │   ├── ClaimsTable.tsx        # Sortable/filterable claims list
│   │   │   ├── FraudBadge.tsx         # Visual fraud score indicator
│   │   │   ├── VerdictCard.tsx        # Verdict + reasoning chain display
│   │   │   ├── ClauseChips.tsx        # BM25 cited clause IDs
│   │   │   └── StatusPill.tsx         # Colour-coded claim status
│   │   ├── hooks/
│   │   │   ├── useClaim.ts
│   │   │   ├── usePolicy.ts
│   │   │   └── useAuth.ts             # Cognito session + token refresh
│   │   ├── lib/
│   │   │   ├── api.ts                 # Axios client — attaches JWT to every request
│   │   │   └── auth.ts                # Amplify/Cognito config
│   │   └── main.tsx
│   ├── index.html
│   └── package.json
│
├── src/                               # Backend (Python)
│   ├── api/
│   │   ├── cms/handler.py             # Lambda: GET /claims/{id}, POST /claims/{id}/decision
│   │   ├── pas/handler.py             # Lambda: GET /policies/{id}
│   │   └── docstore/handler.py        # Lambda: GET /documents/{id}, POST /search
│   ├── agents/
│   │   ├── schemas.py                 # Strict Pydantic typed outputs for all 4 agents
│   │   ├── document_intake.py         # Agent 1: normalise docs, extract content_text
│   │   ├── coverage_check.py          # Agent 2: BM25 retrieval, cite clause IDs
│   │   ├── claim_assessment.py        # Agent 3: net payable, total-loss flag, fraud
│   │   ├── decision_draft.py          # Agent 4: verdict + reasoning chain
│   │   └── pipeline.py                # Orchestrator: pre-checks then 4 agents
│   ├── retrieval/
│   │   ├── pdf_extract.py             # Extract AutoSure_Policy_Manual PDF → clause text
│   │   └── bm25_index.py              # rank_bm25 index over extracted clauses
│   ├── deterministic/
│   │   └── checks.py                  # Liability-only deny, expired policy, total-loss ratio
│   ├── seed/
│   │   └── seed_dynamo.py             # Load CSVs → DynamoDB (idempotent)
│   └── eval/
│       ├── cases.py                   # 21 eval cases as Python structs
│       └── run_eval.py                # Runs pipeline, exits non-zero if accuracy < 92%
│
├── template.yaml                      # SAM: Lambdas + DynamoDB tables + API Gateway + Cognito
├── samconfig.toml                     # Per-environment deploy config (dev / staging / prod)
├── docker-compose.yml                 # DynamoDB Local + SAM local (single `docker compose up`)
├── env.local.json                     # Lambda env vars for local dev (points to DynamoDB Local)
├── Makefile                           # make dev | make seed | make eval | make deploy ENV=prod
├── plan.md                            # This file
└── .github/workflows/ci.yml           # Build → eval gate → push image
```

---

## DynamoDB Tables

| Table | Partition Key | Sort Key | Source |
|---|---|---|---|
| `claimsense-claims` | `claim_id` | — | claimsense_claims.csv |
| `claimsense-policies` | `policy_id` | — | claimsense_policies.csv |
| `claimsense-documents` | `claim_id` | `document_id` | claimsense_documents.csv |
| `claimsense-decisions` | `idempotency_key` | — | written by pipeline |

---

## API Endpoints

| Method | Path | Lambda | Description |
|---|---|---|---|
| GET | `/claims/{id}` | CMS | Read claim record |
| POST | `/claims/{id}/decision` | CMS | Write confirmed decision (idempotent) |
| GET | `/policies/{id}` | PAS | Read policy record |
| GET | `/documents/{id}` | DocStore | List documents for a claim |
| POST | `/search` | DocStore | BM25 search over policy corpus |

---

## Agent Pipeline

```
Pre-checks (deterministic/checks.py)
  ├── Liability Only + first-party claim → DENY (model_generated: false)
  ├── Expired policy → DENY (model_generated: false)
  └── Compute: net_payable, total_loss_flag, deductible_applied
          ↓
Agent 1 — Document Intake
  Normalises raw docs, extracts content_text, flags pending OCR
          ↓
Agent 2 — Coverage Check
  BM25 retrieval → cited_clauses (must include clause IDs, never from memory)
          ↓
Agent 3 — Claim Assessment
  Uses deterministic inputs (net payable, total-loss ratio, fraud score)
          ↓
Agent 4 — Decision Draft
  Verdict: Approve | Deny | Refer-Fraud | Refer-Adjuster
  model_generated: true
```

---

## The 4 Decision Outcomes

| Outcome | Trigger | Example Claim |
|---|---|---|
| **Approve** | Full coverage, low fraud, in-force policy | CLM-2024-1800 (fraud=0.05) |
| **Deny** | Liability Only + first-party claim | CLM-2024-2019 (POL-TXA-88339) |
| **Refer → Fraud** | fraud_risk_score ≥ 0.4 | CLM-2024-1873 (fraud=0.87) |
| **Refer → Adjuster** | Injuries + structural / expired policy | CLM-2024-1946 (injuries=Yes) |

---

## Key Architectural Decisions (locked — do not reverse)

| ADR | Decision |
|---|---|
| ADR-003 | BM25 over vector search — 12-clause corpus too small for embeddings |
| ADR-004 | Read-only except `POST /claims/{id}/decision` (adjuster-gated, idempotent) |
| ADR-005 | Deterministic arithmetic — model never computes dollar figures |
| ADR-006 | Liability-only deny is deterministic code, not model judgment |
| ADR-007 | De-identified data only — DPA required before production data |

---

## Build Steps

- [x] **Step 1** — `template.yaml` + `docker-compose.yml` (SAM + DynamoDB Local)
- [ ] **Step 2** — `src/seed/seed_dynamo.py` (CSVs → DynamoDB, idempotent)
- [ ] **Step 3** — Lambda handlers: `src/api/cms/`, `src/api/pas/`, `src/api/docstore/`
- [ ] **Step 4** — `src/retrieval/` — PDF extract + real BM25 index
- [ ] **Step 5** — `src/deterministic/checks.py` — pre-agent deterministic checks
- [ ] **Step 6** — `src/agents/` — schemas + 4 agents + pipeline orchestrator
- [ ] **Step 7** — `src/eval/` — 21-case eval suite + CI gate (92% threshold)
- [ ] **Step 8** — `frontend/` — Vite scaffold + Cognito auth + all pages + components
- [ ] **Step 9** — `.github/workflows/ci.yml` — build → eval gate → push image

---

## Assignment 3 Deliverables Checklist

- [ ] Agent set on OpenAI Agents SDK with strict typed outputs
- [ ] Container build and local orchestration — `docker compose up` starts everything
- [ ] Retrieval over policy corpus — every coverage output cites retrieved clause IDs
- [ ] CI pipeline — failing eval gate blocks image push
- [ ] All 4 decision outcomes produced correctly, `model_generated` flag set correctly
