# Job Responsibility Mapping v1

## Influencer Campaign Intelligence Pipeline

**Market snapshot date:** 2026-08-25
**Scope:** Thailand — Bangkok / Bangkok Metropolitan Region / Chonburi / Rayong / Hybrid / Remote
**Target roles:** Data Engineer, Data Quality Engineer / Data Tester, Data Integration / ETL Engineer, Master Data / MDM / Data Governance, Analytics Engineer

---

# 1. Purpose

This document maps **current Thailand data-job responsibilities** to evidence already implemented in the Influencer Campaign Intelligence Pipeline.

The traceability model is:

```text
Market Responsibility
→ Project Implementation
→ Test / Runtime Evidence
→ Coverage Strength
→ Gap
→ Interview-Safe Claim
```

The goal is not to maximize tool keywords. A technology is only valuable when it solves a real engineering problem.

```text
Airflow
→ scheduling / dependencies / retry / recovery

dbt
→ transformation governance / model tests / lineage / documentation

Cloud
→ managed execution / IAM / monitoring / scaling / deployment

Spark / Databricks
→ distributed processing / lakehouse workloads when scale justifies it
```

---

# 2. Claim Boundary

This is a **portfolio / production-like engineering lab**.

It does not represent:

```text
production ownership
enterprise on-call experience
customer-impacting incident response
production SLA / SLO ownership
enterprise MDM program ownership
production Airflow ownership
production cloud operations
production Spark / Databricks implementation
production ML ranking
```

The project can demonstrate implementation choices, test discipline, controlled failure experiments, troubleshooting, reconciliation, and explainable reasoning.

---

# 3. Research Method

The market mapping was created through five research passes.

## Round 1 — Data Engineer

Reviewed responsibilities around:

```text
ETL / ELT
Python
SQL
data pipeline
data warehouse
data model
data quality
monitoring
troubleshooting
documentation
cloud
orchestration
CI/CD
```

## Round 2 — Data Quality / Data Testing

Reviewed responsibilities around:

```text
source-to-target validation
duplicate / missing / invalid detection
SQL reconciliation
Python test scripting
automated DQ
DQ controls / metrics
lineage
RCA
remediation
test strategy
```

## Round 3 — MDM / Governance / Analytics Engineering

Reviewed:

```text
master-data models
business rules
stewardship
data lineage
metadata
privacy / PDPA
trusted models
dbt
automated model testing
documentation
auditability
```

## Round 4 — Geographic / Work-Mode Check

Reviewed:

```text
Bangkok
Bangkok Metropolitan Region
Hybrid
Remote
Chonburi
Rayong
```

## Round 5 — Source Coverage Check

Sources successfully used:

```text
LinkedIn Jobs
JobThai
JobsDB
```

JobsBKK was also searched for current Data Engineer / Data Quality / ETL combinations, but no sufficiently reliable indexed result was returned.

> No JobsBKK responsibility is fabricated or inferred in this document.

---

# 4. Repeated Market Responsibilities

Across the reviewed Thailand roles, the most repeated responsibilities were:

```text
build and maintain ETL / ELT pipelines
integrate multiple sources
write SQL
write Python
design data models
work with warehouses / lakes
ensure data quality and reliability
perform validation and reconciliation
monitor pipelines
troubleshoot failures
document systems and lineage
translate business requirements
automate checks and workflows
```

More advanced or company-specific requirements frequently included:

```text
Airflow / Dagster / Cloud Composer
dbt
AWS / GCP / Azure
BigQuery / Redshift / Databricks
Spark / PySpark
Kafka / streaming
Great Expectations / Soda / observability tooling
Terraform / IaC
data catalogs
SAP MDG / enterprise MDM
```

---

# 5. Role Fit Summary

