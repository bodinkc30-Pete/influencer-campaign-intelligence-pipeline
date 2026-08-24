# Temporal Reliability & Data SLO v3

This extension covers late-arriving data, watermark safety, safe backfill, idempotent replay, freshness/completeness SLOs, and simulated alert escalation. It is a portfolio / production-like lab, not a production incident claim.

## Why this layer exists

A pipeline can finish with status `SUCCESS` and still be wrong when an event-time watermark moves past data that arrives later. Temporal reliability therefore needs controls beyond task status.

```text
Event Time
+ Arrival Time
+ Watermark
+ Incremental Selection
+ Late-arrival Detection
+ Safe Backfill
+ Idempotent Upsert
+ Freshness / Completeness SLO
+ Alert Escalation Evidence
```

## Controlled scenarios

1. a late performance record arrives after its event-time watermark and is missed by strict `event_date > watermark` selection;
2. a watermark is ahead of the maximum observed source event date;
3. a stale watermark falls behind the source by more than the governed lag threshold;
4. a bounded backfill recovers missed rows and a repeated backfill inserts no duplicates;
5. freshness/completeness/watermark SLO breaches emit monitoring events and simulated escalation, followed by a clean recovery run.

## Important evidence semantics

The private source has event dates but does **not** contain authoritative ingestion/arrival timestamps. The lab therefore keeps real project event records and lineage while injecting controlled synthetic arrival dates only for the late-arrival experiment. Those synthetic timestamps must never be presented as company production metadata.

## Watermark contract

A watermark must:

- parse as `YYYY-MM-DD`;
- never be ahead of the maximum observed governed event date;
- not lag the governed maximum event date by more than the configured threshold without an explicit backfill/recovery state;
- advance only after a reconciled successful load.

## Backfill contract

Backfill is bounded by an explicit event-date interval and uses a stable business key. Existing keys are skipped or upserted rather than blindly appended. Rerunning the same recovered backfill must insert zero additional rows.

## SLO / SLA distinction

This project implements internal **SLO** controls for freshness, completeness and watermark lag. It does not invent an **SLA** because no approved external/business commitment exists in the source material.

## Alerting guardrail

Alerts and escalation are written to portfolio evidence only. No external production notification integration is claimed.
