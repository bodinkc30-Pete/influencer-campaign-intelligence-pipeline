# Influencer Master Data & Campaign Matching Pipeline

Portfolio Data Engineering project for transforming private, heterogeneous influencer campaign workbooks into a trusted Influencer Master, reusable campaign/performance history, and explainable campaign matching.

## Current status

**Architecture v1 approved. Golden Influencer Master v1, governed Campaign/Deliverable/Performance History, Historical Feature Layer v1, Explainable Matching v1/v2, Human Review/Feedback Contract v1, Campaign Requirement Normalization & Fit Readiness v1, Reliability Failure Lab v1, Operational Reliability v2, Temporal Reliability & Data SLO v3, PostgreSQL Warehouse Runtime v1, and Docker PostgreSQL Reproducibility/Recovery v18 are implemented and tested. ML remains out of scope.**

Current promotion boundary:

```text
Source Discovery + SHA-256
→ Sheet Inventory / Classification
→ Candidate Header + Section Detection
→ PII-safe Candidate Adapter
→ Data Quality Gate
→ Accepted Candidate Observations
   + Quarantine
→ Exact-handle Identity Cluster Preview
→ Deterministic Identity Review Queue
→ Evidence Classification
→ Independent Cross-source Corroboration
→ Source-wide Strong Identity Evidence Scan
→ Manual Decision Gate
→ Partial Reviewed Promotion
→ Golden Influencer Master v1
   + Identity Alias Provenance
   + Remaining Quarantine
   + Promotion Reconciliation
→ Private Brand Registry v1
→ Campaign Registry v1
→ Explicit Campaign Requirement Contract
→ Campaign Candidate Observation History
→ Campaign × Influencer Fact
→ Campaign History Reconciliation + DQ Issues
```

Ambiguous identities are still not silently promoted. Review groups explicitly marked `insufficient_evidence` remain quarantined while evidence-backed groups can enter Golden Master v1. Exact-handle clusters remain an intermediate deterministic layer, not a claim that every source identity has been resolved.

## Why this project exists

Historical influencer information is spread across multiple brands, campaigns, periods and Excel schemas. The project is designed to make that historical knowledge reusable while preserving provenance and protecting PII.

Target flow:

```text
Private Multi-brand Excel
→ File Registry
→ Raw Ingestion
→ Canonical Schema
→ Data Quality
→ PII Boundary
→ Entity Resolution
→ Trusted Influencer Master
→ Campaign / Deliverable / Performance History
→ Explainable Matching
→ Human Review
→ Feedback Loop
```

## Engineering principles

- Pipeline execution success does not imply data correctness.
- Preserve raw values and normalized/canonical values separately.
- Preserve exact raw sheet names for lineage, including source whitespace.
- Candidate tables must not assume a fixed header row.
- Repeated sections and intra-sheet schema boundaries must be detected.
- Entity resolution starts deterministic; ambiguous identities go to manual review.
- Exact-handle clustering is allowed only after the candidate observation itself passes DQ.
- Evidence strength and corroboration are review signals, not permission to merge.
- Resolved identity decisions require explicit evidence and pass a validation gate.
- Raw company data and PII are never committed to the public repository.
- PII values are suppressed from analytics-safe candidate outputs.
- Incremental loads and reruns must be idempotent.
- Important failures must produce evidence, RCA, recovery, reconciliation and regression tests.
- Matching starts with eligibility rules and explainable weighted ranking, not ML.

## Repository structure

```text
config/
  candidate_column_contract.json
  sheet_classification_rules.json
  source_registry.example.yml
  campaign_mapping.example.json
  private/                       # private source/campaign config; gitignored

data/
  raw/                           # private local source only; gitignored
  quarantine/                    # DQ/identity quarantine; gitignored
  private_audit/                 # source-derived evidence; gitignored
  synthetic/                     # safe public portfolio samples

docs/
  architecture/
  contracts/
  data_audit/
  private_audit/                 # incident/source evidence; gitignored

src/
tests/

compose.yaml                    # public-safe PostgreSQL 18.6 service definition
.env.example                    # non-secret local runtime template
.env                            # local secret only; gitignored and excluded from release artifacts
```

## Implemented MVP slice

The current slice proves:

