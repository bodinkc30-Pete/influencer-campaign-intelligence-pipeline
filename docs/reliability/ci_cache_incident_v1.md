# CI Cache Incident RCA v1

## Purpose

This document records a **public-safe CI failure investigation** from the Influencer Campaign Intelligence Pipeline portfolio.

It demonstrates the troubleshooting sequence:

```text
Detect
→ collect evidence
→ isolate failure stage
→ form hypotheses
→ verify root cause
→ apply minimal fix
→ rerun
→ validate recovery
→ retain prevention evidence
```

This is a **portfolio CI incident**, not a claim of production incident ownership.

---

## 1. Incident Summary

The first GitHub Actions CI execution for the repository failed before the automated test suite or PostgreSQL integration harness could run.

Incident evidence:

```text
GitHub Actions run: 32725009465
Run number: 1
Trigger: push
Head commit: b6955392cac389c99f0872f2815307727d6e84a4
Commit message: ci: add automated quality and postgres integration gates
Conclusion: failure
```

Both CI jobs failed during their `actions/setup-python@v6` step.

The failure was **not** caused by:

```text
pytest test failures
Python compilation failures
Docker Compose configuration failures
PostgreSQL migration failures
PostgreSQL integration assertions
```

Those downstream steps were skipped because Python setup failed first.

---

## 2. Affected CI Jobs

The workflow had two independent jobs:

```text
Fast Quality Gate
PostgreSQL Integration Gate
```

Run #1 evidence showed:

| Job | Failing step | Result |
|---|---|---|
| Fast Quality Gate | Set up Python | failure |
| PostgreSQL Integration Gate | Set up Python | failure |

Downstream test and integration steps were skipped after the setup failure.

This immediately narrowed the fault domain to a workflow/environment setup concern shared by both jobs.

---

## 3. Exact Failure Evidence

The Fast Quality Gate log recorded:

```text
No file in /home/runner/work/influencer-campaign-intelligence-pipeline/influencer-campaign-intelligence-pipeline
matched to [**/requirements.txt or **/pyproject.toml],
make sure you have checked out the target repository
```

The failing `actions/setup-python@v6` configuration included:

```yaml
python-version: '3.14'
cache: pip
```

but did not tell the action which dependency file should be used for the pip cache key.

The repository intentionally used:

```text
requirements-dev.txt
```

rather than the dependency filenames that the cache auto-detection was trying to locate.

---

## 4. Detection

The incident was detected by the hosted GitHub Actions result:

```text
run conclusion = failure
```

The first useful diagnostic step was to inspect job-level execution rather than assuming the application code was broken.

Job evidence showed:

```text
checkout        = success
set up Python   = failure
later steps     = skipped
```

This was critical because:

```text
CI failed
```

does not imply:

```text
tests failed
```

The execution timeline showed the suite never reached the test phase.

---

## 5. Initial Hypotheses

Based on the failure stage and message, reasonable hypotheses were:

```text
H1 — repository checkout failed or dependency files were missing
H2 — requested Python 3.14 was unavailable
H3 — setup-python pip cache dependency discovery could not find the repository's dependency file
H4 — pytest or PostgreSQL caused the failure
```

The evidence was then used to eliminate unsupported hypotheses.

---

## 6. Hypothesis Evaluation

### H1 — Checkout failure

Rejected.

Evidence:

```text
Check out repository = success
```

The runner had checked out the intended commit before `setup-python` failed.

### H2 — Python 3.14 unavailable

Rejected.

The setup log showed that CPython 3.14.7 was successfully resolved before the cache-related error was raised.

Therefore the Python version request itself was not the root cause.

### H3 — pip cache dependency discovery failure

Supported.

Evidence:

```text
cache: pip
```

was enabled, while the error specifically reported that cache dependency discovery found neither:

```text
requirements.txt
pyproject.toml
```

The repository dependency file was:

```text
requirements-dev.txt
```

This matched the failure exactly.

### H4 — pytest or PostgreSQL failure

Rejected.

Those steps were never executed in the failed run.

Therefore no evidence supported pytest, application logic, SQL migrations, Docker Compose, or PostgreSQL as the cause of Run #1.

---

## 7. Verified Root Cause

The verified root cause was:

> `actions/setup-python@v6` pip caching was enabled without an explicit `cache-dependency-path`, while the repository dependency manifest was named `requirements-dev.txt`.

As a result, the action attempted its default dependency-file discovery and did not find the filenames it expected.

This caused both jobs to fail at Python setup before any test execution.

The root cause is therefore classified as:

```text
CI workflow configuration defect
```

not:

```text
application defect
data-quality defect
PostgreSQL defect
test-suite defect
```

---

## 8. Minimal Corrective Action

The fix was intentionally narrow.

Commit:

```text
3b4b9966d4263a4731d665ec8fabdf6227c55eee
fix: configure setup-python dependency cache
```

Change applied to both Python setup blocks:

```yaml
cache-dependency-path: requirements-dev.txt
```

Conceptual diff:

```text
Fast Quality Gate
  setup-python
  + cache-dependency-path: requirements-dev.txt

PostgreSQL Integration Gate
  setup-python
  + cache-dependency-path: requirements-dev.txt
```

No application logic, SQL migration, test implementation, or warehouse behavior needed to change.

That is consistent with the evidence that the failure existed in CI cache configuration rather than pipeline code.

---

## 9. Recovery Execution

After the workflow fix was pushed, GitHub Actions executed the workflow again.

Recovery evidence:

```text
GitHub Actions run: 32726051052
Run number: 2
Trigger: push
Head commit: 3b4b9966d4263a4731d665ec8fabdf6227c55eee
Commit message: fix: configure setup-python dependency cache
Status: completed
Conclusion: success
```

Both jobs completed successfully:

```text
Fast Quality Gate              = success
PostgreSQL Integration Gate    = success
```

This established that the workflow could progress beyond the previously failing setup stage.

---

## 10. Fast Quality Gate Recovery Evidence

The recovered hosted job completed:

```text
Python setup
dependency installation
Python compilation
pytest regression
Docker Compose configuration validation
```

Hosted regression evidence:

```text
155 passed in 0.45s
```

The Docker Compose configuration validation also completed successfully.

This recovery evidence is important because it demonstrates that Run #1 did not contain a hidden pytest failure; once the setup configuration was corrected, the suite executed successfully.

---

## 11. PostgreSQL Integration Recovery Evidence

The recovered PostgreSQL Integration Gate successfully initialized its PostgreSQL service and ran the dedicated public-safe integration harness.

Hosted evidence included:

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

This confirmed that the CI fix restored the complete integration path, not merely the initial Python setup step.

---

## 12. Recovery Criteria

The incident was considered recovered only after the previously blocked workflow completed downstream validation.

Recovery criteria:

```text
setup-python succeeds
AND
dependency installation succeeds
AND
compileall succeeds
AND
155-test regression succeeds
AND
Compose config validation succeeds
AND
PostgreSQL integration succeeds
AND
same-batch idempotency evidence succeeds
AND
temporary integration database is cleaned up
```

This follows the project principle:

```text
Fix applied != Recovery proven
```

Recovery requires rerun and evidence.

---

## 13. Timeline

All timestamps below are GitHub-hosted CI timestamps in UTC.

```text
2026-08-24 12:03:03 UTC
Run #1 started on commit b695539...

2026-08-24 12:03:08 UTC
Fast Quality Gate reported setup-python cache dependency discovery failure.

2026-08-24 12:03 UTC
Both jobs ended without reaching their downstream tests/integration steps.

2026-08-24 12:12:52 UTC
Fix commit 3b4b996... created.

2026-08-24 12:14:32 UTC
Run #2 started on the fix commit.

2026-08-24 12:14:42 UTC
Hosted fast regression recorded 155 passed in 0.45s.

2026-08-24 12:15:39 UTC
PostgreSQL integration harness recorded PASS and temporary database cleanup.

2026-08-24 12:15:43 UTC
Run #2 completed successfully.
```

The timeline is evidence for this portfolio CI event only.

---

## 14. Incident Evidence Chain

```text
Run #1 failure
→ inspect job results
→ both jobs fail in setup-python
→ inspect setup log
→ exact dependency-discovery error
→ compare workflow configuration with repository dependency filename
→ identify requirements-dev.txt mismatch
→ add explicit cache-dependency-path
→ push fix
→ Run #2
→ both jobs succeed
→ 155 tests execute successfully
→ PostgreSQL integration executes successfully
→ recovery confirmed
```

