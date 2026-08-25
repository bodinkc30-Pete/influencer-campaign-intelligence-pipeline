# Influencer Master Data & Campaign Intelligence Pipeline

**Portfolio Data Engineering project:** transform heterogeneous multi-brand / multi-campaign Excel data into a trusted Influencer Master, governed campaign and performance history, a PostgreSQL warehouse, and explainable campaign matching.

> This repository is a **portfolio / production-like engineering lab**. It demonstrates engineering design, testing, failure handling, reconciliation, and troubleshooting. It does **not** represent production ownership, enterprise on-call experience, or customer-impacting incident response.

---

## What this project proves

```text
Messy multi-workbook business data
→ Discover and classify sources
→ Normalize schema variants
→ Enforce Data Quality and PII boundaries
→ Resolve identities deterministically
→ Promote a governed Golden Master
→ Build campaign / deliverable / performance history
→ Persist governed data in PostgreSQL
→ Reconcile incremental loads and reruns
→ Build explainable historical matching
→ Test happy paths + failure paths
→ Troubleshoot and prove recovery
→ Document evidence and limitations
```

The engineering objective is not merely:

```text
Pipeline ran successfully
```

It is:

```text
Build
→ Operate
→ Test
→ Break intentionally
→ Troubleshoot with evidence
→ Recover
→ Reconcile
→ Regression test
→ Govern
→ Explain
```

Core principle:

> **Pipeline SUCCESS != Data Correct**

---

# Business Problem

Historical influencer campaign information is distributed across multiple brands, campaigns, periods, workbook layouts, and sheet conventions.

The source domain contains problems typical of real integration and Master Data work:

```text
different workbook schemas
variable headers
repeated sections
inconsistent field names
duplicate identities
TikTok handle / URL / alias variants
ambiguous creator identities
missing campaign requirements
conflicting status / fee observations
mixed metric grains
late / malformed dates
PII and internal business information
```

If these files are joined directly, the result can silently create:

```text
duplicate influencers
incorrect campaign history
incorrect performance attribution
metric fanout
identity leakage
PII exposure
non-idempotent reruns
unexplainable recommendations
```

This project treats the Excel files as **source evidence**, not trusted master data.

---

# As-Built Architecture

```text
Private Multi-Brand Excel
        │
        ▼
Source Discovery + Registry
        │
        ▼
Workbook / Sheet Inventory
        │
        ▼
Schema Classification + Canonical Adaptation
        │
        ▼
Data Quality Gate
        │
        ├──────────────► Quarantine / Review
        │
        ▼
PII-Safe Candidate Observations
        │
        ▼
Deterministic Entity Resolution
        │
        ├──────────────► Manual Identity Review
        │
        ▼
Golden Influencer Master + Alias Lineage
        │
        ├──────────────► Campaign History
        ├──────────────► Deliverable History
        └──────────────► Performance History
                            │
                            ▼
                    Historical Features
                            │
          Campaign Requirements + Fit Readiness
                            │
                            ▼
                 Explainable Matching v1/v2
                            │
                            ▼
                     Human Review
                            │
                            ▼
                      Feedback Model

Governed analytical layers
        │
        ▼
PostgreSQL
  stg  →  core  →  mart
          │
          └────► ops
                 runs / incremental state / DQ evidence

Cross-cutting controls:
DQ • PII • Idempotency • Reconciliation • Logging • Testing • CI • Reliability
```

See the full as-built architecture:

- [Architecture v2](docs/architecture/architecture_v2.md)
- [PostgreSQL Warehouse ERD](docs/warehouse/postgresql_warehouse_erd_v1.md)
- [PostgreSQL Data Dictionary](docs/warehouse/data_dictionary_v1.md)

---

# Verified Evidence Snapshot

The numbers below are **validated project evidence**, not invented demo metrics.

## Master Data

```text
703   Golden Influencer Master records
2,519 identity alias / provenance rows
163   Golden Master records represented across multiple workbooks
8     reviewed identity groups promoted
4     ambiguous groups quarantined
```

Identity review remains deterministic-first.

```text
Normalize
→ Exact Match
→ Deterministic Rules
→ Evidence Corroboration
→ Manual Review
→ Golden Master Promotion
```

**Fuzzy similarity is not permission to auto-merge records.**

---

## Campaign and Performance History