1. workbook discovery and SHA-256 registry
2. sheet inventory and classification
3. variable candidate-header detection
4. repeated-section/schema-boundary handling
5. canonical candidate-field mapping
6. TikTok handle observation parsing
7. fee-model normalization (`fixed`, `free`, `barter`, `hourly`, `pending`)
8. PII detection/suppression boundary
9. accepted vs quarantine DQ promotion gate
10. exact-handle deterministic identity clustering for accepted observations
11. identity cluster reconciliation
12. deterministic identity manual-review grouping
13. identity evidence classification without auto-resolution
14. independent exact-handle corroboration from accepted observations
15. source-wide scan for strong TikTok URL / `@handle` evidence across all sheets
16. controlled manual-review decision validation
17. source-lineage uniqueness checks
18. Golden Master promotion with persistent survivor seed
19. private alias provenance
20. partial reviewed promotion while insufficient-evidence groups remain quarantined
21. Golden Master and review reconciliation checks
22. private brand/campaign source-instance mapping
23. one campaign registry row per candidate source sheet / campaign-period instance
24. explicit campaign-requirement extraction without silent month-to-month inheritance
25. source budget observations with auditable scope
26. 1,005 Golden-Master-linked campaign candidate observations
27. `campaign_id × influencer_id` fact reconciliation
28. duplicate/selection/confirmation/fee conflict warnings instead of silent overwrite
29. campaign summary and DQ issue outputs
30. regression tests for discovered source failures

## Verified audit state

The current private source run has:

```text
12 workbooks
77 worksheets
19 candidate worksheets
1,012 candidate observations
994 accepted PASS/WARN observations
18 quarantined ERROR observations
12 unique identity review groups
```

Deterministic exact-handle clustering of accepted observations:

```text
994 accepted observations
698 exact-handle identity clusters
161 clusters occur in more than one workbook
994 / 994 observations reconciled into clusters
```

After governed review, Golden Master v1 promotion produces:

```text
994 previously accepted observations
+ 11 reviewed identity observations promoted
= 1,005 Golden observations

703 Golden Influencer Master records
2,519 private alias-provenance rows
163 Golden Master records occur in more than one workbook
7 observations remain quarantined
```

The remaining 7 observations belong to 4 review groups with insufficient or conflicting evidence and are deliberately excluded from Golden Master v1.

Campaign History v1 now produces:

```text
12 Brand Registry records
19 Campaign Registry source instances
19 Campaign Requirement records
16 explicit source budget observations
1,005 Golden-Master-linked candidate observations
989 campaign × influencer fact records
16 campaign-history DQ issue records
0 unmapped campaign observations
0 missing Golden Master references
0 PII value columns emitted
0 requirement inheritance applied
```

The 16 DQ issue records are retained as warnings rather than overwritten. Current source evidence includes 16 repeated campaign/influencer pairs, 6 selection-status conflicts, 1 confirmation-status conflict, and 5 fee conflicts. These require a later business/source-precedence rule before a single authoritative selection/fee state can be claimed.

## Identity review evidence state

The initial review evidence classes are:

```text
2 explicit TikTok profile URL conflicts
7 embedded TikTok profile-handle conflicts
2 plain-text handle conflicts
1 display-only unparsable identity
```

Independent exact-handle corroboration adds:

```text
4 groups with one corroborated candidate handle
7 groups with no independent exact corroboration
1 group with no candidate handle to corroborate
```

Three of the four corroborated groups support the same handle shown by embedded TikTok profile evidence and are prepared as `human_can_confirm_supported_handle` recommendations. One corroborated group conflicts with the embedded profile handle and stays manual-review-only.

No evidence class or recommendation permits automatic resolution.

## Data-quality gate

Candidate extraction reports two independent outcomes:

```text
execution_status
```

and

```text
data_quality_gate_status
```

If identity conflicts/unparsable identities remain, extraction can complete successfully while those records are stopped from promotion:

```text
PASS / WARN
→ accepted observations
→ exact-handle identity cluster preview

ERROR
→ quarantine
→ identity review queue
→ evidence classification
→ cross-source corroboration
→ manual decision validation
→ no silent merge
```

This behavior is deliberate.

## Manual identity-review decision gate

Allowed controlled decisions are:

- `same_identity_use_handle`
- `different_identity_keep_separate`
- `alias_confirmed`
- `insufficient_evidence`

Rules include:

