# Operational Reliability v2

This extension demonstrates operational controls after the source-boundary failure lab. It is a portfolio / production-like lab, not a claim of production incident experience.

## Controlled scenarios

1. bad incremental state pointing to a batch that is not a successful run;
2. partial load / interrupted batch leaving staging data without a commit marker;
3. transient dependency failure recovered with bounded retry evidence;
4. monitoring and alert generation for failed, slow, retry-heavy, incomplete runs.

## Operational contract

```text
Run Start
→ Incremental State Gate
→ Stage Write
→ Atomic Commit
→ Run Ledger
→ Monitoring Evaluation
→ Alert Evidence
→ Reconciliation
```

A successful pipeline run must record at least:

- `run_id` and `batch_fingerprint`;
- start/end timestamps and duration;
- current stage and final status;
- rows attempted / loaded / rejected;
- retry count;
- failure code / failed stage when applicable;
- commit status;
- reconciliation status.

## Recovery rules

- incremental state is only advanced after a successful committed run;
- an unknown or malformed incremental-state pointer blocks processing;
- staging data without a commit marker is never treated as loaded data;
- recovery removes orphan staging and performs a full atomic rerun;
- committing the same `run_id` twice is idempotent;
- retries are bounded and only catch explicitly retryable failures;
- monitoring alerts are evidence artifacts in this lab and do not call a real external notification service.

## Portfolio guardrail

`Pipeline SUCCESS != Data Correct`. Recovery is not complete until row counts, fingerprints and state transitions reconcile and regression tests pass.
