from __future__ import annotations

from pathlib import Path

import pytest

from src.operational_reliability import (
    PartialLoadInjected,
    RetryExhaustedError,
    RetryableDependencyError,
    alerts_from_events,
    commit_rows_atomically,
    create_incremental_state,
    detect_partial_load,
    evaluate_monitoring,
    execute_with_retry,
    inject_partial_load,
    recover_partial_load,
    validate_incremental_state,
)


def _rows() -> list[dict[str, str]]:
    return [
        {"influencer_id": "inf_1", "value": "10"},
        {"influencer_id": "inf_2", "value": "20"},
        {"influencer_id": "inf_3", "value": "30"},
    ]


def test_valid_incremental_state_passes() -> None:
    ledger = {"runs": [{"status": "SUCCESS", "batch_fingerprint": "batch_ok"}]}
    state = create_incremental_state("batch_ok", "run_1")
    result = validate_incremental_state(state, ledger)
    assert result.status == "PASS"
    assert result.code == "INCREMENTAL_STATE_VALID"


def test_unknown_incremental_pointer_is_blocking() -> None:
    ledger = {"runs": [{"status": "SUCCESS", "batch_fingerprint": "batch_ok"}]}
    state = create_incremental_state("tampered_batch", "run_bad")
    result = validate_incremental_state(state, ledger)
    assert result.status == "FAIL"
    assert result.code == "BAD_INCREMENTAL_STATE_UNKNOWN_BATCH"


def test_partial_staging_without_commit_is_detected(tmp_path: Path) -> None:
    with pytest.raises(PartialLoadInjected):
        inject_partial_load(_rows(), tmp_path, "run_partial", fail_after_rows=2)
    result = detect_partial_load(tmp_path, "run_partial", expected_rows=3)
    assert result["status"] == "FAIL"
    assert result["code"] == "PARTIAL_LOAD_STAGING_WITHOUT_COMMIT"
    assert result["staging_rows"] == 2


def test_partial_load_recovery_reconciles_exact_rows(tmp_path: Path) -> None:
    rows = _rows()
    with pytest.raises(PartialLoadInjected):
        inject_partial_load(rows, tmp_path, "run_partial", fail_after_rows=1)
    recovered = recover_partial_load(
        rows,
        tmp_path,
        "run_partial",
        key_fields=["influencer_id"],
    )
    assert recovered["removed_orphan_staging"] is True
    result = detect_partial_load(tmp_path, "run_partial", expected_rows=3)
    assert result["status"] == "PASS"
    assert result["committed_rows"] == 3


def test_atomic_commit_rerun_is_idempotent(tmp_path: Path) -> None:
    rows = _rows()
    first = commit_rows_atomically(rows, tmp_path, "run_1", key_fields=["influencer_id"])
    second = commit_rows_atomically(rows, tmp_path, "run_1", key_fields=["influencer_id"])
    assert first["action"] == "COMMIT_NEW_BATCH"
    assert second["action"] == "SKIP_ALREADY_COMMITTED"
    assert second["committed_rows"] == 3
    assert second["row_fingerprint"] == first["row_fingerprint"]


def test_retry_recovers_after_transient_failures() -> None:
    calls = {"count": 0}

    def operation() -> str:
        calls["count"] += 1
        if calls["count"] < 3:
            raise RetryableDependencyError("temporary dependency disconnect")
        return "ok"

    result, attempts = execute_with_retry(
        operation,
        run_id="run_retry",
        max_attempts=4,
        backoff_seconds=[1, 2, 4],
    )
    assert result == "ok"
    assert [a.outcome for a in attempts] == ["RETRY", "RETRY", "SUCCESS"]
    assert calls["count"] == 3


def test_retry_exhaustion_is_blocking() -> None:
    def operation() -> None:
        raise RetryableDependencyError("still unavailable")

    with pytest.raises(RetryExhaustedError):
        execute_with_retry(
            operation,
            run_id="run_retry_fail",
            max_attempts=3,
            backoff_seconds=[1, 2],
        )


def test_monitoring_emits_failure_and_completeness_alerts() -> None:
    run = {
        "run_id": "run_failed",
        "status": "FAILED",
        "failed_stage": "LOAD",
        "duration_seconds": 900,
        "retry_count": 3,
        "rows_attempted": 100,
        "rows_loaded": 40,
        "rows_rejected": 2,
    }
    events = evaluate_monitoring(
        run,
        {
            "max_duration_seconds": 300,
            "max_retry_count": 2,
            "max_rejected_rows": 0,
            "min_row_completeness": 1.0,
        },
    )
    codes = {e.code for e in events}
    assert {"RUN_FAILED", "RUN_DURATION_HIGH", "RETRY_COUNT_HIGH", "REJECTED_ROWS_HIGH", "ROW_COMPLETENESS_LOW"} <= codes
    alerts = alerts_from_events(events)
    assert len(alerts) == len(events)
    assert all(a["delivery_status"] == "SIMULATED_DELIVERED" for a in alerts)


def test_monitoring_success_under_threshold_has_no_alerts() -> None:
    run = {
        "run_id": "run_ok",
        "status": "SUCCESS",
        "duration_seconds": 30,
        "retry_count": 0,
        "rows_attempted": 100,
        "rows_loaded": 100,
        "rows_rejected": 0,
    }
    events = evaluate_monitoring(
        run,
        {
            "max_duration_seconds": 300,
            "max_retry_count": 2,
            "max_rejected_rows": 0,
            "min_row_completeness": 1.0,
        },
    )
    assert events == []


def test_incremental_state_version_mismatch_is_blocking() -> None:
    ledger = {"runs": [{"status": "SUCCESS", "batch_fingerprint": "batch_ok"}]}
    state = {"state_version": 99, "last_successful_batch_fingerprint": "batch_ok"}
    result = validate_incremental_state(state, ledger)
    assert result.status == "FAIL"
    assert result.code == "BAD_INCREMENTAL_STATE_VERSION"
