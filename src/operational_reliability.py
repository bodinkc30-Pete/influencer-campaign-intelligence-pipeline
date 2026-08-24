from __future__ import annotations

import csv
import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable, Sequence


@dataclass(frozen=True)
class IncrementalStateValidation:
    status: str
    code: str
    evidence: str


@dataclass(frozen=True)
class RetryAttempt:
    run_id: str
    attempt: int
    outcome: str
    error_type: str
    error_message: str
    scheduled_backoff_seconds: float


@dataclass(frozen=True)
class MonitoringEvent:
    run_id: str
    severity: str
    code: str
    metric: str
    observed_value: str
    threshold: str
    evidence: str


class RetryableDependencyError(RuntimeError):
    """Transient failure that may succeed when retried."""


class RetryExhaustedError(RuntimeError):
    """Raised when all retry attempts are consumed."""


class PartialLoadInjected(RuntimeError):
    """Controlled failure used by the portfolio reliability lab."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temp_path, path)


def atomic_write_csv(path: Path, fieldnames: Sequence[str], rows: Iterable[dict]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    count = 0
    with temp_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(fieldnames))
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})
            count += 1
    os.replace(temp_path, path)
    return count


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def rows_fingerprint(rows: Sequence[dict], key_fields: Sequence[str]) -> str:
    digest = hashlib.sha256()
    normalized: list[str] = []
    for row in rows:
        normalized.append("|".join(str(row.get(field, "")) for field in key_fields))
    for value in sorted(normalized):
        digest.update(value.encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def load_json(path: Path, default: dict | None = None) -> dict:
    if not path.exists():
        return dict(default or {})
    return json.loads(path.read_text(encoding="utf-8"))


def append_run_ledger_event(path: Path, event: dict) -> None:
    payload = load_json(path, {"ledger_version": 1, "runs": []})
    payload.setdefault("ledger_version", 1)
    payload.setdefault("runs", []).append(dict(event))
    atomic_write_json(path, payload)


def successful_batch_fingerprints(run_ledger: dict) -> set[str]:
    result: set[str] = set()
    for event in run_ledger.get("runs", []):
        if str(event.get("status", "")).upper() == "SUCCESS" and event.get("batch_fingerprint"):
            result.add(str(event["batch_fingerprint"]))
    return result


def validate_incremental_state(state: dict, run_ledger: dict) -> IncrementalStateValidation:
    if int(state.get("state_version", 0) or 0) != 1:
        return IncrementalStateValidation(
            "FAIL",
            "BAD_INCREMENTAL_STATE_VERSION",
            f"expected state_version=1; actual={state.get('state_version')!r}",
        )

    last_successful = str(state.get("last_successful_batch_fingerprint", "")).strip()
    if not last_successful:
        return IncrementalStateValidation(
            "FAIL",
            "BAD_INCREMENTAL_STATE_EMPTY_POINTER",
            "last_successful_batch_fingerprint is blank",
        )

    known_successes = successful_batch_fingerprints(run_ledger)
    if last_successful not in known_successes:
        return IncrementalStateValidation(
            "FAIL",
            "BAD_INCREMENTAL_STATE_UNKNOWN_BATCH",
            f"state points to batch {last_successful[:16]} not found as SUCCESS in the run ledger",
        )

    return IncrementalStateValidation(
        "PASS",
        "INCREMENTAL_STATE_VALID",
        f"state points to known successful batch {last_successful[:16]}",
    )


def create_incremental_state(batch_fingerprint: str, run_id: str) -> dict:
    return {
        "state_version": 1,
        "last_successful_batch_fingerprint": batch_fingerprint,
        "last_successful_run_id": run_id,
        "updated_at_utc": utc_now(),
    }


def staging_paths(work_dir: Path, run_id: str) -> tuple[Path, Path, Path]:
    staging = work_dir / "staging" / f"{run_id}.csv"
    committed = work_dir / "committed" / f"{run_id}.csv"
    manifest = work_dir / "committed" / f"{run_id}.commit.json"
    return staging, committed, manifest


def inject_partial_load(
    rows: Sequence[dict],
    work_dir: Path,
    run_id: str,
    *,
    fail_after_rows: int,
) -> None:
    if not rows:
        raise ValueError("rows must not be empty")
    fieldnames = list(rows[0].keys())
    staging, _, _ = staging_paths(work_dir, run_id)
    staging.parent.mkdir(parents=True, exist_ok=True)
    with staging.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for index, row in enumerate(rows, start=1):
            writer.writerow(row)
            if index >= fail_after_rows:
                break
    raise PartialLoadInjected(
        f"controlled interruption after {min(fail_after_rows, len(rows))} of {len(rows)} rows"
    )


def count_csv_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return sum(1 for _ in csv.DictReader(f))


def detect_partial_load(work_dir: Path, run_id: str, *, expected_rows: int) -> dict:
    staging, committed, manifest = staging_paths(work_dir, run_id)
    staging_rows = count_csv_rows(staging)
    committed_rows = count_csv_rows(committed)
    commit_exists = manifest.exists()

    if staging.exists() and not commit_exists:
        return {
            "status": "FAIL",
            "code": "PARTIAL_LOAD_STAGING_WITHOUT_COMMIT",
            "expected_rows": expected_rows,
            "staging_rows": staging_rows,
            "committed_rows": committed_rows,
            "commit_manifest_exists": False,
        }
    if committed.exists() and commit_exists and committed_rows != expected_rows:
        return {
            "status": "FAIL",
            "code": "COMMITTED_ROW_COUNT_MISMATCH",
            "expected_rows": expected_rows,
            "staging_rows": staging_rows,
            "committed_rows": committed_rows,
            "commit_manifest_exists": True,
        }
    return {
        "status": "PASS",
        "code": "LOAD_STATE_CLEAN",
        "expected_rows": expected_rows,
        "staging_rows": staging_rows,
        "committed_rows": committed_rows,
        "commit_manifest_exists": commit_exists,
    }


def commit_rows_atomically(
    rows: Sequence[dict],
    work_dir: Path,
    run_id: str,
    *,
    key_fields: Sequence[str],
) -> dict:
    if not rows:
        raise ValueError("rows must not be empty")
    staging, committed, manifest = staging_paths(work_dir, run_id)

    if manifest.exists() and committed.exists():
        prior_manifest = load_json(manifest)
        return {
            "action": "SKIP_ALREADY_COMMITTED",
            "committed_rows": count_csv_rows(committed),
            "row_fingerprint": prior_manifest.get("row_fingerprint", ""),
        }

    if staging.exists():
        staging.unlink()

    fieldnames = list(rows[0].keys())
    staging.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_csv(staging, fieldnames, rows)
    committed.parent.mkdir(parents=True, exist_ok=True)
    os.replace(staging, committed)

    fingerprint = rows_fingerprint(rows, key_fields)
    commit_payload = {
        "commit_version": 1,
        "run_id": run_id,
        "committed_rows": len(rows),
        "row_fingerprint": fingerprint,
        "committed_at_utc": utc_now(),
    }
    atomic_write_json(manifest, commit_payload)
    return {
        "action": "COMMIT_NEW_BATCH",
        "committed_rows": len(rows),
        "row_fingerprint": fingerprint,
    }


def recover_partial_load(
    rows: Sequence[dict],
    work_dir: Path,
    run_id: str,
    *,
    key_fields: Sequence[str],
) -> dict:
    staging, _, _ = staging_paths(work_dir, run_id)
    removed_staging = staging.exists()
    if staging.exists():
        staging.unlink()
    committed = commit_rows_atomically(rows, work_dir, run_id, key_fields=key_fields)
    return {
        "removed_orphan_staging": removed_staging,
        **committed,
    }


def execute_with_retry(
    operation: Callable[[], object],
    *,
    run_id: str,
    max_attempts: int,
    backoff_seconds: Sequence[float],
) -> tuple[object, list[RetryAttempt]]:
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")

    attempts: list[RetryAttempt] = []
    for attempt in range(1, max_attempts + 1):
        backoff = 0.0 if attempt == 1 else float(backoff_seconds[min(attempt - 2, len(backoff_seconds) - 1)]) if backoff_seconds else 0.0
        try:
            result = operation()
            attempts.append(RetryAttempt(run_id, attempt, "SUCCESS", "", "", backoff))
            return result, attempts
        except RetryableDependencyError as exc:
            attempts.append(
                RetryAttempt(
                    run_id,
                    attempt,
                    "RETRY" if attempt < max_attempts else "FAILED",
                    type(exc).__name__,
                    str(exc),
                    backoff,
                )
            )
            if attempt >= max_attempts:
                raise RetryExhaustedError(
                    f"run {run_id} exhausted {max_attempts} attempts: {exc}"
                ) from exc

    raise AssertionError("unreachable")


def evaluate_monitoring(run: dict, thresholds: dict) -> list[MonitoringEvent]:
    events: list[MonitoringEvent] = []
    run_id = str(run.get("run_id", ""))
    status = str(run.get("status", "")).upper()
    duration_seconds = float(run.get("duration_seconds", 0) or 0)
    retry_count = int(run.get("retry_count", 0) or 0)
    rows_attempted = int(run.get("rows_attempted", 0) or 0)
    rows_loaded = int(run.get("rows_loaded", 0) or 0)
    rows_rejected = int(run.get("rows_rejected", 0) or 0)

    if status == "FAILED":
        events.append(
            MonitoringEvent(
                run_id,
                "CRITICAL",
                "RUN_FAILED",
                "status",
                status,
                "SUCCESS",
                f"run failed at stage={run.get('failed_stage', '')}",
            )
        )

    max_duration = float(thresholds.get("max_duration_seconds", 0) or 0)
    if max_duration and duration_seconds > max_duration:
        events.append(
            MonitoringEvent(
                run_id,
                "WARN",
                "RUN_DURATION_HIGH",
                "duration_seconds",
                str(duration_seconds),
                str(max_duration),
                "run duration exceeded configured threshold",
            )
        )

    max_retries = int(thresholds.get("max_retry_count", 0) or 0)
    if retry_count > max_retries:
        events.append(
            MonitoringEvent(
                run_id,
                "WARN",
                "RETRY_COUNT_HIGH",
                "retry_count",
                str(retry_count),
                str(max_retries),
                "retry count exceeded configured threshold",
            )
        )

    max_rejected = int(thresholds.get("max_rejected_rows", 0) or 0)
    if rows_rejected > max_rejected:
        events.append(
            MonitoringEvent(
                run_id,
                "WARN",
                "REJECTED_ROWS_HIGH",
                "rows_rejected",
                str(rows_rejected),
                str(max_rejected),
                "rejected rows exceeded configured threshold",
            )
        )

    min_completeness = float(thresholds.get("min_row_completeness", 0) or 0)
    if rows_attempted > 0:
        completeness = rows_loaded / rows_attempted
        if completeness < min_completeness:
            events.append(
                MonitoringEvent(
                    run_id,
                    "CRITICAL",
                    "ROW_COMPLETENESS_LOW",
                    "row_completeness",
                    f"{completeness:.6f}",
                    f"{min_completeness:.6f}",
                    f"loaded={rows_loaded} attempted={rows_attempted}",
                )
            )

    return events


def alerts_from_events(events: Sequence[MonitoringEvent]) -> list[dict]:
    alerts: list[dict] = []
    for index, event in enumerate(events, start=1):
        alerts.append(
            {
                "alert_id": f"alert_{index:03d}_{event.run_id}",
                "run_id": event.run_id,
                "severity": event.severity,
                "alert_code": event.code,
                "message": f"{event.code}: {event.evidence}",
                "delivery_status": "SIMULATED_DELIVERED",
                "channel": "portfolio_lab_sink",
            }
        )
    return alerts


def dataclass_rows(items: Sequence[object]) -> list[dict]:
    return [asdict(item) for item in items]