```text
12    brands
19    campaign source instances
19    campaign requirement records
989   campaign × influencer facts
494   canonical deliverables
515   influencer performance rows
1,260 campaign-level performance rows
```

Performance is kept at its correct business grain.

For example:

```text
content views
≠ live viewers

GMV
≠ sales amount
≠ revenue

campaign-level performance
≠ influencer-level performance
```

---

## Historical Features and Matching

```text
703   historical feature rows
12    campaigns ready for rule-based fit
8,436 historical replay score rows
360   shortlist rows
0     target-campaign leakage audit failures
```

Matching remains:

```text
Eligibility Rules
→ Configurable Weighted Ranking
→ Explainable Components
→ Deterministic Rank
→ Human Review
```

It is **not** presented as production ML recommendation accuracy.

---

## PostgreSQL Warehouse

Validated governed core baseline:

```text
6,530 total core rows

703   dim_influencer
2,519 influencer_identity_alias
12    dim_brand
19    dim_campaign
19    campaign_requirement
989   fact_campaign_influencer
494   fact_campaign_deliverable
515   fact_influencer_performance
1,260 fact_campaign_performance
```

Warehouse fingerprint from the validated full-data lab:

```text
38f8a4c24dd20d4098f0f581156fc53abbd1b82dcdb53e169f20826de90a3db5
```

---

## Automated Testing

```text
23  pytest test files
155 automated Python tests
```

Important boundary:

> **155 tests is the repository-wide pytest baseline. It is not 155 integration tests and not 155 Data Quality-only tests.**

A **separate real PostgreSQL integration harness** validates the database runtime with synthetic public-safe data.

---

# Source Discovery and Canonicalization

Source processing starts before transformation.

Key implementation:

```text
src/discover_sources.py
src/xlsx_probe.py
src/build_sheet_inventory.py
src/sheet_classifier.py
src/candidate_adapter.py
src/extract_candidate_observations.py
src/build_resolved_candidate_observations.py
```

The pipeline handles source conditions such as:

```text
variable header rows
repeated sections
schema variants
renamed columns
empty expected sheets
duplicate workbook content
missing expected workbooks
```

The canonical layer is governed by explicit contracts instead of ad-hoc column renaming.

See:

- [Canonical Data Contract](docs/contracts/canonical_data_contract_v1.md)
- [Sheet Classification Evidence](docs/data_audit/sheet_classification_v1.md)

---

# Data Quality Strategy

Data Quality is implemented as multiple gates rather than one final validation step.

```text
Source DQ
→ Schema DQ
→ Canonical DQ
→ Identity DQ
→ Master Promotion DQ
→ Historical DQ
→ PostgreSQL Constraint DQ
→ Reconciliation
→ Temporal DQ
→ Matching Leakage DQ
→ Regression Tests
```

Examples covered:

```text
missing values
duplicates
invalid formats
schema drift
renamed columns
duplicate workbook hashes
empty source sheets
ambiguous identities
invalid master promotion
orphan relationships
duplicate business keys
same-batch reruns
partial-load states
bad incremental state
late-arriving data
watermark errors
matching target leakage
```

For a compact summary:

- [Data Quality Summary v1](docs/portfolio/data_quality_summary_v1.md)
- [Testing Evidence v1](docs/portfolio/testing_evidence_v1.md)

---

# Deterministic Entity Resolution and Golden Master

Influencer identity is one of the highest-risk parts of the domain.

A creator can appear as:

```text
@handle
handle
TikTok profile URL
embedded URL text
alias
display name
conflicting source identity
```

The project therefore follows:

```text
Normalize
→ Exact Match
→ Deterministic Rules
→ Alias Mapping
→ Evidence Corroboration
→ Manual Review
```

Not:

```text
fuzzy score
→ automatically merge everything
```

Controls include:

```text
observed-handle validation
source evidence classification
independent corroboration
manual review queue
controlled decision vocabulary
Golden Master promotion rules
alias lineage
quarantine
```

Key evidence:

- [Identity Review Evidence Policy](docs/data_audit/identity_review_evidence_policy.md)
- [Identity Review Corroboration](docs/data_audit/identity_review_corroboration_v1.md)
- [Manual Identity Review Contract](docs/data_audit/manual_identity_review_contract.md)
- [Golden Master Promotion Contract](docs/contracts/golden_master_promotion_contract_v1.md)