| Target Role | Core Portfolio Fit | Reason |
|---|---|---|
| Data Quality / Data Tester | Very Strong | Reconciliation, DQ controls, negative/boundary tests, reliability labs, identity review, CI regression |
| Junior–Mid Data Engineer | Strong | Python/SQL, multi-file ETL, PostgreSQL warehouse, incremental/idempotency, testing, Docker, CI, troubleshooting |
| Data Integration / ETL Engineer | Strong | Multi-source normalization, schema mapping, history integration, PostgreSQL loading, reconciliation, failure recovery |
| Master Data / MDM / Governance | Strong domain fit | Entity resolution, Golden Master, aliases, manual review, quarantine, PII boundary, contracts, traceability |
| Analytics Engineer | Moderate–Strong fundamentals | SQL modeling, marts, tests, documentation, lineage; dbt/cloud implementation remains a gap |

These are qualitative portfolio-fit assessments, not hiring probabilities.

---

# 6. Data Quality Engineer / Data Tester

## 6.1 Market Responsibilities

Current Thailand Data Quality / Data Tester roles ask for work such as:

```text
validate ETL pipelines source-to-target
detect duplicate records
detect missing data
detect invalid formats
compare large datasets with SQL
write Python reconciliation scripts
automate quality checks
define DQ controls and metrics
monitor DQ health
investigate quality issues
analyze lineage
perform RCA
recommend remediation
design testing strategy
collaborate with Data Engineers and business teams
```

A recent Senior Data Tester role in Bangkok explicitly includes source-to-target ETL validation, duplicate/missing/invalid checks, advanced SQL, Python reconciliation, automated DQ, and test-strategy design.

A recent Data Governance / Quality Engineer role includes DQ technical rules, controls/metrics, profiling/cleansing, lineage analysis, RCA, remediation, metadata, and governance documentation.

## 6.2 Project Evidence

### Data Quality Controls

```text
docs/portfolio/data_quality_summary_v1.md
src/pii_guard.py
tests/test_pii_guard.py
```

### Automated Regression

```text
23 pytest files
155 automated Python tests
```

The 155-test number is repository-wide. It is **not** 155 DQ-only tests, integration tests, or end-to-end tests.

### Warehouse Reconciliation

```text
sql/postgres/005_reconciliation.sql
docs/portfolio/testing_evidence_v1.md
```

Checks include:

```text
row-count validation
FK orphan detection
business-key duplicate checks
same-batch stability
fingerprint stability
```

### Source / Schema Failure Testing

```text
docs/reliability/reliability_failure_lab_v1.md
tests/test_reliability_lab.py
```

Controlled cases include:

```text
missing workbook
duplicate workbook
empty expected candidate sheet
schema drift
column rename
same-batch rerun
```

### Operational / Temporal Testing

```text
docs/reliability/operational_reliability_v2.md
docs/reliability/temporal_reliability_v3.md
tests/test_operational_reliability.py
tests/test_temporal_reliability.py
```

### Identity Quality

```text
docs/data_audit/identity_review_evidence_policy.md
docs/data_audit/identity_review_corroboration_v1.md
docs/data_audit/manual_identity_review_contract.md
```

## 6.3 Responsibility Mapping

| Market Responsibility | Project Evidence | Coverage |
|---|---|---|
| Source-to-target validation | canonical adapters, history builders, warehouse reconciliation | Strong |
| Duplicate detection | source duplicate scenarios, identity rules, business-key checks | Strong |
| Missing / invalid checks | schema/DQ tests and failure labs | Strong |
| SQL reconciliation | PostgreSQL reconciliation migration | Strong |
| Python test automation | pytest suite and reliability harnesses | Strong |
| DQ controls | PII, schema, identity, relational, temporal controls | Strong |
| Negative testing | controlled failure labs | Strong |
| Regression testing | 155-test baseline | Strong |
| RCA | CI cache incident + failure-lab methodology | Strong portfolio evidence |
| Great Expectations / Soda | not implemented | Gap |
| Enterprise DQ observability | not implemented | Gap |

## 6.4 Interview-Safe Claim

> I designed Data Quality as multiple control layers rather than one validation step. The portfolio covers schema issues, missing/duplicate/invalid inputs, entity ambiguity, relational reconciliation, rerun correctness, late-data behavior, controlled failures, and regression testing.

Do not claim enterprise Great Expectations platform ownership.

---

# 7. Junior–Mid Data Engineer

## 7.1 Market Responsibilities

