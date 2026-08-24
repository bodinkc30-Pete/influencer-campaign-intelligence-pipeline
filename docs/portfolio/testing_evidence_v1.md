# Testing Evidence v1

## Purpose

This document summarizes the **public-safe testing evidence** for the Influencer Campaign Intelligence Pipeline.

It separates four different validation layers so that the portfolio does not overclaim test coverage:

```text
Static / configuration validation
≠
Automated pytest regression tests
≠
Real PostgreSQL integration execution
≠
Hosted GitHub Actions execution
```

The project is a **portfolio / production-like engineering lab**, not a claim of production ownership or production incident experience.

---

## 1. Testing Principle

The project follows the evidence chain:

```text
Requirement
→ Acceptance Criteria
→ Test Scenario
→ Test Case
→ Expected Result
→ Execution
→ Evidence
```

The reliability principle is:

```text
Pipeline SUCCESS != Data Correct
```

A process is not considered trusted only because a command exits successfully. Data contracts, reconciliation, idempotency, failure behavior, and regression evidence are tested separately.

---

## 2. Current Automated Test Baseline

The current repository inventory contains:

```text
23 test_*.py files
155 pytest test functions
155 passed in the current local regression baseline
```

`pytest.ini` currently contains:

```ini
[pytest]
pythonpath = .
testpaths = tests
```

There are no custom pytest markers in the current configuration. Therefore, the test-layer grouping in this document is a **portfolio evidence classification**, not a pytest marker taxonomy.

The `155` figure is the repository-wide automated pytest baseline. It must **not** be described as:

```text
155 PostgreSQL integration tests
155 end-to-end tests
155 Data Quality-only tests
```

---

## 3. Automated Test Inventory by File

| Test file | Test functions | Primary evidence area |
|---|---:|---|
| `test_campaign_history.py` | 6 | Campaign history |
| `test_candidate_adapter.py` | 16 | Canonical candidate adaptation |
| `test_deliverable_performance.py` | 6 | Deliverable/performance history |
| `test_deterministic_identity_clusters.py` | 2 | Deterministic identity resolution |
| `test_feedback_loop.py` | 11 | Human review / feedback |
| `test_golden_master_promotion.py` | 4 | Golden Master promotion |
| `test_historical_features.py` | 4 | Historical feature engineering |
| `test_identity_corroboration.py` | 4 | Identity corroboration |
| `test_identity_review_decision_gate.py` | 6 | Manual-review decision gate |
| `test_identity_review_evidence.py` | 4 | Identity review evidence |
| `test_identity_review_queue.py` | 1 | Review queue |
| `test_identity_source_evidence.py` | 3 | Source identity evidence |
| `test_matching.py` | 9 | Explainable matching v1 |
| `test_matching_v2.py` | 11 | Historical-replay matching v2 |
| `test_operational_reliability.py` | 10 | Operational reliability |
| `test_pii_guard.py` | 3 | PII/public-safety boundary |
| `test_postgres_warehouse_runtime.py` | 7 | Warehouse runtime contract logic |
| `test_reliability_lab.py` | 7 | Controlled source failure lab |
| `test_requirement_normalization.py` | 12 | Requirement normalization |
| `test_resolved_candidate_observations.py` | 2 | Resolved candidate observations |
| `test_sheet_classifier.py` | 5 | Workbook/sheet classification |
| `test_temporal_reliability.py` | 12 | Temporal reliability / SLO controls |
| `test_warehouse_contract.py` | 10 | PostgreSQL warehouse contract |
| **Total** | **155** | Repository-wide pytest baseline |

---

## 4. Portfolio-Oriented Test Grouping

The following grouping is derived from the test files and their responsibilities. It is a documentation classification, not an encoded pytest marker scheme.

| Test area | Test functions |
|---|---:|
| Source / canonicalization / requirements | 33 |
| Identity / Golden Master / PII | 29 |
| Campaign / performance / historical features | 16 |
| Matching / feedback | 31 |
| Reliability | 29 |
| PostgreSQL warehouse contract/runtime logic | 17 |
| **Total** | **155** |

This distribution shows that the test suite is not concentrated only on the happy-path transformation layer.

---

## 5. Layer 1 — Static and Configuration Validation

The CI Fast Quality Gate includes:

```text
python -m compileall -q src tests
python -m pytest -q
docker compose --env-file .env.example config --quiet
```

These checks answer different questions.