- blank decision = unresolved
- merge/alias decisions require an observed resolved handle and written evidence
- a resolved handle not present in observed candidates is rejected
- separate identities cannot be collapsed to one handle
- insufficient evidence stays quarantined
- fuzzy similarity alone is not merge evidence
- machine corroboration is advisory and never writes the final decision

A private manual-review workbook is generated outside the public-safe repository package to make these decisions auditable. The current governed review contains 8 promotable groups and 4 explicit `insufficient_evidence` groups. The latter remain quarantined.

## Data security

The source workbooks may contain personal or company-sensitive information such as names, telephone numbers, shipping addresses, tracking information and internal campaign codes.

**Raw company workbooks and source-derived private audit artifacts must never be committed to public GitHub.**

Public portfolio datasets must be synthetic or appropriately anonymized.

## Core stack and roadmap

- Python
- SQL
- PostgreSQL
- Docker — implemented for PostgreSQL reproducibility/recovery validation
- pytest
- structured logging
- Git / GitHub
- GitHub Actions

Airflow, dbt, Spark/Databricks, cloud services and probabilistic entity-resolution tooling are evaluated later only when they solve a demonstrated architecture or job-responsibility gap.

## Next gate

Brand/Campaign Registry v1 and Campaign Candidate History v1 are now implemented and reconciled.

Next implementation sequence:

```text
Golden Influencer Master v1
→ Campaign Candidate History v1 ✅
→ Campaign Deliverable History v1 ✅
→ Performance Metric Contract v1 ✅
→ Performance History v1 ✅
→ Historical Feature Layer v1 ✅
→ Eligibility Rules ✅
→ Explainable Weighted Ranking v1 ✅
→ Human Review / Decision Capture
→ Campaign Result Feedback Loop
```

The four unresolved identity review groups remain quarantined and do not enter campaign history. The 16 campaign-history DQ issue records also remain visible until a source-precedence/business rule can resolve them with evidence.

Deliverable, performance, and historical feature layers are now modeled and reconciled. Matching can proceed next, but only through explicit eligibility rules and configurable explainable weights.

## Definition of Done

The finished project must demonstrate:

```text
Build
→ Operate
→ Test
→ Break intentionally
→ Troubleshoot with evidence
→ Recover
→ Reconcile
→ Regression test
→ Optimize
→ Govern
→ Explain
```

This is a portfolio/production-like lab and must not be represented as real production ownership experience.

## Phase update — Deliverable & Performance History v1

The project now separates performance by business grain instead of forcing all metrics into an influencer fact:

```text
Campaign Candidate History
        ↓
Influencer Content Deliverable
        ├── Influencer Performance Snapshot
        └── Campaign-level Live / Ads / Monthly Performance
```

Promotion rules remain conservative: campaign mapping must be configured and influencer identity must resolve by exact canonical handle or exact known alias. Unresolved source rows are quarantined. Fuzzy auto-merge remains disabled.

Metric semantics are versioned. Video views, Live viewers, GMV, sales amount, revenue, ROI and ROAS are not silently treated as interchangeable metrics.

### Evidence snapshot (private run, aggregated only)

- 504 deliverable observations passed campaign + identity promotion gates.
- 494 canonical deliverables remained after exact same-post consolidation.
- 515 influencer performance snapshots linked to Golden Master identities.
- 1,260 campaign-level performance records were retained separately: Ads, Monthly Platform, and Live Session grains.
- 153 unresolved influencer-scoped source records remained quarantined rather than being fuzzy-linked.
- 62 automated tests pass in the public-safe codebase.

Real creator identities, source filenames, source mappings, lineage and raw workbooks remain private.


## Phase update — Historical Feature Layer v1

Historical Feature v1 creates one governed row per Golden Master `influencer_id`. It is an evidence layer, not a recommendation score.

The private evidence run produces:

```text
703 Golden Master inputs
→ 703 historical feature rows
→ 0 duplicate influencer IDs

186 influencers observed in 2+ campaign source-instances
163 influencers observed under 2+ brands
305 influencers with promoted influencer/content performance history
293 influencers with content views evidence
692 influencers with exact consistent fee history
170 influencers with known deliverable post-status history
```

Feature families include campaign reuse, selection history, exact fee evidence, follower/engagement source snapshots, deliverable completion evidence, content views/interactions, separate GMV/sales/order observations, and DQ/confidence evidence.