Recent Thailand Data Engineer postings repeatedly request:

```text
design ETL / ELT pipelines
maintain pipelines
integrate multiple sources
Python
SQL
data warehousing
data modeling
data quality
monitoring
troubleshooting
documentation
business-requirement translation
cloud familiarity
workflow automation
```

Some current junior roles explicitly accept GitHub / small-scale ETL portfolio evidence.

## 7.2 Project Evidence

### Multi-Source Integration

```text
12 heterogeneous source workbooks
src/discover_sources.py
src/xlsx_probe.py
src/build_sheet_inventory.py
src/sheet_classifier.py
```

### Canonical Transformation

```text
src/candidate_adapter.py
src/extract_candidate_observations.py
src/build_resolved_candidate_observations.py
docs/contracts/canonical_data_contract_v1.md
```

### PostgreSQL Warehouse

```text
sql/postgres/001_schemas_and_helpers.sql
sql/postgres/002_staging_tables.sql
sql/postgres/003_core_tables.sql
sql/postgres/004_incremental_upserts.sql
sql/postgres/005_reconciliation.sql
sql/postgres/006_mart_views.sql
```

Validated warehouse baseline:

```text
6530 governed rows
703 dim_influencer
2519 identity aliases
12 brands
19 campaigns
19 campaign requirements
989 campaign × influencer facts
494 deliverables
515 influencer performance rows
1260 campaign performance rows
```

### Incremental / Idempotency

```text
batch fingerprint
same-batch detection
same-batch SKIPPED
unchanged row counts
```

### Testing / CI

```text
155 pytest tests
real PostgreSQL synthetic integration harness
GitHub Actions Fast Quality Gate
GitHub Actions PostgreSQL Integration Gate
```

### Troubleshooting

```text
docs/reliability/ci_cache_incident_v1.md
```

## 7.3 Responsibility Mapping

| Market Responsibility | Project Evidence | Coverage |
|---|---|---|
| Python | pipeline / matching / reliability implementation | Strong |
| SQL | PostgreSQL DDL, UPSERT, reconciliation, marts | Strong |
| ETL / ELT | multi-file transformation → PostgreSQL | Strong |
| Multi-source integration | 12 workbook sources / schema variants | Strong |
| Data modeling | master + history + warehouse facts/dims | Strong |
| Warehouse | PostgreSQL warehouse | Strong |
| Data quality | multi-layer DQ + reconciliation | Strong |
| Incremental loading | UPSERT + batch state | Strong |
| Idempotency | same-batch skip + stable counts | Strong |
| Testing | 155 tests + DB integration | Strong |
| CI/CD | GitHub Actions | Strong |
| Docker | PostgreSQL container / persistence lab | Strong |
| Troubleshooting | failure labs + CI RCA | Strong |
| Documentation | architecture, ERD, dictionary, DQ, testing, evidence map | Strong |
| Airflow orchestration | not core yet | Gap |
| Cloud deployment | not core yet | Gap |
| Spark / Databricks | not core yet | Gap |

## 7.4 Interview-Safe Claim

> I built a multi-source Python/SQL pipeline from heterogeneous workbooks into governed history and a PostgreSQL warehouse, then added incremental upserts, same-batch idempotency, reconciliation, automated tests, Docker validation, and CI.

Do not claim production cloud Data Engineering experience from this project.

---

# 8. Data Integration / ETL Engineer

## 8.1 Market Responsibilities

Integration-oriented roles emphasize:

```text
connect heterogeneous sources
build ingestion flows
map schemas
migrate or transform data
validate movement between systems
reconcile outputs
handle failures
automate repetitive work
monitor jobs
document mappings / processes
```

## 8.2 Project Evidence

```text
multiple brands / campaigns / workbook structures
canonical schema mapping
deterministic identity resolution
campaign / performance history integration
public-safe stage CSV → PostgreSQL staging → core → marts
reconciliation and same-batch checks
```

## 8.3 Responsibility Mapping