---

# PostgreSQL Warehouse

The persistent warehouse separates four concerns:

```text
stg
→ text-first landing / source anomaly preservation

core
→ typed governed dimensions and facts

ops
→ run ledger / incremental state / DQ evidence

mart
→ pre-aggregated analytical views
```

SQL migrations:

```text
sql/postgres/001_schemas_and_helpers.sql
sql/postgres/002_staging_tables.sql
sql/postgres/003_core_tables.sql
sql/postgres/004_incremental_upserts.sql
sql/postgres/005_reconciliation.sql
sql/postgres/006_mart_views.sql
```

Validated schema controls include:

```text
9  staging tables
9  core tables
3  ops tables
12 primary-key constraints
13 foreign-key constraints
26 CHECK constraints
3  UNIQUE constraints
13 explicit indexes
2  mart views
```

More detail:

- [PostgreSQL Warehouse v1](docs/warehouse/postgresql_warehouse_v1.md)
- [Warehouse ERD](docs/warehouse/postgresql_warehouse_erd_v1.md)
- [Data Dictionary](docs/warehouse/data_dictionary_v1.md)

---

# Incremental Loads, Idempotency, and Reconciliation

A successful rerun should not silently duplicate or mutate trusted data.

The PostgreSQL runtime uses a deterministic batch fingerprint:

```text
Governed load-ready files
→ SHA-256 batch fingerprint
→ compare with last successful state
```

New batch:

```text
RUNNING
→ staging load
→ staging reconciliation
→ core UPSERT
→ mart checks
→ reconciliation
→ SUCCESS
→ incremental state advance
```

Identical successful batch:

```text
same fingerprint
→ SKIPPED
→ no staging COPY
→ no core UPSERT
→ row counts unchanged
→ successful state unchanged
```

The real PostgreSQL integration harness verifies:

```text
first load     → SUCCESS
same batch     → SKIPPED
fingerprint    → unchanged
core counts    → unchanged
temporary DB   → dropped after test
```

Key implementation:

```text
src/postgres_warehouse_runtime.py
src/run_postgres_warehouse.py
tests/integration/generate_postgres_integration_fixture.py
tests/integration/run_postgres_integration.py
```

---

# Reliability and Failure-Path Engineering

The project deliberately proves more than the happy path.

Reliability method:

```text
Hypothesis
→ Inject Failure
→ Detect
→ Capture Evidence
→ Establish Timeline
→ Evaluate Hypotheses
→ Verify Root Cause
→ Fix
→ Recover
→ Rerun
→ Reconcile
→ Regression Test
→ Prevent Recurrence
```

## Source Reliability Lab

```text
5 / 5 controlled experiments
```

Includes source failures such as:

```text
missing workbook
duplicate workbook content
schema drift / renamed column
empty expected candidate sheet
same-batch / idempotency behavior
```

See [Reliability Failure Lab v1](docs/reliability/reliability_failure_lab_v1.md).

---

## Operational Reliability

```text
4 / 4 controlled experiments
```

Includes:

```text
bad incremental state
partial / interrupted load
bounded retry after transient dependency failure
monitoring / alert evidence and recovery
```

See [Operational Reliability v2](docs/reliability/operational_reliability_v2.md).

---

## Temporal Reliability

```text
5 / 5 controlled experiments
287 governed temporal rows
```

Includes:

```text
late-arriving data
watermark ahead of governed source
stale watermark
bounded backfill
idempotent repeated backfill
freshness / completeness / watermark SLO evidence
```

The source does not contain authoritative production ingestion timestamps, so controlled late-arrival experiments use clearly labeled synthetic arrival-time metadata.

See [Temporal Reliability v3](docs/reliability/temporal_reliability_v3.md).

---

## CI Troubleshooting Incident

A real hosted portfolio CI run failed because `actions/setup-python` pip caching was configured without pointing at the repository's actual dependency file.

Evidence chain:

```text
hosted CI failure
→ both jobs fail at Set up Python
→ Python installation itself succeeds
→ cache dependency-file discovery fails
→ repository uses requirements-dev.txt
→ add cache-dependency-path in both jobs
→ rerun
→ 155 tests pass
→ PostgreSQL integration passes
```