Guardrails remain explicit:

- content `views` never includes campaign-level Live viewers;
- `GMV`, `sales_amount`, and `revenue` remain separate concepts;
- conflicting/range/unknown fees are not forced into one fee value;
- selection/confirmation conflicts do not enter known-status rate denominators;
- two suspicious derived interaction-rate values remain DQ WARN evidence rather than being silently corrected;
- Recency is deferred until campaign chronology is governed;
- Category fit is deferred until a verified brand/category taxonomy exists;
- Persona/Audience fit is deferred until raw requirement fields are normalized with provenance.

The public-safe codebase now has **75 automated tests**. `pytest.ini` pins the project root on the test import path so a normal `pytest -q` run works without a manual `PYTHONPATH` override.


## Phase update — Explainable Matching v1

Explainable Matching v1 is intentionally a **Historical Evidence Baseline**, not a claim of full campaign fit. The current governed feature layer does not yet contain verified Category, Persona, Audience or Recency features, so the engine does not invent them.

Processing order:

```text
Historical Feature Layer v1
→ Eligibility Rules
→ Configurable Component Scores
→ Weighted Total Score
→ Deterministic Rank
→ Positive Reasons + Cautions
→ Human Review
```

Eligibility and weights live in JSON configuration. Matching v1 uses only governed evidence families:

- historical campaign experience;
- cross-brand experience;
- historical selection outcomes;
- content-view performance percentile among eligible candidates;
- budget headroom against a configured fee cap;
- governed post-status evidence;
- explicit data-confidence / DQ coverage.

Guardrails:

- no machine learning;
- no fuzzy entity resolution;
- no implicit Category/Persona/Audience score;
- no Recency score before chronology is governed;
- `budget_headroom` is not represented as ROI or cost efficiency;
- missing evidence receives a configured neutral component score and lowers data confidence rather than being treated as zero performance;
- exact zero-fee history is retained but flagged because it may represent free/barter or a source convention.

A private demo run uses a clearly labeled **synthetic portfolio scenario** with TikTok + a 3,000 fee cap. It is not represented as a historical client campaign requirement. The demo reconciles all 703 historical-feature rows into 570 eligible and 133 ineligible candidates, with a 30-candidate shortlist and no missing/duplicate eligible ranks.

The public-safe codebase now has **75 automated tests**.


## Phase update — Human Review & Campaign Feedback Contract v1

The next layer keeps the matching engine as decision support rather than silently turning a score into a business decision.

```text
Explainable Shortlist
→ Human Review Queue
→ Selected / Rejected / Hold + Reason
→ Campaign Result Capture
→ Feedback Readiness Gate
→ Observational Evaluation
```

The contract requires reviewer/timestamp/reason for every entered human decision. Campaign-result evidence is accepted only for selected candidates. Matching evaluation remains blocked until human decisions are complete, selected-candidate results are complete, and a business success definition is explicitly documented.

Important guardrails:

- no automatic human decision;
- no fabricated campaign result;
- no model-accuracy/precision claim for rejected candidates because their counterfactual outcomes are unknown;
- no automatic weight calibration;
- no machine learning;
- public tests use synthetic fixtures only.

The current private matching scenario therefore creates a **pending review/result template** rather than fabricated feedback. Evaluation status remains `WAITING_FOR_REAL_FEEDBACK` until real decisions and campaign outcomes exist.

The public-safe codebase now has **86 automated tests** after adding the Human Review & Campaign Feedback contract and observational evaluation readiness logic.


## Phase update — Campaign Requirement Normalization & Fit Readiness v1

This layer converts explicit source brief fields into controlled, explainable dimensions without silently copying requirements across campaign periods.

```text
Raw Campaign Requirement
→ Deterministic Platform / Gender / Age Normalization
→ Controlled Theme / Persona / Content-style Tags
→ DQ + Provenance
→ Historical Audience Profile
→ Historical Requirement Exposure
→ Campaign Fit Readiness Gate
```

Key rules:

- tier-only or missing briefs are not inherited from another month/campaign;
- taxonomy mapping uses deterministic keyword rules only; fuzzy semantic mapping is disabled;
- campaign-theme/persona/content-style tags are rule-derived and are not represented as an enterprise-approved category taxonomy;
- historical persona-requirement exposure is evidence of prior campaign exposure, not proof of an intrinsic creator persona;
- audience gender/age values shifted across source columns are excluded from canonical audience profiles and preserved as DQ warnings;
- audience snapshots remain historical evidence rather than timeless creator attributes.

