# Portfolio Evidence Map v1

## Purpose

This document maps the major engineering capabilities in the **Influencer Campaign Intelligence Pipeline** to concrete implementation, automated tests, runtime/reconciliation evidence, and public-safe portfolio documentation.

The traceability pattern is:

```text
Requirement / Capability
→ Implementation
→ Automated Test
→ Runtime / Reconciliation Evidence
→ Portfolio Documentation
→ Safe Claim
```

This is a **portfolio / production-like engineering lab**. It does not claim production ownership, customer-impacting incident response, or enterprise on-call experience.

---

## 1. Evidence Rules

A capability should not be described as complete only because source code exists.

For this project, stronger evidence means:

```text
code exists
+
tests exist
+
execution evidence exists where applicable
+
reconciliation / failure-path evidence exists where applicable
+
documentation explains the boundary
```

The project follows:

```text
Pipeline SUCCESS != Data Correct
Fix Applied != Recovery Proven
```

---

## 2. Evidence Strength Levels

| Level | Meaning |
|---|---|
| Contract | Requirement, schema, or behavior is documented |
| Implementation | Executable Python / SQL / configuration exists |
| Automated Test | Behavior is covered by pytest or integration assertions |
| Runtime Evidence | A real execution produced inspectable evidence |
| Reconciliation | Output correctness or state consistency was checked |
| Failure / Recovery Evidence | Controlled failure and recovery behavior was exercised |
| Hosted CI Evidence | GitHub Actions executed the checks on a hosted runner |

---

## 3. Repository Evidence Baseline

Current public repository evidence includes:

```text
116 tracked files
2 architecture documents
9 business/data contracts
4 data-audit / identity-review documents
3 warehouse documents
4 reliability documents
2 portfolio evidence documents before this map
23 pytest test files
2 PostgreSQL integration assets
6 PostgreSQL SQL migrations
1 GitHub Actions workflow
```

Current automated pytest baseline:

```text
23 test_*.py files
155 pytest test functions
155 passed in the validated local regression baseline
```

The dedicated PostgreSQL integration harness is separate from the 155 pytest baseline.

---

# 4. Capability-to-Evidence Map

## 4.1 Source Discovery and Workbook / Sheet Classification

**Requirement / Capability**

Multiple workbook sources must be discoverable and sheets must be classified before downstream transformation.

**Implementation**

```text
src/discover_sources.py
src/xlsx_probe.py
src/build_sheet_inventory.py
src/sheet_classifier.py
```

**Automated Tests**

```text
tests/test_sheet_classifier.py
```

**Evidence**

Controlled handling exists for:

```text
missing workbook
duplicate workbook content
empty expected candidate sheet
schema drift / renamed column
```

**Documentation**

```text
docs/data_audit/sheet_classification_v1.md
docs/reliability/reliability_failure_lab_v1.md
```

**Safe Claim**

> Built and tested workbook discovery / sheet-classification logic for a multi-workbook portfolio pipeline, including controlled missing, duplicate, empty-sheet, and schema-drift scenarios.

---

## 4.2 Canonical Schema Adaptation

**Requirement / Capability**

Different workbook schema variants must be normalized into a consistent candidate representation before master-data processing.

**Implementation**

```text
src/candidate_adapter.py
src/extract_candidate_observations.py
src/build_resolved_candidate_observations.py
```

**Automated Tests**

```text
tests/test_candidate_adapter.py
tests/test_resolved_candidate_observations.py
```

**Contract**

```text
docs/contracts/canonical_data_contract_v1.md
```

**Safe Claim**

> Implemented deterministic schema adaptation from heterogeneous workbook observations into a governed canonical candidate layer.

---

## 4.3 PII Boundary and Public-Safe Portfolio Design

**Requirement / Capability**

Private raw workbook content and PII must not be exposed through the public portfolio repository.

**Implementation / Controls**

```text
src/pii_guard.py
.env.example
.gitignore
```

**Automated Tests**

```text
tests/test_pii_guard.py
```

**Integration Evidence**