This is useful troubleshooting evidence, but it is **not a production incident** and was **not an intentionally injected failure**.

See [CI Cache Incident RCA](docs/reliability/ci_cache_incident_v1.md).

---

# Explainable Campaign Matching

The project intentionally does **not** start with machine learning.

Why:

```text
poor identity resolution
+ weak campaign requirements
+ mixed metric grains
+ target leakage
= sophisticated model trained on unreliable evidence
```

The sequence is:

```text
1. Eligibility Rules
2. Explainable Weighted Ranking
3. Historical Replay / Calibration Evidence
4. Statistical or ML methods only when enough governed feedback exists
```

Matching components can include governed evidence such as:

```text
Audience Fit
Historical Requirement Exposure
Campaign Experience
Cross-Brand Experience
Historical Selection
Content Performance
Budget Headroom
Operational Reliability
Data Confidence
```

Weights are configuration-driven.

Missing target dimensions are disabled and remaining active weights are renormalized instead of inventing information.

Matching v2 excludes the target campaign from historical inputs **before aggregation** and emits an explicit leakage audit.

See:

- [Explainable Matching Contract v1](docs/contracts/explainable_matching_contract_v1.md)
- [Explainable Matching v2 Contract](docs/contracts/explainable_matching_v2_contract.md)
- [Human Review / Feedback Contract](docs/contracts/human_review_feedback_contract_v1.md)

---

# Human Review and Feedback

A ranking score is decision support, not an automatic business decision.

```text
Explainable Shortlist
→ Human Review
→ Selected / Rejected / Hold
→ Reason
→ Campaign Result Capture
→ Feedback Readiness Gate
→ Observational Evaluation
```

The project does **not** fabricate campaign outcomes to make the matching system appear trained or accurate.

Unknown outcomes remain unknown.

Automatic model-weight calibration is deferred until governed real feedback exists.

---

# Docker PostgreSQL Reproducibility

The repository includes a public-safe PostgreSQL 18.6 Compose definition.

```text
compose.yaml
.env.example
```

The service uses:

```text
postgres:18.6
named volume: influencer_pgdata
network: influencer-network
configurable host port
healthcheck with pg_isready
```

The validated local lab used host port `55432` to keep Docker PostgreSQL separate from the native PostgreSQL instance used during development.

Persistence evidence proved:

```text
container stop / start
→ warehouse state preserved

docker compose down        # without -v
→ container/network removed
→ named volume preserved

docker compose up
→ service recreated
→ governed core / ops state preserved
```

This is a **local reproducibility and recovery lab**, not a cloud deployment claim.

---

# Testing Strategy

Important features follow:

```text
Requirement
→ Acceptance Criteria
→ Test Scenario
→ Test Case
→ Expected Result
→ Execution
→ Evidence
```

Coverage includes:

```text
positive
negative
boundary
missing
duplicate
invalid
schema drift
incremental
retry
rerun
regression
failure recovery
```

Current public baseline:

```text
155 passed
```

The pytest baseline is separate from the real PostgreSQL integration harness.

See [Testing Evidence v1](docs/portfolio/testing_evidence_v1.md).

---

# GitHub Actions CI

The CI workflow runs on push and pull request to `main`.

## Fast Quality Gate

```text
Python 3.14
dependency install
compileall
155-test regression suite
Docker Compose configuration validation
```

## PostgreSQL Integration Gate

```text
PostgreSQL 18.6 service
public-safe synthetic fixture
real psql client
temporary integration database
first load SUCCESS
same-batch rerun SKIPPED
fingerprint / row-count stability
temporary DB cleanup
```

Workflow:

```text
.github/workflows/ci.yml
```

---

# Security and Public Portfolio Boundary

The original workbooks can contain:

```text
real names
telephone numbers
shipping information
tracking information
internal campaign codes
company-sensitive mappings
```

Therefore the repository follows:

```text
Private Raw
→ PII Detection
→ Mask / Remove / Suppress
→ Governed Internal Evidence
→ Synthetic / Aggregated Public Evidence
```

Public GitHub must **not** contain:

```text
raw company workbooks
private source mappings
private load-ready data
PII values
local .env
database passwords
private incident evidence
private lineage files
```

Controls include:

```text
src/pii_guard.py
.gitignore
.env.example
synthetic PostgreSQL integration fixtures
```