Private evidence from the 19 Campaign Registry source instances yields 12 campaigns ready for rule-based fit dimensions and 7 campaigns intentionally held at `insufficient_source_requirement`. All 703 Golden Master influencers reconcile to audience-profile and historical requirement-exposure rows; 612 have at least one governed audience gender or age observation.

The public-safe codebase now has **98 automated tests**.

## Phase update — Explainable Matching v2

Matching v2 combines the governed requirement layer with historical evidence while treating **target-campaign leakage as a testable data-quality failure**. It is a historical replay baseline, not a claim of production recommendation accuracy.

For each target campaign:

```text
Fit-ready Campaign Requirement
→ Remove Target Campaign from all Historical Inputs
→ Rebuild non-target Campaign / Deliverable / Performance Evidence
→ Rebuild non-target Audience Evidence
→ Rebuild non-target Requirement Experience
→ Eligibility Rules
→ Dynamic Active Weights
→ Explainable Component Scores
→ Deterministic Ranking
→ Leakage Audit + Reconciliation
```

The leakage guard excludes the target campaign **before aggregation** from:

- Campaign × Influencer history;
- Deliverable history;
- Influencer performance;
- Audience evidence;
- historical Theme / Persona-requirement / Content-style exposure.

Target selection, confirmation and campaign-outcome fields are never score inputs. Every target run emits an explicit leakage audit.

Fit components now include:

- Audience Gender evidence fit;
- Audience Age evidence fit;
- historical Theme exposure fit;
- historical Persona-requirement exposure fit;
- historical Content-style exposure fit;
- non-target campaign / cross-brand experience;
- non-target selection history;
- non-target content-view percentile;
- governed per-influencer budget headroom when the target budget scope supports it;
- non-target post-status reliability;
- evidence / DQ confidence.

Important semantics remain explicit:

- Persona experience means prior exposure to similar campaign requirements, not intrinsic creator persona truth.
- Theme tags remain deterministic source-text tags, not an enterprise-approved category taxonomy.
- Audience observations are historical snapshots and are not treated as timeless demographics.
- `campaign_total` and `candidate_pool_unspecified` budgets are never converted into individual fee caps.
- Target dimensions missing from the approved brief are disabled and the remaining weights are renormalized. Candidate-level missing evidence receives a neutral score and lowers data confidence.
- Recency and automatic weight calibration remain deferred.

The current private historical replay uses all 12 campaigns marked `ready_for_rule_based_fit` and produces:

```text
12 target campaign runs
703 Golden Master candidates per target
8,436 scenario × influencer score rows
360 shortlist rows (30 per target)
29 governed individual-budget eligibility rejections
0 duplicate scenario × influencer score rows
0 eligible rows missing ranks
0 target-campaign leakage-audit failures
0 target-outcome fields used in scoring
```

The public-safe codebase now has **109 automated tests**.


## Reliability & Failure Testing Extension v1

The project now includes a controlled reliability lab for the Excel source boundary. This is a **portfolio lab / production-like simulation**, not a claim of production incident experience.

Failure method:

```text
Hypothesis
→ Inject Failure in an isolated copy
→ Detect
→ Capture Evidence
→ Verify Cause
→ Contain / Fix
→ Recover
→ Rerun
→ Reconcile
→ Regression Test
→ Prevent
```

Reliability v1 covers five high-risk scenarios:

1. missing expected workbook;
2. duplicate workbook content under a different filename;
3. candidate schema drift / column rename;
4. empty expected candidate sheet;
5. same-batch rerun / idempotency.

Implemented controls:

- exact approved source baseline manifest for controlled replay;
- expected workbook/sheet validation;
- SHA-256 duplicate-content hard gate;
- candidate header-signature drift detection;
- expected non-empty sheet validation;
- deterministic batch fingerprint with an atomic idempotency ledger.

A controlled private run against isolated copies of the 12 real source workbooks produced:

```text
12 baseline workbooks
77 baseline sheets
19 baseline candidate sheets
5 controlled failure experiments
5 / 5 detected and recovered as expected
0 original source workbook hash changes after the lab
```