| Market Responsibility | Project Evidence | Coverage |
|---|---|---|
| Heterogeneous-source integration | 12 workbook sources | Strong |
| Schema mapping | canonical adapter / contracts | Strong |
| Data transformation | Python layers | Strong |
| Database loading | PostgreSQL runtime | Strong |
| Migration-style reconciliation | reconciliation SQL + synthetic DB harness | Strong |
| Retry / rerun reasoning | reliability labs + idempotency | Strong |
| Error handling | controlled source/operational tests | Strong |
| File integration | Excel → canonical | Strong |
| API ingestion | not implemented | Gap |
| SFTP ingestion | not implemented | Gap |
| Enterprise integration middleware | not implemented | Gap |
| Streaming integration | not implemented | Gap |

## 8.4 Interview-Safe Claim

> The project demonstrates integration patterns across heterogeneous workbook schemas, deterministic entity consolidation, historical fact construction, and governed PostgreSQL loading with reconciliation.

---

# 9. Master Data / MDM / Data Governance

## 9.1 Market Responsibilities

Current Thailand MDM / governance roles ask for:

```text
master-data models
business rules
data standards
data quality
consistency
accuracy
stewardship
cleanup
data lifecycle
metadata
lineage
privacy / PDPA
cross-system alignment
governance processes
```

More enterprise-focused positions add:

```text
SAP master data
SAP MDG
Collibra
Alation
enterprise governance frameworks
vendor management
governance councils
```

## 9.2 Project Evidence

### Deterministic Entity Resolution

```text
src/build_deterministic_identity_clusters.py
src/corroborate_identity_review.py
src/build_identity_review_queue.py
src/validate_identity_review_decisions.py
```

### Golden Master

```text
src/promote_golden_master.py
docs/contracts/golden_master_promotion_contract_v1.md
```

### Validated Master Evidence

```text
703 influencer master records
2519 aliases
163 cross-workbook masters
8 reviewed / promoted groups
4 quarantined groups
```

### Review Evidence

```text
12 identity review groups
4 independently corroborated
7 without independent exact corroboration
1 without parseable handle
auto-resolution disabled for review groups
```

### PII / Governance Boundary

```text
src/pii_guard.py
.env.example
.gitignore
public-safe synthetic integration fixture
```

## 9.3 Responsibility Mapping

| Market Responsibility | Project Evidence | Coverage |
|---|---|---|
| Master entity design | influencer Golden Master | Strong domain evidence |
| Deterministic deduplication | identity rules | Strong |
| Alias mapping | 2519 aliases | Strong |
| Ambiguity governance | review queue / manual gate | Strong |
| Master-data quality | promotion / quarantine rules | Strong |
| Cross-source consistency | cross-workbook identity | Strong |
| Data rules / contracts | contracts + code/tests | Strong |
| PII awareness | explicit private/public boundary | Strong portfolio evidence |
| Enterprise stewardship operating model | not implemented | Gap |
| SAP master data | not implemented | Gap |
| SAP MDG | not implemented | Gap |
| Collibra / Alation | not implemented | Gap |
| Enterprise governance council | not implemented | Gap |

## 9.4 Interview-Safe Claim

> I implemented Master Data and deterministic entity-resolution patterns for an influencer domain, including Golden Master promotion, alias lineage, ambiguity review, and quarantine controls.

Do not claim enterprise MDM or SAP MDG implementation.

---

# 10. Analytics Engineer

## 10.1 Market Responsibilities

Current Bangkok Analytics Engineer / Data Platform roles emphasize:

```text
strong SQL
trusted transformation models
dbt
data warehouse concepts
gold / curated datasets
testing
documentation
traceability
semantic clarity
Git
cloud data platforms
```

A current Bangkok Analytics Engineer role specifically focuses on dbt + SQL, Azure Databricks, trusted gold datasets, testing, documentation, traceability, and audit-ready models.

JobsDB also shows Bangkok roles for ELT pipelines, dbt models/tests, data-quality SLAs, and AWS orchestration.

## 10.2 Project Evidence

```text
PostgreSQL staging / core / marts
Golden Master
Campaign History
Performance History
Historical Features
155 tests
reconciliation
PostgreSQL integration
CI
architecture / ERD / data dictionary / DQ / testing / evidence map
```