```text
tests/integration/generate_postgres_integration_fixture.py
tests/integration/run_postgres_integration.py
```

The PostgreSQL CI fixture is synthetic and intentionally uses public-safe identifiers rather than company-derived load-ready rows.

**Documentation**

```text
docs/architecture/architecture_v2.md
docs/portfolio/data_quality_summary_v1.md
docs/portfolio/testing_evidence_v1.md
docs/reliability/ci_cache_incident_v1.md
```

**Safe Claim**

> Designed an explicit private-raw / public-safe boundary with PII checks, ignored local secrets, environment templates, and synthetic integration data.

---

## 4.4 Deterministic Entity Resolution

**Requirement / Capability**

Influencer identity resolution must prioritize deterministic evidence and avoid automatic fuzzy merging of ambiguous identities.

**Implementation**

```text
src/build_deterministic_identity_clusters.py
src/scan_identity_source_evidence.py
src/enrich_identity_review_evidence.py
src/corroborate_identity_review.py
src/build_identity_review_queue.py
src/validate_identity_review_decisions.py
```

**Automated Tests**

```text
tests/test_deterministic_identity_clusters.py
tests/test_identity_source_evidence.py
tests/test_identity_review_evidence.py
tests/test_identity_corroboration.py
tests/test_identity_review_queue.py
tests/test_identity_review_decision_gate.py
```

**Documentation**

```text
docs/data_audit/identity_review_evidence_policy.md
docs/data_audit/identity_review_corroboration_v1.md
docs/data_audit/manual_identity_review_contract.md
```

**Runtime / Review Evidence**

```text
12 identity review groups
4 independently corroborated groups
7 without independent exact corroboration
1 without a parseable handle
auto_resolution_allowed = no for review groups
```

**Safe Claim**

> Built a deterministic entity-resolution workflow with evidence enrichment, corroboration, manual-review gating, and explicit non-auto-resolution of ambiguous groups.

---

## 4.5 Golden Influencer Master Promotion

**Implementation**

```text
src/promote_golden_master.py
```

**Automated Tests**

```text
tests/test_golden_master_promotion.py
```

**Contract**

```text
docs/contracts/golden_master_promotion_contract_v1.md
```

**Runtime Evidence**

```text
703 influencer master records
2519 identity aliases
163 masters represented across multiple workbooks
8 reviewed / promoted groups
4 quarantined groups
```

**Safe Claim**

> Implemented rule-governed Golden Master promotion with alias lineage, cross-workbook identity consolidation, review evidence, and quarantine behavior.

---

## 4.6 Campaign History

**Implementation**

```text
src/build_campaign_history.py
```

**Automated Tests**

```text
tests/test_campaign_history.py
```

**Contract**

```text
docs/contracts/campaign_history_contract_v1.md
```

**Runtime Evidence**

```text
12 brands
19 campaigns
989 campaign × influencer facts
```

**Safe Claim**

> Built a normalized campaign-history layer connecting influencers, brands, campaigns, and campaign participation.

---

## 4.7 Deliverable and Performance History

**Implementation**

```text
src/build_deliverable_performance_history.py
src/deliverable_performance.py
```

**Automated Tests**

```text
tests/test_deliverable_performance.py
```

**Contract**

```text
docs/contracts/deliverable_performance_contract_v1.md
```

**Runtime Evidence**

```text
494 campaign deliverables
515 influencer-performance rows
1260 campaign-performance rows
```

**Safe Claim**

> Separated deliverable and performance history from master data so campaign intelligence can use historical evidence without corrupting entity identity.

---

## 4.8 Campaign Requirement Normalization and Readiness

**Implementation**

```text
src/requirement_normalization.py
src/build_requirement_fit_layer.py
config/requirement_taxonomy.example.json
```

**Automated Tests**

```text
tests/test_requirement_normalization.py
```

**Contract**

```text
docs/contracts/campaign_requirement_normalization_contract_v1.md
```

**Runtime Evidence**

```text
19 campaign requirements
12 campaigns classified as fit-ready
```