### Python compilation

Purpose:

```text
Can Python source and test modules compile?
```

This catches syntax-level defects before deeper execution.

### Pytest regression

Purpose:

```text
Do the repository's automated contract / logic / failure-path tests still pass?
```

Current baseline:

```text
155 passed
```

### Docker Compose configuration validation

Purpose:

```text
Can the public Compose configuration resolve successfully from the public-safe environment template?
```

This is a configuration validation gate. It is not equivalent to proving that every runtime behavior of the database is correct.

---

## 6. Layer 2 — Automated Pytest Regression Suite

The pytest suite covers business rules, contracts, deterministic transformations, quality gates, and controlled reliability behavior.

Representative evidence areas include:

```text
candidate schema adaptation
sheet classification
requirement normalization
PII guard
deterministic identity clustering
manual-review gating
Golden Master promotion
campaign history
deliverable/performance history
historical features
matching v1
matching v2
feedback loop
source failure lab
operational reliability
temporal reliability
warehouse contracts
warehouse runtime helper logic
```

The suite is intentionally fast enough to run as a CI quality gate.

---

## 7. Important PostgreSQL Test Classification

`tests/test_postgres_warehouse_runtime.py` contains 7 automated pytest tests.

Those tests verify logic such as:

```text
load-order manifest coverage
deterministic batch fingerprint behavior
CSV row-count calculation
atomic COPY-script structure
9-table staging coverage
UPSERT loaded_at contract
ISO-date helper SQL contract
SQL migration UTF-8 BOM safety
```

These tests inspect Python/runtime behavior and SQL files.

They do **not**, by themselves, establish a live PostgreSQL connection.

Therefore:

```text
test_postgres_warehouse_runtime.py
=
warehouse runtime contract / unit-style automated tests

not
=
the real PostgreSQL integration harness
```

This distinction is important for an accurate portfolio claim.

---

## 8. Layer 3 — Real PostgreSQL Integration Harness

The public repository contains two dedicated integration assets:

```text
tests/integration/generate_postgres_integration_fixture.py
tests/integration/run_postgres_integration.py
```

This integration path is separate from the 155 pytest baseline.

### Synthetic fixture contract

The fixture generator uses intentionally synthetic identifiers and values such as:

```text
inf_ci_1
brd_ci_1
cmp_ci_1
synthetic_ci
synthetic_ci.xlsx
public_safe
```

The fixture is designed to exercise the warehouse without publishing private company-derived load-ready data.

### Integration database lifecycle

The harness creates a uniquely named temporary PostgreSQL database for the run.

Conceptually:

```text
Create temporary integration database
→ generate public-safe synthetic fixture
→ execute real warehouse pipeline
→ inspect governed core counts
→ rerun same batch
→ verify idempotent skip
→ drop temporary database
```

The temporary database is removed in the harness cleanup path.

---

## 9. Real Integration Assertions

The integration harness validates all of the following.

### Fixture generation

Expected:

```text
PUBLIC_SAFE_FIXTURE=True
FIXTURE_CSV_COUNT=9
```

The fixture has one synthetic row for each of the nine governed warehouse source/core entities.

### First warehouse execution

Expected:

```text
FIRST_STATUS=SUCCESS
FIRST_SKIPPED=False
FIRST_SOURCE_ROWS=9
```

The first run must execute rather than skip.

### Core reconciliation

After the first run, the harness requires exactly one row in each governed core table:

```text
campaign_requirement
dim_brand
dim_campaign
dim_influencer
fact_campaign_deliverable
fact_campaign_influencer
fact_campaign_performance
fact_influencer_performance
influencer_identity_alias
```

### Same-batch rerun

Expected:

```text
SECOND_STATUS=SKIPPED
SECOND_SKIPPED=True
```

### Fingerprint stability

Expected:

```text
FINGERPRINT_MATCH=True
```

The same synthetic source batch must generate the same deterministic fingerprint.

### Idempotent row-count behavior

Expected:

```text
ROW_COUNTS_UNCHANGED=True
```

The second same-batch execution must not append duplicate core rows.

### Integration completion

Expected:

```text
POSTGRES_INTEGRATION_STATUS=PASS
DATABASE_DROPPED=True
```

This proves the harness executed real PostgreSQL behavior and cleaned up its temporary database.

---

## 10. Layer 4 — Hosted GitHub Actions Evidence

The CI workflow runs on:

