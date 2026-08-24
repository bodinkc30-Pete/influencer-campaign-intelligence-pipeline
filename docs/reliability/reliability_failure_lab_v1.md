# Reliability Failure Lab v1

This extension demonstrates controlled failure experiments for the Excel source boundary of the Influencer Data Matching pipeline.

## Scope

1. Missing workbook
2. Duplicate workbook content
3. Candidate schema drift / column rename
4. Empty expected candidate sheet
5. Same-batch rerun / idempotency

The public project contains detection/recovery logic and synthetic regression tests only. Real company workbooks and private incident evidence are excluded from the public repository.

## Experiment method

`Hypothesis -> Inject Failure -> Detect -> Evidence -> Verified Cause -> Fix -> Recover -> Rerun -> Reconcile -> Regression -> Prevent`

## Important controls

- Approved source baseline manifest
- SHA-256 duplicate-content hard gate
- Candidate header-signature drift detection
- Expected non-empty sheet validation
- Deterministic batch fingerprint + atomic idempotency ledger

## Portfolio claim boundary

This is a controlled portfolio lab / production-like simulation. It is not production incident experience.