The `.env.example` file contains placeholders only.

Local secrets belong in `.env`, which is excluded from the public repository.

---

# Repository Structure

```text
.github/
  workflows/
    ci.yml

config/
  *.example.json
  *.example.yml
  private/                     # local/private; gitignored where applicable

data/
  raw/                         # private source data; never public
  quarantine/                  # private governed quarantine
  private_audit/               # private source-derived evidence
  synthetic/                   # public-safe synthetic assets where present

docs/
  architecture/
  contracts/
  data_audit/
  portfolio/
  reliability/
  warehouse/

sql/
  postgres/
    001_schemas_and_helpers.sql
    002_staging_tables.sql
    003_core_tables.sql
    004_incremental_upserts.sql
    005_reconciliation.sql
    006_mart_views.sql

src/
  source discovery / canonicalization
  entity resolution / Golden Master
  campaign / performance history
  historical features
  explainable matching
  reliability
  PostgreSQL runtime

tests/
  unit / contract / regression tests
  integration/
    generate_postgres_integration_fixture.py
    run_postgres_integration.py

compose.yaml
.env.example
pytest.ini
requirements-dev.txt
```

---

# Quick Start — Public-Safe Validation

## 1. Clone and install test dependencies

```bash
git clone https://github.com/bodinkc30-Pete/influencer-campaign-intelligence-pipeline.git
cd influencer-campaign-intelligence-pipeline

python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

## 2. Compile and run the regression suite

```bash
python -m compileall -q src tests
python -m pytest -q
```

Expected validated baseline:

```text
155 passed
```

## 3. Validate Docker Compose configuration

```bash
docker compose --env-file .env.example config --quiet
```

---

# Optional Local PostgreSQL Integration

Create a local secret file from the public template:

```powershell
Copy-Item .env.example .env
```

Edit `.env` locally and replace the placeholder password.

Never commit `.env`.

Start PostgreSQL:

```powershell
docker compose up -d postgres
docker compose ps postgres
```

For the public-safe real database harness, provide the same local PostgreSQL password at runtime without committing it:

```powershell
$env:PGPASSWORD = '<your-local-postgres-password>'

python tests/integration/run_postgres_integration.py `
  --host localhost `
  --port 55432 `
  --user postgres `
  --admin-database postgres