## 10.3 Responsibility Mapping

| Market Responsibility | Project Evidence | Coverage |
|---|---|---|
| SQL | PostgreSQL migrations | Strong |
| Data models | facts/dims + marts | Strong |
| Trusted datasets | master/history layers | Strong |
| Data testing | pytest + reconciliation | Strong |
| Documentation | extensive evidence artifacts | Strong |
| Traceability | contracts + evidence map | Strong |
| Git / CI | GitHub + Actions | Strong |
| dbt models | not implemented | Gap |
| dbt tests/docs | not implemented | Gap |
| Cloud warehouse | not implemented | Gap |
| Databricks | not implemented | Gap |
| Semantic / metrics layer | not implemented | Gap |

## 10.4 Interview-Safe Claim

> The project already demonstrates the SQL modeling, trusted-data, testing, documentation, and traceability foundations of Analytics Engineering, but it does not yet implement dbt or a cloud warehouse.

---

# 11. Reliability / Troubleshooting Alignment

Reliability appears repeatedly inside Data Engineer and Data Quality responsibilities.

Common market language:

```text
monitor
troubleshoot
resolve pipeline issues
ensure reliability
detect anomalies
perform RCA
reduce incidents
write runbooks
```

Project evidence:

```text
Source reliability: 5 / 5 controlled scenarios
Operational reliability: 4 / 4 controlled experiments
Temporal reliability: 5 / 5 controlled experiments
Temporal rows: 287
Hosted CI incident: evidence-based RCA and recovered CI
```

The CI incident is real portfolio troubleshooting evidence. It is not a production incident or controlled failure experiment.

---

# 12. Explainable Matching as Business-Value Evidence

The matching layer matters because it shows that trusted engineering outputs support a business decision.

```text
trusted master
→ campaign history
→ performance history
→ normalized campaign requirements
→ historical features
→ eligibility
→ weighted ranking
→ human review
→ feedback structure
```

Validated evidence:

```text
703 historical feature rows
570 eligible influencers in v1
30 shortlist rows in v1
8436 score rows in v2
360 shortlist rows in v2
0 leakage-audit failures
```

Interview-safe explanation:

> I first built trusted data and history, then used eligibility rules and configurable weighted ranking. Historical replay and leakage controls were added before considering statistical or ML calibration.

---

# 13. Geographic Alignment

## Bangkok / Bangkok Metropolitan Region

The largest current sample is concentrated in Bangkok and the metropolitan area.

Repeated requirements:

```text
SQL
Python
ETL / ELT
data model
warehouse
quality
monitoring
troubleshooting
cloud
Airflow / dbt in some roles
```

The current core portfolio aligns strongly with the first eight items. Cloud/orchestration are explicit extension areas.

## Chonburi

A reviewed Chonburi Data Engineer role includes:

```text
multi-source ETL / ELT
PLC / CNC / IoT
MES / ERP / CMMS
CSV / Excel
DWH / lakehouse
schema design
SCD
metadata
DQ monitoring
streaming
```

Transferable project evidence:

```text
multi-source ingestion
Excel integration
schema design
historical modeling
DQ controls
```

Not proven:

```text
industrial IoT
MES
real-time streaming
```

## Rayong

A reviewed Rayong Data Engineer / BI role includes:

```text
strong SQL
large datasets
query optimization
database structures
schema design
PostgreSQL
ETL / ELT
pipeline design
fact / dimension modeling
star schema
```

This overlaps directly with the core warehouse work.

## Hybrid / Remote

Current sources include multiple Bangkok hybrid roles and a Rayong-linked WFH listing.

The project itself is not evidence of remote-work experience. Git/GitHub/CI/documentation are only supporting evidence for reproducible collaboration.

---

# 14. Tool Decision Matrix