One experiment also exposed a concrete pre-v13 control gap: the previous discovery CLI reported duplicate hash groups but could still exit successfully when no expected file count was supplied. v13 makes duplicate workbook hashes a blocking discovery failure by default and includes a regression test for that behavior.

Private incident evidence (source hashes, filenames, timelines and RCA records) is excluded from the public repository. Public tests use synthetic Excel fixtures only.

The public-safe codebase now has **116 automated tests**.

## Reliability & Operations Extension v2

Operational Reliability v2 extends the source-boundary Failure Lab into run-state, transaction, retry and monitoring behavior. This remains a **portfolio / production-like lab**, not a claim of production incident experience.

Operational flow:

```text
Run Start
→ Incremental State Gate
→ Stage Write
→ Atomic Commit
→ Run Ledger
→ Monitoring Evaluation
→ Alert Evidence
→ Recovery / Rerun
→ Reconciliation
→ Regression Test
```

Controlled scenarios:

1. bad incremental state pointing to a batch that is not a successful run;
2. partial load / interrupted batch that leaves staging rows without a commit marker;
3. transient dependency failure recovered by a bounded retry policy;
4. failed/slow/retry-heavy/incomplete run detected by monitoring and routed to alert evidence, followed by a clean recovery run.

Implemented controls:

- incremental state referential integrity against successful run-ledger batches;
- state advancement only after governed successful commit;
- staging vs committed output boundary;
- atomic commit marker and orphan-staging detection;
- idempotent committed-run guard;
- bounded retry with attempt/backoff evidence;
- run-level status, stage, row-count, retry and duration telemetry;
- monitoring rules for failed runs, long duration, excessive retries, rejected rows and low row completeness;
- simulated alert sink for portfolio evidence without pretending an external production alerting integration exists.

A private controlled run used the approved 12-workbook source baseline and the 703-row Historical Feature Layer as the transactional payload:

```text
4 controlled operational experiments
4 / 4 PASS
703 / 703 rows recovered after partial-load interruption
same recovered run rerun → SKIP_ALREADY_COMMITTED
transient dependency → 2 retries, success on attempt 3
failed monitoring run → 5 monitoring events / 5 alert records
clean monitoring recovery → 703 / 703 rows, 0 threshold alerts
failed run committed output → 0
original source workbook hashes unchanged → 12 / 12
```

Important guardrails:

- a staging file is never accepted as a committed data product;
- retries only catch explicitly retryable failures and are bounded by configuration;
- alert delivery is simulated to an evidence sink in this portfolio lab;
- recovery is not considered complete until row counts/state transitions reconcile and regression tests pass;
- `Pipeline SUCCESS != Data Correct` remains the governing reliability principle.

The public-safe codebase now has **126 automated tests**.

## Temporal Reliability & Data SLO Extension v3

Temporal Reliability v3 extends run-level reliability into event-time correctness. It focuses on a failure mode where a pipeline can finish successfully while late-arriving records are silently missed by an event-time watermark. This remains a **portfolio / production-like lab**, not a production incident claim.

Temporal flow:

```text
Event Time + Arrival Time
→ Watermark Gate
→ Incremental Selection
→ Late-arrival Detection
→ Bounded Backfill
→ Business-key Upsert
→ Idempotent Replay
→ Freshness / Completeness / Watermark SLO
→ Alert Escalation Evidence
→ Recovery / Reconciliation
```

Controlled scenarios:

1. a late performance record arrives after its event-time watermark and is missed by strict `event_date > watermark` selection;
2. a watermark is ahead of the maximum observed governed event date;
3. a stale watermark trails the governed source maximum beyond the configured lag threshold;
4. a bounded backfill recovers the missed row exactly once and a repeated backfill inserts zero additional rows;
5. freshness, completeness and watermark SLO breaches emit monitoring events and simulated escalation, followed by a clean recovery run.

Important evidence guardrail: the private source contains event dates but does **not** provide authoritative ingestion/arrival timestamps. The late-arrival experiment therefore keeps the real source performance record and lineage but injects a controlled synthetic arrival date. That synthetic timestamp is lab metadata and must not be presented as company production metadata.

The private controlled run used Campaign Performance History v1 and the approved 12-workbook source baseline:

