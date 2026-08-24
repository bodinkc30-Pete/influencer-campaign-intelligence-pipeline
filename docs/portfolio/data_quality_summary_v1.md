# Data Quality Summary v1

## Purpose

This document summarizes the **public-safe data-quality controls and evidence** implemented in the Influencer Campaign Intelligence Pipeline.

It is designed to show how the project separates:

```text
Pipeline execution
from
Data correctness
```

The project is a **portfolio / production-like engineering lab**, not a claim of production ownership or production incident experience.

---

## 1. Data Quality Operating Principle

The project treats Data Quality as a set of explicit gates across the full pipeline:

```text
Source Discovery
→ Structural Validation
→ Canonicalization
→ PII Boundary
→ Deterministic Entity Resolution
→ Golden Master Promotion
→ Campaign / Deliverable / Performance History
→ PostgreSQL Referential Reconciliation
→ Incremental / Idempotency Controls
→ Temporal Reliability
→ Explainable Matching Quality
```

The governing principle is:

```text
Pipeline SUCCESS != Data Correct
```

A technically successful process is not considered trustworthy until the relevant data-quality, reconciliation, and governance controls pass.

---

## 2. Evidence Scope and Claim Boundary

This summary uses three evidence classes.

| Evidence class | Meaning |
|---|---|
| Governed aggregate evidence | Public-safe counts derived from the governed project outputs |
| Public synthetic/runtime evidence | Tests and integration evidence that do not require private company data |
| Controlled reliability evidence | Failure experiments performed intentionally in a portfolio lab |

Private company workbooks, raw PII, credentials, and private source-derived evidence are excluded from the public repository.

Synthetic or simulated evidence is never presented as real production metadata or real campaign outcome evidence.

---

## 3. Current Governed Aggregate Evidence

The current as-built architecture records the following public-safe aggregate evidence:

```text
703 Golden Influencer Master records
2,519 alias-provenance rows
163 Golden records observed across multiple workbooks

12 fit-ready target campaigns
8,436 scenario × influencer score rows
360 shortlist rows
0 target-campaign leakage audit failures
```

These values are portfolio evidence for the implemented governed dataset and historical-replay layer. They are not production KPIs or an SLA.

---

## 4. Source and Structural Data Quality

### Risks addressed

The source layer is designed for heterogeneous multi-workbook Excel data where structural defects may include:

- missing expected workbook;
- duplicate workbook content;
- empty expected sheet;
- candidate-column rename;
- schema drift;
- malformed values;
- repeated or inconsistent workbook structures.

### Controls

The implemented source/reliability boundary uses:

```text
source discovery
SHA-256 source evidence
workbook / sheet inventory
sheet classification rules
candidate-column contracts
expected non-empty sheet validation
duplicate-content detection
schema-drift detection
```

### Controlled failure evidence

`docs/reliability/reliability_failure_lab_v1.md` contains 5 controlled scenarios:

```text
1. Missing workbook
2. Duplicate workbook content
3. Candidate schema drift / column rename
4. Empty expected candidate sheet
5. Same-batch rerun / idempotency
```

The failure-lab method is evidence-based:

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

## 5. Canonicalization and Type Quality

The PostgreSQL landing design intentionally separates untrusted text from governed typed data.

```text
stg.*
→ text-first UNLOGGED landing
→ safe conversion helpers
→ typed core.*
```

The current incremental UPSERT migration uses:

```text
core.try_integer()  = 16 calls
core.try_numeric()  = 39 calls
core.try_boolean()  = 4 calls
core.try_iso_date() = 4 calls
```

Safe helpers return `NULL` when source text is not safely convertible instead of silently fabricating a typed value.

This allows invalid or ambiguous source values to remain detectable at the Data Quality boundary.

---

## 6. Identity and Master Data Quality

### Resolution policy

Entity resolution follows:

```text
Normalize
→ Exact Match
→ Deterministic Rules
→ Alias Evidence
→ Manual Review
```

Fuzzy similarity is not allowed to automatically merge every record.

Ambiguous identities are kept outside trusted promotion until sufficient evidence exists.

### Manual-review evidence

The current identity-review corroboration evidence contains:

```text
12 review groups
4 groups with one independently corroborated candidate handle
7 groups with no independent exact corroboration
1 group with no parseable candidate handle
```

Corroboration is advisory evidence only.

```text
auto_resolution_allowed = no
```

remains the policy for every review group in that evidence set.