| Tool / Skill | Market Problem | Current Evidence | Decision |
|---|---|---|---|
| Python | transformation, automation, validation, pipeline logic | Strong | Keep core |
| SQL / PostgreSQL | warehouse, reconciliation, modeling | Strong | Keep core |
| Git / GitHub / CI | versioning, automated quality gates | Strong | Keep core |
| Docker | repeatable DB environment, persistence/recovery lab | Strong lab evidence | Keep core |
| Airflow | scheduling, dependency, retry, recovery | Not implemented | Strong Phase 15 candidate |
| dbt | transformation governance, tests, docs, lineage | Not implemented | Useful for Analytics Engineer later |
| Cloud | managed execution, IAM, monitoring, deployment | Not implemented | Separate later extension |
| Spark / Databricks | distributed processing / lakehouse | Not implemented | Add only with scale/job justification |
| Great Expectations / Soda | standardized reusable DQ framework | Custom DQ exists; framework absent | Optional later extension |

---

# 15. Application Strategy

## Highest-Priority Role Family

```text
Data Quality Engineer
Data Tester
ETL / Data Tester
Data Engineer with strong DQ responsibility
```

Why:

```text
validation
negative testing
reconciliation
data correctness
schema drift
identity ambiguity
failure injection
RCA
rerun
regression
```

## Strong Role Family

```text
Junior Data Engineer
Data Engineer
Data Integration Engineer
ETL Developer / ETL Engineer
```

Best fit where postings emphasize:

```text
Python
SQL
ETL / ELT
PostgreSQL / relational databases
warehouse
data quality
testing
troubleshooting
documentation
```

## Strong Adjacent Role Family

```text
Master Data Analyst
MDM Analyst
Data Governance Engineer
Data Steward
Data Management Specialist
```

Best fit where responsibilities emphasize:

```text
data quality
master records
business rules
matching / mapping
consistency
cleanup
validation
stewardship
lineage
```

More selective when deep SAP MDG / Collibra / Alation ownership is mandatory.

## Conditional Role Family

```text
Analytics Engineer
Data Platform Engineer
Modern Data Stack Engineer
```

Apply when dbt/cloud are preferred or learnable. Be more selective when production dbt/Databricks/cloud experience is a hard requirement.

---

# 16. Resume / Portfolio Claim Library

## Data Engineering

> Built a Python/SQL data pipeline integrating heterogeneous Excel workbooks into governed master, campaign, performance, and PostgreSQL warehouse layers.

## Data Modeling

> Designed a relational warehouse with governed master entities, campaign/performance facts, constraints, marts, and documented ERD/data dictionary.

## Incremental Loading

> Implemented PostgreSQL incremental upserts with deterministic batch fingerprints and same-batch idempotency.

## Reconciliation

> Added post-load reconciliation for row counts, orphan relationships, duplicate business keys, and rerun stability.

## Data Quality

> Implemented layered Data Quality controls covering source/schema failures, identity ambiguity, relational integrity, PII boundaries, temporal behavior, and regression tests.

## Testing

> Maintained a 155-test Python regression baseline and a separate real PostgreSQL synthetic integration harness.

## Reliability

> Built controlled source, operational, and temporal failure labs covering detection, evidence, recovery, rerun, reconciliation, and prevention.

## Troubleshooting

> Diagnosed a hosted CI failure from logs, verified the dependency-cache root cause, applied a scoped fix, and proved recovery through regression and PostgreSQL integration gates.

## Master Data

> Implemented deterministic influencer entity resolution with evidence corroboration, manual-review gates, Golden Master promotion, alias lineage, and quarantine controls.

## CI/CD

> Automated Python regression, Compose validation, and real PostgreSQL synthetic integration with GitHub Actions.

## Explainable Matching

> Built eligibility-first and configuration-driven influencer ranking using governed historical evidence, with human review and historical leakage controls.

---

# 17. Claims to Avoid

Avoid:

```text
production-grade system
production incident
enterprise MDM implementation
production cloud architecture
Airflow expert
dbt expert
Spark expert
Databricks expert
ML ranking system
real-time streaming platform
enterprise Data Governance owner
```

Prefer:

```text
portfolio implementation
production-like lab
controlled failure experiment
real PostgreSQL integration
hosted CI
deterministic master-data patterns
explainable rule-based ranking
public-safe synthetic test fixture
```

---

# 18. Gap Register