**Safe Claim**

> Implemented a governed requirement-normalization and readiness layer so matching only uses campaign requirements with sufficient structured evidence.

---

## 4.9 Historical Feature Engineering

**Implementation**

```text
src/historical_features.py
src/build_historical_features.py
config/historical_feature_config.example.json
```

**Automated Tests**

```text
tests/test_historical_features.py
```

**Contract**

```text
docs/contracts/historical_feature_contract_v1.md
```

**Runtime Evidence**

```text
703 historical-feature rows
```

**Safe Claim**

> Built reusable historical influencer features from governed history, with feature behavior separated from matching logic.

---

## 4.10 Explainable Matching v1

**Requirement / Capability**

Use eligibility rules and explainable weighted ranking rather than starting with machine learning.

**Implementation**

```text
src/matching.py
src/run_explainable_matching.py
config/matching_config.example.json
```

**Automated Tests**

```text
tests/test_matching.py
```

**Contract**

```text
docs/contracts/explainable_matching_contract_v1.md
```

**Runtime Evidence**

```text
570 eligible influencers
30 shortlisted influencers
```

**Safe Claim**

> Implemented an eligibility-first, config-driven weighted ranking approach that produces explainable shortlist results without requiring ML.

---

## 4.11 Explainable Matching v2 / Historical Replay

**Implementation**

```text
src/matching_v2.py
src/run_explainable_matching_v2.py
config/matching_v2_config.example.json
```

**Automated Tests**

```text
tests/test_matching_v2.py
```

**Contract**

```text
docs/contracts/explainable_matching_v2_contract.md
```

**Runtime Evidence**

```text
8436 score rows
360 shortlist rows
0 leakage-audit failures
```

**Safe Claim**

> Extended explainable ranking to historical replay with temporal controls and explicit leakage checks.

---

## 4.12 Human Review and Feedback Loop

**Implementation**

```text
src/build_feedback_templates.py
src/feedback_loop.py
config/feedback_config.example.json
```

**Automated Tests**

```text
tests/test_feedback_loop.py
```

**Contract**

```text
docs/contracts/human_review_feedback_contract_v1.md
```

**Runtime Evidence**

```text
30 pending review records
no fabricated campaign outcomes
```

**Safe Claim**

> Implemented human-review and feedback structures while keeping unknown real-world outcomes explicitly pending instead of inventing labels.

---

# 5. PostgreSQL Warehouse Evidence

## 5.1 Warehouse Architecture and Data Model

**Implementation**

```text
src/build_postgres_warehouse_stage.py
src/warehouse_contract.py
src/postgres_warehouse_runtime.py
src/run_postgres_warehouse.py

sql/postgres/001_schemas_and_helpers.sql
sql/postgres/002_staging_tables.sql
sql/postgres/003_core_tables.sql
sql/postgres/004_incremental_upserts.sql
sql/postgres/005_reconciliation.sql
sql/postgres/006_mart_views.sql
```

**Automated Tests**

```text
tests/test_warehouse_contract.py
tests/test_postgres_warehouse_runtime.py
```

**Integration Assets**

```text
tests/integration/generate_postgres_integration_fixture.py
tests/integration/run_postgres_integration.py
```

**Documentation**

```text
docs/warehouse/postgresql_warehouse_v1.md
docs/warehouse/postgresql_warehouse_erd_v1.md
docs/warehouse/data_dictionary_v1.md
docs/architecture/architecture_v2.md
```

**Runtime Evidence**

```text
6530 governed warehouse rows

703 dim_influencer
2519 influencer_identity_alias
12 dim_brand
19 dim_campaign
19 campaign_requirement
989 fact_campaign_influencer
494 fact_campaign_deliverable
515 fact_influencer_performance
1260 fact_campaign_performance
```

**Safe Claim**

> Designed and implemented a PostgreSQL warehouse with staging, governed core tables, constraints, incremental upserts, reconciliation SQL, marts, and documented ERD/data dictionary.

---

## 5.2 Incremental Load and Idempotency

**Implementation**