This is an intentional quality control: unresolved identity ambiguity is preserved rather than hidden through an unsafe automatic merge.

---

## 7. Golden Master Quality

The Golden Master is a governed promotion layer rather than a simple deduplication output.

Current public-safe evidence:

```text
703 Golden Influencer Master records
2,519 alias-provenance rows
163 Golden records observed across multiple workbooks
```

Quality characteristics include:

- deterministic identity promotion;
- retained alias/provenance evidence;
- source occurrence evidence;
- explicit identity confidence/method;
- review evidence where needed;
- a PII boundary before public portfolio exposure.

The project does not claim that every source observation is automatically promotable.

---

## 8. Campaign, Deliverable, and Performance Quality

The project keeps different business grains separate instead of forcing heterogeneous metrics into one flattened fact.

Governed entities include:

```text
campaign × influencer
deliverable
influencer performance
campaign performance
```

Important quality protections include:

- stable campaign/influencer business grain;
- explicit selection and confirmation states;
- conflict-aware fee evidence;
- raw and parsed date preservation where applicable;
- campaign and identity mapping evidence;
- row-level DQ status/codes for campaign history and deliverables;
- metric-definition versioning.

Metric fields such as:

```text
GMV
sales_amount
revenue
ROI
ROAS
CTR
```

are not treated as semantically interchangeable.

---

## 9. PostgreSQL Referential Quality

The governed PostgreSQL model uses primary keys, foreign keys, check constraints, uniqueness rules, and reconciliation queries.

The audited core/ops migration currently contains:

```text
12 PRIMARY KEY declarations
13 REFERENCES declarations
26 CHECK(...) declarations
3 UNIQUE(...) declarations
```

Post-load reconciliation explicitly checks:

```text
campaign → brand orphan
campaign-influencer → campaign orphan
campaign-influencer → influencer orphan
duplicate campaign × influencer business key
deliverable → campaign orphan
deliverable → influencer orphan
influencer-performance → optional deliverable orphan
```

For violation queries, the expected result is:

```text
violation_count = 0
```

Row-count reconciliation is also captured for the major governed core tables.

---

## 10. Incremental and Idempotency Quality

The warehouse uses a deterministic batch fingerprint and idempotent UPSERT behavior.

The current source-to-target migration contains:

```text
9 ON CONFLICT statements
```

The runtime contract separates:

```text
same successful batch
→ SKIPPED
→ no duplicate load
```

from:

```text
new batch
→ stage
→ typed UPSERT
→ reconcile
→ SUCCESS
→ advance incremental state
```

Incremental state must not advance merely because processing started.

---

## 11. Operational Reliability Quality

`docs/reliability/operational_reliability_v2.md` contains 4 controlled scenarios:

```text
1. Bad incremental state
2. Partial load / interrupted batch
3. Transient dependency failure with bounded retry
4. Monitoring / alert evaluation
```

Important recovery rules include:

- incremental state advances only after successful commit;
- malformed or unknown state blocks processing;
- staging data without a commit marker is not trusted as loaded data;
- recovery removes orphan staging before atomic rerun;
- duplicate commit of the same run ID is idempotent;
- retries are bounded and limited to explicitly retryable failures;
- recovery is incomplete until reconciliation and regression evidence pass.

Monitoring/alert evidence in this project is simulated portfolio evidence, not a real production notification integration.

---

## 12. Temporal Data Quality

`docs/reliability/temporal_reliability_v3.md` contains 5 controlled scenarios covering:

```text
late-arriving data
future/ahead watermark
stale watermark
bounded backfill
freshness / completeness / watermark SLO recovery
```

The watermark contract requires that a watermark:

- parses as `YYYY-MM-DD`;
- is not ahead of the maximum governed event date;
- does not exceed governed lag tolerance without explicit recovery state;
- advances only after reconciled success.

Backfill is bounded by an explicit event-date interval and stable business key.

A repeated recovered backfill must not blindly append duplicates.

The source data does not contain authoritative production arrival timestamps. Controlled synthetic arrival dates used by the reliability lab must therefore not be presented as company production metadata.

---

## 13. Matching Data Quality

The matching layer is governed as decision support rather than an opaque automatic recommender.

Processing order:

```text
Campaign Requirement
+
Historical Evidence
→ Eligibility Rules
→ Configurable Weighted Ranking
→ Deterministic Rank
→ Reasons + Cautions
→ Human Review
```

