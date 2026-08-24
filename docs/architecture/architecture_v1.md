# Architecture v1 — Influencer Master Data & Campaign Matching Pipeline

## Status
Approved for implementation foundation.

## Business goal
Transform private multi-brand Excel campaign data into a trusted Influencer Master, campaign/performance history, and an explainable candidate-matching layer without exposing company PII.

## Architecture

```text
Private Excel Workbooks
        ↓
File Discovery + Registry
        ↓
Immutable Raw / Landing
        ↓
Workbook + Sheet Classification
        ↓
Adapter per Sheet Type
        ↓
Canonical Staging Contract
        ↓
Data Quality Gates
        ↓
PII Boundary
        ↓
Identity Observation
        ↓
Normalize → Exact → Deterministic → Alias → Manual Review
        ↓
Influencer Golden Master
        ↓
Campaign / Deliverable / Performance History
        ↓
Eligibility Rules
        ↓
Configurable Weighted Ranking
        ↓
Explainable Shortlist
        ↓
Human Review
        ↓
Campaign Result + Feedback
```

## Cross-cutting requirements
- Audit and lineage
- Structured logging
- Idempotency and rerun safety
- DQ evidence and quarantine
- Reconciliation
- PII isolation
- Versioned contracts/configuration

## MVP boundary
The first ingestion slice covers Influencer/Candidate sheets plus source metadata only. Live, Ads, Shipment, Sales/GMV and other operational/performance sheets are deferred until the registry, identity normalization, DQ and rerun contract are proven.

## Explicit non-goals for MVP
- No ML ranking
- No fuzzy auto-merge
- No Spark/Databricks
- No Airflow until recurring orchestration is justified
- No raw company workbook in public GitHub