```text
sql/postgres/004_incremental_upserts.sql
src/postgres_warehouse_runtime.py
src/run_postgres_warehouse.py
```

**Automated Tests**

```text
tests/test_postgres_warehouse_runtime.py
tests/test_warehouse_contract.py
```

**Real PostgreSQL Integration Evidence**

```text
FIRST_STATUS=SUCCESS
FIRST_SKIPPED=False
FIRST_SOURCE_ROWS=9
SECOND_STATUS=SKIPPED
SECOND_SKIPPED=True
FINGERPRINT_MATCH=True
ROW_COUNTS_UNCHANGED=True
```

**Safe Claim**

> Implemented deterministic batch fingerprinting and same-batch idempotency, validated by a real PostgreSQL synthetic integration rerun.

---

## 5.3 Reconciliation

**Implementation**

```text
sql/postgres/005_reconciliation.sql
```

**Evidence**

```text
core row-count checks
foreign-key orphan checks
duplicate campaign × influencer business-key checks
same-batch row-count stability
deterministic fingerprint checks
```

Validated reconciliation evidence reported zero governed violations for the established warehouse baseline.

**Documentation**

```text
docs/portfolio/testing_evidence_v1.md
docs/portfolio/data_quality_summary_v1.md
docs/warehouse/postgresql_warehouse_v1.md
```

**Safe Claim**

> Treated reconciliation as a separate correctness gate rather than assuming a successful pipeline run means correct data.

---

# 6. Reliability Evidence

## 6.1 Source Reliability Failure Lab

**Implementation**

```text
src/reliability_lab.py
src/run_reliability_failure_lab.py
```

**Automated Tests**

```text
tests/test_reliability_lab.py
```

**Controlled Scenarios**

```text
missing workbook
duplicate workbook content
schema drift / renamed column
empty expected candidate sheet
same-batch rerun
```

**Documentation**

```text
docs/reliability/reliability_failure_lab_v1.md
```

**Runtime Evidence**

```text
5 / 5 controlled scenarios executed
source hashes preserved during the lab
```

**Safe Claim**

> Built a controlled source-failure lab that captures detection, evidence, recovery, rerun, and prevention behavior without modifying private raw source data.

---

## 6.2 Operational Reliability

**Implementation**

```text
src/operational_reliability.py
src/run_operational_reliability_lab.py
```

**Automated Tests**

```text
tests/test_operational_reliability.py
```

**Controlled Scenarios**

```text
bad incremental state
partial / interrupted load
transient dependency failure
monitoring / alert evaluation
```

**Documentation**

```text
docs/reliability/operational_reliability_v2.md
```

**Runtime Evidence**

```text
4 / 4 controlled operational experiments executed
```

**Safe Claim**

> Exercised operational failure classification, bounded retry/recovery behavior, and monitoring-state evaluation in a controlled portfolio lab.

---

## 6.3 Temporal Reliability

**Implementation**

```text
src/temporal_reliability.py
src/run_temporal_reliability_lab.py
```

**Automated Tests**

```text
tests/test_temporal_reliability.py
```

**Controlled Scenarios**

```text
late-arriving data
ahead watermark
stale watermark
bounded backfill
freshness / completeness / watermark SLO recovery
```

**Documentation**

```text
docs/reliability/temporal_reliability_v3.md
```

**Runtime Evidence**

```text
5 / 5 temporal experiments
287 governed temporal rows
SLO recovery evidence
```

**Safe Claim**

> Implemented and tested late-arrival, watermark, backfill, and temporal SLO behavior in a controlled reliability lab.

---

# 7. Automated Testing Evidence

## 7.1 Repository-Wide Regression

**Implementation**

```text
pytest.ini
tests/test_*.py
```

**Evidence**

```text
23 pytest files
155 pytest test functions
155 passed in the validated regression baseline
```

The 155 figure is repository-wide and must not be described as:

```text
155 PostgreSQL integration tests
155 end-to-end tests
155 Data Quality-only tests
```

**Documentation**