## Gap A — Orchestration

```text
Current:
script-level execution + CI

Market:
Airflow / Dagster / Cloud Composer common in many DE roles

Action:
Phase 15 can add orchestration around real existing pipeline steps,
dependency, retry, failure, recovery, idempotency, and PostgreSQL state.
```

Priority: **High after core portfolio completion**

## Gap B — Cloud

```text
Current:
local PostgreSQL + Docker + hosted CI

Market:
AWS / GCP / Azure common

Action:
separate cloud extension after orchestration
```

Priority: **High for broader DE market**

## Gap C — dbt

```text
Current:
SQL migrations + marts + tests + documentation

Market:
strong in Analytics Engineer / modern-stack roles

Action:
add only if transformation ownership moves deliberately into dbt
```

Priority: **Medium–High for Analytics Engineer**

## Gap D — Distributed Processing

```text
Current:
dataset does not require distributed compute

Market:
Spark / Databricks common in senior / lakehouse roles

Action:
defer until scale or target role justifies it
```

Priority: **Medium**

## Gap E — Enterprise Governance Tooling

```text
Current:
contracts, lineage-oriented evidence, PII boundary, MDM rules

Market:
Collibra / Alation / Informatica / SAP MDG in specialized roles

Action:
do not simulate enterprise ownership without a justified use case
```

Priority: **Low for core DE; higher only for specialized governance/MDM targets**

---

# 19. Market Sources

This is a time-bound snapshot. Job advertisements may change or close.

## S1 — Amaris Consulting — Data Governance / Quality Engineer

Platform: LinkedIn Jobs
Location: Bangkok
Observed responsibilities: DQ technical rules, controls/metrics/monitoring, profiling/cleansing, lineage, RCA, remediation, metadata/governance, SQL, Python or similar.
Source: https://www.linkedin.com/jobs/view/4426310275/

## S2 — Senior Data Tester (Hybrid)

Platform: JobThai
Location: Chatuchak, Bangkok
Observed responsibilities: ETL source-to-target validation, duplicate/missing/invalid detection, advanced SQL, Python reconciliation, automated DQ, test strategy.
Source: https://www.jobthai.com/en/job/1936835

## S3 — Infinitas by Krungthai — Data Engineer

Platform: LinkedIn Jobs
Location: Bangkok
Observed responsibilities: ETL/ELT, data models, automated validation, lineage documentation, Python, SQL, cloud familiarity, portfolio/GitHub evidence.
Source: https://www.linkedin.com/jobs/view/4442015858/

## S4 — Jaymart Group — Data Engineer

Platform: JobThai
Location: Bangkok
Observed responsibilities: ETL, Web Service/SFTP, multi-source integration, Customer 360, reliability, DQ, Python migration, governance, documentation, monitoring.
Source: https://www.jobthai.com/en/job/1933547

## S5 — ASCGroup — Data Engineer Contract / Hybrid

Platform: JobThai
Location: Bangkok / Hybrid
Observed responsibilities: pipelines, ETL, SQL optimization, PostgreSQL/other RDBMS, Python/Java transformation, AWS, business collaboration, technical documentation.
Source: https://www.jobthai.com/company/job/1942236

## S6 — JobsDB Bangkok dbt / Data Engineer market

Platform: JobsDB
Location: Bangkok / Hybrid
Observed examples: Python, SQL, Airflow, dbt, BigQuery, ELT, dbt models/tests, DQ SLAs, AWS orchestration.
Source: https://th.jobsdb.com/dbt-jobs/in-Chatuchak%2C-Bangkok

## S7 — Brand New Day — Analytics Engineer

Platform: LinkedIn Jobs
Location: Bangkok
Observed responsibilities: dbt, SQL, Azure Databricks, trusted gold datasets, testing, documentation, traceability, audit-ready models.
Source: https://www.linkedin.com/jobs/view/4385235970/

## S8 — Thai Union Group — Data Governance & Management Specialist