```

The integration harness generates synthetic data and creates a temporary database.

It does not require private company workbooks.

---

# Private Full-Data Runtime Boundary

The complete historical warehouse load requires governed private load-ready files that are intentionally excluded from this repository.

The public runner is:

```text
python -m src.run_postgres_warehouse
```

A private load directory is supplied explicitly at runtime.

No real source data is required to review the public architecture, code, tests, contracts, CI, or synthetic integration flow.

---

# Evidence Index

For reviewers who want to go beyond the README:

| Evidence | Document |
|---|---|
| As-built architecture | [Architecture v2](docs/architecture/architecture_v2.md) |
| PostgreSQL model | [Warehouse ERD](docs/warehouse/postgresql_warehouse_erd_v1.md) |
| Warehouse implementation | [PostgreSQL Warehouse v1](docs/warehouse/postgresql_warehouse_v1.md) |
| Column / table semantics | [Data Dictionary](docs/warehouse/data_dictionary_v1.md) |
| Data Quality evidence | [DQ Summary](docs/portfolio/data_quality_summary_v1.md) |
| Test evidence | [Testing Evidence](docs/portfolio/testing_evidence_v1.md) |
| Capability → evidence traceability | [Portfolio Evidence Map](docs/portfolio/portfolio_evidence_map_v1.md) |
| Thailand job responsibility alignment | [Job Responsibility Mapping](docs/portfolio/job_responsibility_mapping_v1.md) |
| Source failure experiments | [Reliability Failure Lab](docs/reliability/reliability_failure_lab_v1.md) |
| Operational failure experiments | [Operational Reliability](docs/reliability/operational_reliability_v2.md) |
| Temporal failure experiments | [Temporal Reliability](docs/reliability/temporal_reliability_v3.md) |
| CI troubleshooting RCA | [CI Cache Incident RCA](docs/reliability/ci_cache_incident_v1.md) |

The [Portfolio Evidence Map](docs/portfolio/portfolio_evidence_map_v1.md) is the best starting point for tracing:

```text
Capability
→ Implementation
→ Test
→ Runtime Evidence
→ Documentation
→ Safe Claim
```

---

# Job-Market Alignment

The core portfolio is intentionally optimized for responsibilities that repeatedly appear in Thailand roles such as:

```text
Data Engineer
Data Quality Engineer
Data / ETL Tester
Data Integration / ETL Engineer
Master Data / MDM
Data Governance
```

Strong demonstrated areas:

```text
Python
SQL
PostgreSQL
ETL / ELT patterns
multi-source integration
schema mapping
data modeling
Master Data
deterministic entity resolution
Data Quality
incremental loads
idempotency
reconciliation
testing
failure recovery
troubleshooting
Docker
Git / GitHub
CI
technical documentation
```

Analytics Engineering is an adjacent fit because the project already demonstrates trusted SQL models, marts, testing, documentation, and traceability.

See [Job Responsibility Mapping v1](docs/portfolio/job_responsibility_mapping_v1.md) for the current Thailand market research and explicit gaps.

---

# Known Limitations and Deferred Extensions

The project intentionally avoids tool stuffing.

## Airflow

Not implemented in the core repository.

It is a justified later extension because the existing pipeline already has real orchestration problems to solve:

```text
scheduling
dependencies
retry
failure propagation
recovery
rerun
same-batch idempotency
PostgreSQL run state
```

---

## Cloud

No AWS / GCP / Azure production deployment is claimed.

A future cloud extension should add real value through:

```text
managed execution
IAM
networking
monitoring
deployment
cost controls
```

---

## dbt

Not implemented.

It becomes useful if SQL transformation ownership is deliberately moved into a governed analytics transformation workflow requiring:

```text
dependency graphs
model tests
documentation
lineage
```

---

## Spark / Databricks

Not implemented because the current data volume does not require distributed compute.

It should only be added when:

```text
data scale
architecture
or target job responsibility
```

provides a real reason.

---

## Machine Learning

Not implemented for ranking.

The current order remains:

```text
Eligibility Rules
→ Explainable Weighted Ranking
→ Historical Calibration
→ ML only when governed real feedback is sufficient
```

---

# Engineering Decisions

## Why PostgreSQL?

Because the project needs to prove:

```text
relational data modeling
PK / FK / CHECK / UNIQUE constraints
incremental UPSERT
transactions
idempotency
reconciliation
analytical marts
SQL reasoning
```

The dataset does not need a distributed engine to demonstrate these problems.

---

## Why deterministic entity resolution first?

Because a false influencer merge corrupts:

```text
campaign history
performance history
fee history
matching features
future shortlist decisions
```

Precision and auditability are more important than maximizing automatic merge coverage.

---

## Why matching is explainable before ML?

Because the project must first establish:

```text
trusted identities
trusted history
governed requirements
correct temporal boundaries
real feedback
```

before statistical optimization is meaningful.

---

## Why failure labs?

Because:

```text
code exists
≠ pipeline is operable

pipeline succeeds
≠ data is correct

fix applied
≠ recovery is proven
```

Failure experiments make troubleshooting, recovery, and reconciliation inspectable.

---

# Portfolio Claim Boundary

Safe claims:

```text
built a multi-source Python / SQL pipeline
implemented deterministic Master Data patterns
implemented a PostgreSQL warehouse
implemented incremental UPSERT and same-batch idempotency
implemented layered Data Quality controls
implemented automated regression testing
validated a real PostgreSQL synthetic integration flow
implemented controlled reliability experiments
troubleshot a real hosted portfolio CI failure
implemented explainable rule-based ranking
```

Claims this repository does **not** make:

```text
production ownership
production incident response
enterprise MDM ownership
enterprise Data Governance ownership
production Airflow experience
production cloud experience
Spark / Databricks expertise from this project
ML recommendation accuracy
real-time streaming platform
```

---

# Definition of Done

The core project is considered complete only when it can demonstrate:

```text
Build
→ Operate
→ Test
→ Break
→ Troubleshoot
→ Recover
→ Reconcile
→ Optimize
→ Govern
→ Explain
```

The final business story is:

> Turn fragmented influencer data from multiple brands and campaigns into trusted Master Data with historical evidence, then use that governed history to support explainable influencer shortlisting while preserving Data Quality, lineage, security, and human review.