```text
docs/portfolio/testing_evidence_v1.md
```

**Safe Claim**

> Maintained a 155-test automated regression baseline across source/canonicalization, identity/master data, history, matching, reliability, PII, and warehouse contract/runtime logic.

---

## 7.2 Real PostgreSQL Integration

**Implementation**

```text
tests/integration/generate_postgres_integration_fixture.py
tests/integration/run_postgres_integration.py
```

**Evidence**

The harness:

```text
creates a temporary PostgreSQL database
generates 9 public-safe synthetic CSVs
runs the real warehouse pipeline
checks nine governed core counts
reruns the same batch
verifies SKIPPED state
verifies fingerprint stability
verifies unchanged row counts
drops the temporary database
```

Expected success evidence includes:

```text
PUBLIC_SAFE_FIXTURE=True
DATABASE_CREATED=True
FIRST_STATUS=SUCCESS
SECOND_STATUS=SKIPPED
FINGERPRINT_MATCH=True
ROW_COUNTS_UNCHANGED=True
POSTGRES_INTEGRATION_STATUS=PASS
DATABASE_DROPPED=True
```

**Safe Claim**

> Added a real PostgreSQL synthetic integration harness separate from unit/contract-style pytest coverage.

---

# 8. CI/CD Evidence

## 8.1 GitHub Actions Quality Gates

**Implementation**

```text
.github/workflows/ci.yml
requirements-dev.txt
```

**Hosted Jobs**

```text
Fast Quality Gate
PostgreSQL Integration Gate
```

**Hosted Evidence**

```text
GitHub Actions run: 32726051052
Conclusion: success
155 passed in 0.45s
PostgreSQL integration harness: PASS
```

**Safe Claim**

> Automated regression, Compose validation, and real PostgreSQL synthetic integration through separate GitHub Actions quality gates.

---

## 8.2 CI Failure Investigation and RCA

**Failed Run**

```text
GitHub Actions run: 32725009465
Head commit: b6955392cac389c99f0872f2815307727d6e84a4
Conclusion: failure
```

Both jobs failed in:

```text
Set up Python
```

before tests executed.

**Verified Root Cause**

The workflow enabled:

```yaml
cache: pip
```

without an explicit dependency path, while the repository used:

```text
requirements-dev.txt
```

**Corrective Change**

Commit:

```text
3b4b9966d4263a4731d665ec8fabdf6227c55eee
fix: configure setup-python dependency cache
```

added:

```yaml
cache-dependency-path: requirements-dev.txt
```

to both Python setup blocks.

**Recovery Evidence**

```text
Run 32726051052 = success
155 pytest tests executed successfully
PostgreSQL integration harness executed successfully
```

**Documentation**

```text
docs/reliability/ci_cache_incident_v1.md
```

**Safe Claim**

> Diagnosed a portfolio CI configuration failure from the first failing step, verified the cache-manifest mismatch, applied a scoped fix, and proved recovery through both downstream CI gates.

---

# 9. Architecture and Governance Evidence

## 9.1 As-Built Architecture

**Documentation**

```text
docs/architecture/architecture_v1.md
docs/architecture/architecture_v2.md
```

The v2 document is the as-built architecture reference.

**Safe Claim**

> Documented both the architecture evolution and the as-built architecture of the portfolio pipeline.

---

## 9.2 Warehouse Governance Artifacts

**Documentation**

```text
docs/warehouse/postgresql_warehouse_v1.md
docs/warehouse/postgresql_warehouse_erd_v1.md
docs/warehouse/data_dictionary_v1.md
```

**Safe Claim**

> Produced implementation-aligned warehouse documentation including ERD, data dictionary, schema/constraint design, and runtime behavior.

---

# 10. Portfolio Documentation Crosswalk