```text
1,260 campaign-performance source rows
287 rows with governed ISO event dates used by the temporal lab
973 blank/non-ISO/non-date event-date values excluded from temporal processing
5 controlled temporal experiments
5 / 5 PASS
1 controlled late-arriving record detected behind the watermark
1 missing row recovered by bounded backfill
same backfill rerun → 0 additional inserts
3 data-SLO breach events
5 simulated primary/escalated alert evidence rows
clean recovery run → 287 / 287 rows, 0 SLO breach events
original source workbook hashes unchanged → 12 / 12
```

Implemented controls:

- ISO event-date gate for temporal processing;
- arrival-aware late-data detection behind a watermark;
- watermark ahead-of-source and stale-watermark blocking rules;
- bounded backfill interval;
- business-key upsert and idempotent backfill replay;
- internal freshness, completeness and watermark-lag SLOs;
- severity-based simulated alert escalation;
- recovery reconciliation and source-integrity verification.

SLA and SLO are kept distinct. The project implements internal **SLOs** for portfolio monitoring, but it does not invent an external **SLA** because no approved business/service commitment exists in the source material.

The public-safe codebase now has **138 automated tests**.


## PostgreSQL Warehouse Runtime & Incremental Operations v1

The project includes a PostgreSQL persistent warehouse plus an operational runner that applies the same controls proven during the controlled local warehouse lab. Private load-ready CSVs stay outside the public repository.

Architecture:

```text
Private governed load-ready CSVs
→ deterministic SHA-256 batch fingerprint
→ PostgreSQL schema bootstrap / migration
→ same-batch gate
   ├─ same as last SUCCESS → SKIPPED ledger, no COPY, no UPSERT
   └─ new batch → RUNNING / PRE_LOAD
       → atomic STAGING_LOAD
       → staging reconciliation
       → CORE_UPSERT
       → mart refresh
       → RECONCILIATION
       → DQ evidence
       → SUCCESS
       → incremental state advance
```

PostgreSQL schemas:

- `stg` — text-first landing tables that preserve source anomalies;
- `core` — typed dimensions/facts with PK/FK/UNIQUE/CHECK constraints and indexes;
- `ops` — pipeline run, incremental state and DQ result tables;
- `mart` — analytical views pre-aggregated before joins to avoid metric fanout.

Operational controls implemented in v17 and revalidated against the Docker runtime in v18:

- deterministic batch fingerprint across the nine private load-ready CSVs;
- secure password prompt or `PGPASSWORD` environment variable (password is not written to evidence JSON);
- automatic Windows `psql` discovery with explicit `--psql-path` override;
- idempotent DDL bootstrap before data processing;
- same-batch detection based on the last successful incremental state;
- `SKIPPED / SAME_BATCH_GATE` ledger record with no staging COPY or core UPSERT;
- atomic staging `TRUNCATE + COPY` transaction;
- staging row-count reconciliation against the CSV files actually supplied;
- transactional `INSERT ... ON CONFLICT DO UPDATE` core promotion;
- conflict updates preserve the original `loaded_at` value so an identical replay does not create timestamp drift;
- mart grain/fanout DQ checks;
- run state transitions (`PRE_LOAD → STAGING_LOAD → CORE_UPSERT → RECONCILIATION → COMPLETED`);
- DQ evidence written to `ops.data_quality_result`;
- incremental state advances only after all required DQ checks pass;
- failed tracked runs are marked `FAILED` without advancing successful incremental state.

Run the public runner from the repository root while pointing it to a **private** load directory:

```powershell
python -m src.run_postgres_warehouse `
  --host localhost `
  --port 5433 `
  --user postgres `
  --database influencer_dw `
  --load-dir "C:\path\to\private\postgresql-warehouse-v1\load_ready" `
  --evidence-json "C:\path\to\private\warehouse-runtime-evidence.json"
```

If `PGPASSWORD` is not set, the runner prompts for the PostgreSQL password without echoing it. The password is never included in the JSON output.

Controlled local runtime evidence has demonstrated schema creation, staging/core promotion, identical replay stability, mart reconciliation, representative `EXPLAIN (ANALYZE, BUFFERS)` evidence, tracked SUCCESS state, and same-batch SKIPPED behavior. This is a **portfolio lab**, not a production deployment. A database-level injected rollback/failure experiment remains a separate reliability extension rather than being claimed implicitly.