Current historical-replay evidence includes:

```text
12 fit-ready target campaigns
8,436 scenario × influencer score rows
360 shortlist rows
0 target-campaign leakage audit failures
```

Target-campaign leakage is treated as a data-quality defect because it would allow future/current campaign information to contaminate historical evidence.

Machine learning remains out of scope until sufficient governed outcome data exists.

---

## 14. PII and Public-Safety Quality Boundary

The source workbooks may contain sensitive company/internal information and PII.

The public portfolio therefore follows:

```text
Private raw data
→ PII / sensitivity detection
→ private governed processing
→ public-safe code, contracts, synthetic fixtures, documentation, and aggregate evidence
```

The public repository must not contain:

- raw company workbooks;
- real PII;
- private source mappings;
- local credentials;
- private load-ready/runtime evidence derived from company data.

Public CI integration uses synthetic fixture data rather than private company-derived load-ready data.

---

## 15. Automated Testing Evidence

The repository baseline currently contains:

```text
155 automated test functions
```

This is the **repository-wide automated test baseline**, not a claim of 155 Data Quality-only tests.

A keyword-based inventory identified 17 test files related to DQ concepts such as:

```text
PII
missing / invalid data
duplicates
schema drift
entity review
quarantine / resolution
reconciliation
reliability
warehouse contracts
matching leakage / safeguards
```

The 17-file figure is a heuristic evidence inventory based on test-content keywords; it is not a formal test-classification taxonomy.

The project also has a real PostgreSQL integration harness using public-safe synthetic fixture data.

---

## 16. Quality Status Is Not Binary

A key design choice is to preserve uncertainty.

Examples:

```text
PASS
→ acceptable for governed processing

WARN
→ allowed but quality concern remains visible

ERROR / invalid boundary
→ quarantine or block

ambiguous identity
→ manual review

missing requirement evidence
→ not silently inherited

missing authoritative arrival metadata
→ synthetic lab metadata kept explicitly separate
```

The project therefore avoids describing the whole dataset as simply “clean.”

Trusted data is promoted selectively according to evidence and contract.

---

## 17. Known Boundaries

This portfolio does not claim:

- real production incident ownership;
- approved external production SLA;
- enterprise MDM platform ownership;
- automatic fuzzy identity merge;
- ML-driven recommendation quality;
- authoritative production ingestion timestamps;
- external production alerting;
- public storage of private company data.

These are deliberate claim boundaries, not hidden gaps.

---

## 18. Evidence Map

| DQ area | Main implementation/evidence |
|---|---|
| Source discovery / structure | `src/discover_sources.py`, `src/xlsx_probe.py`, `src/build_sheet_inventory.py`, `src/sheet_classifier.py` |
| Canonical contracts | `src/candidate_adapter.py`, `config/candidate_column_contract.json` |
| PII boundary | `src/pii_guard.py`, `tests/test_pii_guard.py` |
| Entity resolution | deterministic identity modules, identity-review documentation |
| Golden Master | `src/promote_golden_master.py` and related tests |
| Campaign/history DQ | campaign/deliverable/performance builders and tests |
| PostgreSQL constraints | `sql/postgres/003_core_tables.sql` |
| Safe conversion / UPSERT | `sql/postgres/001_schemas_and_helpers.sql`, `004_incremental_upserts.sql` |
| Referential reconciliation | `sql/postgres/005_reconciliation.sql` |
| Source failure testing | `docs/reliability/reliability_failure_lab_v1.md` |
| Operational reliability | `docs/reliability/operational_reliability_v2.md` |
| Temporal reliability | `docs/reliability/temporal_reliability_v3.md` |
| Matching leakage / quality | `src/matching_v2.py`, matching tests |
| Warehouse contract | `docs/warehouse/data_dictionary_v1.md`, warehouse tests |
| CI/runtime validation | `.github/workflows/ci.yml`, synthetic PostgreSQL integration harness |

---

## 19. Summary

The project's Data Quality strategy is not a single validation script.

It is a layered governance model:

```text
Detect
→ classify
→ prevent unsafe promotion
→ preserve evidence
→ reconcile
→ test failure paths
→ recover
→ rerun
→ verify regression
```

The resulting portfolio demonstrates that Data Engineering quality requires more than a successful pipeline run:

```text
Build
→ Operate
→ Test
→ Break
→ Troubleshoot
→ Recover
→ Reconcile
→ Govern
→ Explain
```