Platform: LinkedIn Jobs
Location: Bangkok
Observed responsibilities: governance strategy, MDM architecture, models/schemas/business rules, master-data accuracy/consistency, cleanup, DQ standards, PDPA/privacy, SAP master data / SAP MDG preference.
Source: https://www.linkedin.com/jobs/view/4436551053/

## S9 — Rapida Solutions — Master Data & POS Analyst

Platform: LinkedIn Jobs
Location: Bangkok / Hybrid
Observed responsibilities: master data, cross-system consistency, mapping, data requirements, governance standards, DQ controls, validation, incidents, workflow improvement.
Source: https://th.linkedin.com/jobs/view/master-data-pos-analyst-at-rapida-solutions-4430394408

## S10 — Metro Systems — Data Engineer / BI Developer

Platform: JobThai
Location: Rayong
Observed responsibilities: SQL, query performance, schema design, PostgreSQL, ETL/ELT, pipeline design, fact/dimension modeling, star schema.
Source: https://www.jobthai.com/company/job/1885993

## S11 — Reeracoen Eastern Seaboard — Data Engineer

Platform: JobThai
Location: Chonburi
Observed responsibilities: multi-source ETL/ELT, industrial systems, CSV/Excel, DWH/lakehouse, schema design, SCD, metadata, DQ monitoring, streaming.
Source: https://www.jobthai.com/th/job/1859834

## S12 — JobsDB Bangkok Data Engineer market

Platform: JobsDB
Location: Bangkok / Hybrid
Observed examples: Python, SQL, Airflow, dbt, BigQuery, pipeline architecture, data marts, cloud.
Source: https://th.jobsdb.com/data-engineer-jobs/in-Bangkok/full-time

---

# 20. Source Limitations

```text
job boards are dynamic
some postings may close after the snapshot date
search-index freshness differs by platform
not every role exposes its full description publicly
job-board results pages may summarize postings
salary was not used for fit scoring
job-title frequency was not treated as responsibility frequency
```

JobsBKK limitation:

```text
JobsBKK was searched in this research round.
No sufficiently reliable indexed result was returned for the target queries.
No JobsBKK responsibilities were invented.
```

---

# 21. Portfolio Positioning

The strongest positioning is not:

> I know many tools.

The stronger positioning is:

> I can turn messy multi-source business data into trusted master and historical data, persist it in a governed warehouse, validate correctness, handle reruns and failure paths, troubleshoot evidence-first, and expose explainable business outputs.

That story directly supports:

```text
Data Engineering
+
Data Quality Engineering
+
Data / ETL Testing
+
Data Integration
+
Master Data
```

Analytics Engineering is a credible adjacent direction, with dbt/cloud remaining visible gaps.

---

# 22. Recommended Core Portfolio Headline

> **Influencer Master Data & Campaign Intelligence Pipeline — Python, SQL/PostgreSQL, Data Quality, Entity Resolution, Incremental Loads, Reliability Testing, Explainable Matching, Docker, GitHub Actions**

Avoid adding Airflow, dbt, Spark, Databricks, AWS, GCP, or Azure to the headline until they are implemented and validated.

---

# 23. Final Market Alignment Statement

Current Thailand job evidence supports keeping the core project centered on:

```text
Python
SQL
PostgreSQL
ETL / ELT
multi-source integration
schema mapping
Master Data
entity resolution
data modeling
Data Quality
incremental loading
idempotency
reconciliation
testing
reliability
troubleshooting
documentation
Git
Docker
CI
```

The most valuable next extension after the core portfolio is complete is likely Airflow orchestration because it can solve existing project problems around scheduling, dependencies, retry, failure propagation, recovery, rerun, same-batch idempotency, and operational evidence.

Cloud should remain a separate later extension.

dbt is particularly relevant if the target role shifts toward Analytics Engineering.

Spark / Databricks should remain deferred until the architecture or target job genuinely requires distributed processing.

---

# 24. Interview Principle

Use this structure:

```text
Business Problem
→ Data Risk
→ Architecture Decision
→ Implementation
→ Test
→ Failure Path
→ Runtime Evidence
→ Reconciliation
→ Limitation
→ Business Value
```

This is stronger than listing technology names because it demonstrates engineering judgment rather than a tool checklist.