```text
push to main
pull request to main
```

with read-only repository content permission.

It has two separate jobs:

```text
Fast Quality Gate
PostgreSQL Integration Gate
```

This separation is deliberate.

### Fast Quality Gate

The hosted job performs:

```text
checkout
Python setup
dependency installation
compileall
pytest
Docker Compose configuration validation
```

A verified successful hosted run recorded:

```text
GitHub Actions run: 32726051052
Commit: 3b4b9966d4263a4731d665ec8fabdf6227c55eee
Event: push
Status: completed
Conclusion: success
```

The hosted Fast Quality Gate recorded:

```text
155 passed in 0.45s
```

and the Docker Compose configuration validation step completed successfully.

### PostgreSQL Integration Gate

The hosted integration job uses:

```text
Ubuntu 24.04 runner
PostgreSQL 18.6 service container
Python 3.14
PostgreSQL client
public-safe synthetic fixture
real PostgreSQL integration harness
```

The successful hosted execution recorded:

```text
PUBLIC_SAFE_FIXTURE=True
DATABASE_CREATED=True
FIXTURE_CSV_COUNT=9

FIRST_STATUS=SUCCESS
FIRST_SKIPPED=False
FIRST_SOURCE_ROWS=9

SECOND_STATUS=SKIPPED
SECOND_SKIPPED=True
FINGERPRINT_MATCH=True
ROW_COUNTS_UNCHANGED=True

POSTGRES_INTEGRATION_STATUS=PASS
DATABASE_DROPPED=True
```

This is stronger evidence than merely showing that the integration script exists.

---

## 11. CI Gate Architecture

```text
Git Push / Pull Request
        |
        +-----------------------------+
        |                             |
        v                             v
Fast Quality Gate             PostgreSQL Integration Gate
        |                             |
        v                             v
Python compile                PostgreSQL 18.6 service
        |                             |
        v                             v
155 pytest tests              Synthetic 9-CSV fixture
        |                             |
        v                             v
Compose config                Real warehouse execution
                                      |
                                      v
                               First load SUCCESS
                                      |
                                      v
                               Same batch SKIPPED
                                      |
                                      v
                               Counts unchanged
                                      |
                                      v
                               Temp DB dropped
```

The two jobs validate different failure surfaces and should not be collapsed into one generic “tests passed” claim.

---

## 12. Positive, Negative, Boundary, and Failure-Path Coverage

The project testing strategy includes more than happy-path assertions.

Representative categories include:

| Test type | Examples in this portfolio |
|---|---|
| Positive | valid canonicalization, valid Golden promotion, valid warehouse load |
| Negative | invalid PII/public boundary, malformed/unsupported values, invalid state |
| Missing | missing workbook, missing requirement evidence |
| Duplicate | duplicate workbook content, same-batch rerun |
| Invalid | malformed identity/URL/value/state inputs |
| Schema drift | renamed/missing candidate column |
| Boundary | empty expected sheet, bounded temporal windows |
| Conflict | ambiguous identity, conflicting campaign/history evidence |
| Incremental | deterministic fingerprint and state transition behavior |
| Retry | bounded retry for explicitly retryable operational failures |
| Rerun | idempotent same-batch and recovery reruns |
| Temporal | late arrival, stale/ahead watermark, backfill |
| Regression | repository-wide 155-test suite |
| Integration | real PostgreSQL synthetic fixture execution |

---

## 13. Reliability Failure Evidence

Testing extends beyond normal functional tests.

### Source Reliability Lab

Controlled scenarios:

```text
missing workbook
duplicate workbook content
schema drift / column rename
empty expected candidate sheet
same-batch rerun
```

### Operational Reliability

Controlled scenarios:

```text
bad incremental state
partial/interrupted load
transient dependency failure
monitoring / alert evaluation
```

### Temporal Reliability

Controlled scenarios:

```text
late-arriving data
ahead watermark
stale watermark
bounded backfill
freshness / completeness / watermark SLO recovery
```

The reliability method is:

```text
Hypothesis
→ Inject Failure
→ Detect
→ Evidence
→ Verified Cause
→ Fix
→ Recover
→ Rerun
→ Reconcile
→ Regression
→ Prevent
```

---

## 14. Data Correctness and Reconciliation

The warehouse testing layer distinguishes execution success from data correctness.

Reconciliation checks include:

```text
foreign-key orphan detection
duplicate campaign × influencer business key
core row counts
same-batch row-count stability
deterministic batch fingerprint
incremental-state behavior
```

The real PostgreSQL integration harness verifies core counts both before and after the same-batch rerun.

This directly tests:

```text
SUCCESS
+
reconciliation
+
idempotency
```

rather than relying only on process exit code.

---

## 15. Public-Safety Testing Boundary

The integration path is designed for a public portfolio.

Public CI uses:

```text
synthetic identities
synthetic brand/campaign data
synthetic workbook lineage
example-domain URL
public_safe boundary status
```

It does not require public access to:

```text
raw company Excel workbooks
real influencer PII
private load-ready company data
local runtime credentials
private incident evidence
```

This preserves the distinction:

```text
Private source evidence
≠
Public test fixture
```

---

## 16. What the Current Test Suite Does Not Claim

The portfolio does not claim:

```text
155 end-to-end tests
155 live-database tests
155 Data Quality-only tests
full browser/UI testing
performance/load benchmarking
chaos testing against a production platform
enterprise production monitoring
production SLA validation
production incident ownership
```

The evidence is intentionally narrower and verifiable.

---

## 17. Current Test Evidence Snapshot

```text
Automated test files                     23
Automated pytest test functions          155
Current local pytest baseline            155 passed

Dedicated integration assets             2
Synthetic integration CSVs               9
First integration source rows            9
Core tables checked by harness            9

Hosted CI jobs                            2
Fast Quality Gate                         success
PostgreSQL Integration Gate               success

Same-batch second run                     SKIPPED
Fingerprint stable                        True
Core row counts unchanged                 True
Temporary integration database dropped   True
```

---

## 18. Evidence References

| Evidence | Repository location |
|---|---|
| Pytest configuration | `pytest.ini` |
| Automated tests | `tests/test_*.py` |
| PostgreSQL fixture generator | `tests/integration/generate_postgres_integration_fixture.py` |
| PostgreSQL integration harness | `tests/integration/run_postgres_integration.py` |
| CI workflow | `.github/workflows/ci.yml` |
| Warehouse migrations | `sql/postgres/` |
| Warehouse runtime | `src/postgres_warehouse_runtime.py`, `src/run_postgres_warehouse.py` |
| Warehouse contract tests | `tests/test_warehouse_contract.py` |
| Warehouse runtime logic tests | `tests/test_postgres_warehouse_runtime.py` |
| Source reliability | `docs/reliability/reliability_failure_lab_v1.md` |
| Operational reliability | `docs/reliability/operational_reliability_v2.md` |
| Temporal reliability | `docs/reliability/temporal_reliability_v3.md` |
| Data Quality summary | `docs/portfolio/data_quality_summary_v1.md` |

Hosted execution evidence:

```text
GitHub Actions run 32726051052
head commit 3b4b9966d4263a4731d665ec8fabdf6227c55eee
conclusion success
```

---

## 19. Interview-Safe Claims

Accurate statements supported by this project include:

```text
I built a 155-test automated regression suite across 23 pytest files.

I separated fast contract/logic tests from a real PostgreSQL integration harness.

The PostgreSQL integration test creates a temporary database, runs the actual
warehouse pipeline against nine public-safe synthetic CSVs, verifies the first
load, reruns the same batch, proves idempotent skipping and unchanged core row
counts, and drops the temporary database.

I run the fast quality gate and PostgreSQL integration gate independently in
GitHub Actions.

I test both happy paths and controlled failure/recovery paths, including schema
drift, duplicate inputs, partial loads, retry behavior, late-arriving data,
watermarks, backfill, and rerun idempotency.
```

Statements that should be avoided include:

```text
I have production incident ownership.
All 155 tests are database integration tests.
The synthetic CI fixture is real company data.
This lab proves enterprise-scale performance.
```

---

## 20. Summary

The project's testing evidence demonstrates four distinct levels:

```text
Compile and configuration validation
→ automated regression contracts
→ real PostgreSQL synthetic integration
→ hosted CI runtime proof
```

The testing strategy supports the broader engineering lifecycle:

```text
Build
→ Operate
→ Test
→ Break
→ Troubleshoot
→ Recover
→ Reconcile
→ Regression
→ Govern
→ Explain
```

The main portfolio value is not the raw number of tests. It is the ability to connect a requirement or failure mode to an executable check and verifiable evidence without overstating what that evidence proves.