---

## 15. Why This Is an RCA Rather Than a Guess

The root cause is not inferred merely from the fact that the later run passed.

It is supported by three connected evidence points:

```text
1. Failure location
   both jobs failed at setup-python

2. Failure message
   cache dependency discovery could not find requirements.txt or pyproject.toml

3. Corrective diff
   both setup-python blocks received:
   cache-dependency-path: requirements-dev.txt
```

The recovery run then validated the corrective action.

This satisfies:

```text
Failure evidence
+
mechanism
+
targeted fix
+
successful rerun
```

---

## 16. Prevention

The repository now makes the cache dependency manifest explicit:

```yaml
cache: pip
cache-dependency-path: requirements-dev.txt
```

This removes reliance on default dependency-file discovery for the current repository structure.

Additional prevention principles retained from this incident:

```text
inspect the first failed step
do not diagnose from the final workflow status alone
distinguish environment/configuration failures from test failures
make repository-specific dependency contracts explicit
validate recovery through the complete downstream path
```

---

## 17. What Was Not Changed

The incident did not require changes to:

```text
Python business logic
entity resolution
Golden Master logic
campaign history
performance history
matching logic
PostgreSQL migrations
warehouse reconciliation logic
synthetic integration fixture semantics
pytest assertions
Docker Compose service design
```

This is useful evidence that the correction remained scoped to the verified cause.

---

## 18. Security and Public-Safety Boundary

This incident record intentionally excludes:

```text
personal access tokens
GitHub authentication credentials
local .env secrets
private company workbook data
real PII
private source-derived runtime evidence
```

GitHub-hosted secrets and tokens are not reproduced in this document.

The integration evidence referenced here uses the repository's public-safe synthetic CI fixture.

---

## 19. Claim Boundary

This document demonstrates:

```text
CI troubleshooting
failure-stage isolation
evidence-based RCA
minimal workflow correction
rerun validation
regression validation
PostgreSQL integration recovery
```

It does not claim:

```text
production outage ownership
customer-impacting incident management
enterprise on-call experience
production SRE responsibility
production MTTR/SLA performance
```

The event occurred in a portfolio engineering environment.

---

## 20. Interview-Safe Explanation

A concise interview explanation is:

```text
My first GitHub Actions run failed before tests started. Both CI jobs failed
inside setup-python because pip caching could not auto-discover a supported
dependency manifest. The repository used requirements-dev.txt, so I verified
the failure from the job logs and added cache-dependency-path explicitly to
both setup-python blocks. I then reran CI. The fast gate completed 155 tests
and Compose validation, while the PostgreSQL integration gate successfully
ran the synthetic warehouse load, proved same-batch idempotency, and cleaned
up the temporary database.
```

This describes the evidence without presenting the portfolio incident as production experience.

---

## 21. Evidence References

| Evidence | Reference |
|---|---|
| Failed CI run | GitHub Actions Run `32725009465` |
| Failed head commit | `b6955392cac389c99f0872f2815307727d6e84a4` |
| Failed workflow file | `.github/workflows/ci.yml` at the failed commit |
| Exact failure stage | `Set up Python` in both CI jobs |
| Corrective commit | `3b4b9966d4263a4731d665ec8fabdf6227c55eee` |
| Corrective change | `cache-dependency-path: requirements-dev.txt` in both jobs |
| Recovery CI run | GitHub Actions Run `32726051052` |
| Recovery regression | `155 passed in 0.45s` |
| Recovery integration | public-safe PostgreSQL integration harness PASS |
| Current workflow | `.github/workflows/ci.yml` |
| Testing evidence | `docs/portfolio/testing_evidence_v1.md` |

---

## 22. Summary

The incident demonstrates a small but important Data Engineering troubleshooting pattern:

```text
workflow failure
≠
application failure
```

The useful engineering behavior was to locate the first failing stage, collect the exact error, connect it to repository configuration, change only the supported cause, and then prove recovery through the entire downstream test path.

Final incident chain:

```text
Detect
→ Evidence
→ Hypotheses
→ Verified RCA
→ Minimal Fix
→ Rerun
→ Regression
→ Integration Recovery
→ Prevention
→ Explain
```