| Portfolio Question | Primary Evidence |
|---|---|
| What problem does the architecture solve? | `docs/architecture/architecture_v2.md` |
| What does each warehouse field mean? | `docs/warehouse/data_dictionary_v1.md` |
| How are warehouse entities related? | `docs/warehouse/postgresql_warehouse_erd_v1.md` |
| What are the major Data Quality risks and controls? | `docs/portfolio/data_quality_summary_v1.md` |
| What testing layers exist? | `docs/portfolio/testing_evidence_v1.md` |
| How is identity ambiguity governed? | `docs/data_audit/*identity*` |
| How is matching explained? | `docs/contracts/explainable_matching_contract_v1.md`, `docs/contracts/explainable_matching_v2_contract.md` |
| How are source failures tested? | `docs/reliability/reliability_failure_lab_v1.md` |
| How are operational failures tested? | `docs/reliability/operational_reliability_v2.md` |
| How are late data / watermarks tested? | `docs/reliability/temporal_reliability_v3.md` |
| Is there a real troubleshooting example? | `docs/reliability/ci_cache_incident_v1.md` |
| Where is the full requirement → evidence trace? | `docs/portfolio/portfolio_evidence_map_v1.md` |

---

# 11. Interview Evidence Chains

## 11.1 Master Data / MDM

```text
heterogeneous workbook identity observations
→ canonical candidate adaptation
→ deterministic identity clustering
→ evidence enrichment / corroboration
→ manual-review gate
→ Golden Master promotion
→ alias lineage
→ tests
→ DQ documentation
```

## 11.2 Data Engineering

```text
multiple workbook sources
→ canonical layers
→ governed history
→ PostgreSQL staging
→ constrained core model
→ incremental UPSERT
→ reconciliation
→ marts
→ integration test
→ CI
```

## 11.3 Data Quality / Data Testing

```text
requirement
→ acceptance criteria
→ scenario
→ automated test
→ controlled failure
→ evidence
→ reconciliation
→ regression
```

## 11.4 Reliability / Troubleshooting

```text
hypothesis
→ inject or observe failure
→ detect
→ collect evidence
→ verify cause
→ fix
→ recover
→ rerun
→ reconcile
→ regression
→ prevention
```

## 11.5 Explainable Matching

```text
campaign requirement normalization
→ readiness gate
→ historical features
→ eligibility
→ configurable weighted scoring
→ shortlist
→ explanation
→ human review
→ feedback structure
```

---

# 12. Evidence Boundaries

The repository supports strong evidence for:

```text
Python data transformation
SQL / PostgreSQL warehouse design
multi-file integration
schema normalization
Master Data / entity resolution
deterministic deduplication controls
data modeling
Data Quality
incremental loading
idempotency
audit / lineage-oriented metadata
reconciliation
logging / operational state
reliability testing
controlled failure experiments
pytest regression
real PostgreSQL integration
Docker Compose validation
Git / GitHub
GitHub Actions CI
explainable matching
human review
public-safe portfolio governance
```

The current repository should not be used to claim:

```text
production ownership
customer-impacting incident response
enterprise on-call experience
production SLA / SLO ownership
production Airflow orchestration
production cloud platform operations
Spark / Databricks production implementation
ML production ranking
real campaign outcome labels where they are not available
```

---

# 13. Current Evidence Gaps / Later Extensions

Capabilities that may be added later only when they solve a clear architectural or job-market problem include:

```text
workflow orchestration / scheduling
cloud deployment
dbt-style transformation governance
distributed processing
lakehouse architecture
statistical / ML calibration
```

These are later extensions, not missing proof for the current core portfolio.

---

# 14. Final Traceability Principle

Preferred interview pattern:

```text
Business problem
→ requirement
→ architecture choice
→ implementation
→ test
→ failure path
→ runtime evidence
→ reconciliation
→ limitation
→ business impact
```

Avoid:

```text
I used Python, PostgreSQL, Docker, and GitHub Actions.
```

Prefer:

```text
I used PostgreSQL because the project needed governed historical entities,
explicit relational constraints, repeatable incremental upserts, and
reconciliation. I then tested the same-batch rerun against a real temporary
PostgreSQL database in CI to prove idempotent behavior.
```

Final principle:

```text
technology
→ engineering problem
→ implementation
→ proof
→ explainable claim
```