The public-safe codebase now has **155 automated tests**.


## Docker PostgreSQL Reproducibility & Recovery v18

Docker v18 proves that the PostgreSQL warehouse can be reconstructed, operated, skipped idempotently, stopped, restarted, removed and recreated while preserving governed warehouse state. This is a **local portfolio / production-like reliability lab**, not a production deployment claim.

Runtime boundary:

```text
Native PostgreSQL 18.6
localhost:5433
        │
        └── remains separate

Docker PostgreSQL 18.6
localhost:55432
        ↓
container:5432
        ↓
influencer_dw
        ↓
named volume: influencer_pgdata
```

Public Docker assets:

- `compose.yaml` — PostgreSQL `18.6`, healthcheck, named volume and dedicated network;
- `.env.example` — non-secret template only;
- `.env` — required only for local secrets, gitignored and excluded from public release artifacts;
- host port `55432` — intentionally avoids the native PostgreSQL endpoint on `5433` and other local Docker PostgreSQL services on `5432`;
- `influencer_pgdata` — persistent named volume;
- `influencer-network` — dedicated Docker bridge network.

Fresh rebuild evidence:

```text
fresh Docker database before migration
→ 0 warehouse schemas
→ 0 warehouse tables

001 schemas/helpers
→ 4 schemas
→ 4 helper functions

002 staging
→ 9 / 9 UNLOGGED tables

003 core/ops
→ 9 core tables
→ 3 ops tables
→ 26 CHECK constraints
→ 13 FK constraints
→ 12 PK constraints
→ 3 UNIQUE constraints
→ 13 explicit indexes

private governed CSV staging load
→ 9 files
→ 6,530 rows

004 core upsert
→ 6,530 rows
→ 0 duplicate campaign × influencer business-key groups
→ 0 campaign/influencer orphans in the checked relationship

005 reconciliation
→ 7 / 7 checks with 0 violations
→ all 9 core table row counts reconcile
→ total core rows = 6,530

006 marts
→ 2 views
→ influencer mart grain = 703
→ campaign mart grain = 19
→ 6 / 6 mart fanout checks exactly match core counts
```

One-command runner evidence against Docker PostgreSQL:

```text
first tracked run
→ status = SUCCESS
→ source_rows = 6,530
→ DQ = 8 PASS / 0 non-pass
→ incremental state advances to the successful run

identical second batch
→ same_batch_check = 1
→ status = SKIPPED
→ stage = SAME_BATCH_GATE
→ rows_loaded = 0
→ no staging COPY
→ no core UPSERT
→ successful incremental state remains unchanged
```

Persistence/recovery evidence:

```text
docker compose stop postgres
→ container Exited (0)
→ localhost:55432 = no response

docker compose start postgres
→ healthy
→ localhost:55432 = accepting connections
→ total core rows still 6,530
→ SUCCESS/SKIPPED run history preserved
→ DQ evidence preserved

docker compose down            # deliberately without -v
→ container removed
→ network removed
→ influencer_pgdata preserved

docker compose up -d postgres
→ container/network recreated
→ PostgreSQL healthy
→ total core rows still 6,530
→ ops/incremental state preserved
```

The local database credential is never stored in the public release package. Password entry is handled through a secure prompt or runtime environment variable, and the local `.env` is excluded from release staging. Public safety checks for v18 verified no private warehouse evidence, no old absolute workspace paths, and no Python cache artifacts in the release staging tree.

Typical local Docker bootstrap:

```powershell
Copy-Item .env.example .env
# Edit .env locally and replace the placeholder password. Never commit .env.

docker compose pull postgres
docker compose up -d postgres
docker compose ps postgres
```

Run the warehouse automation against Docker PostgreSQL while keeping the governed load directory private:

```powershell
python -m src.run_postgres_warehouse `
  --host localhost `
  --port 55432 `
  --user postgres `
  --database influencer_dw `
  --load-dir "C:\path\to\private\postgresql-warehouse-v1\load_ready" `
  --evidence-json "C:\path\to\private\warehouse-docker-runtime-evidence.json"
```

A same-batch rerun should return `SKIPPED` after the last successful batch fingerprint is already registered. Destructive volume removal such as `docker compose down -v` is intentionally **not** part of the persistence test because that command deletes the named volume.

Post-Docker regression result:

```text
155 passed
```
