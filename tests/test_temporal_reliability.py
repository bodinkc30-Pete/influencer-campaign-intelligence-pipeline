from __future__ import annotations

from src.temporal_reliability import (
    alerts_with_escalation,
    annotate_arrival_dates,
    apply_upsert,
    dated_rows,
    detect_late_arrivals,
    evaluate_temporal_slo,
    safe_backfill,
    select_incremental_by_event_time,
    validate_watermark,
)


def _events() -> list[dict[str, str]]:
    return [
        {"id": "a", "event_date": "2026-05-18"},
        {"id": "b", "event_date": "2026-05-20"},
        {"id": "c", "event_date": "2026-05-22"},
    ]


def test_dated_rows_excludes_non_iso_values() -> None:
    rows = [{"id": "a", "event_date": "2026-05-18"}, {"id": "b", "event_date": "not-a-date"}]
    assert [r["id"] for r in dated_rows(rows)] == ["a"]


def test_valid_watermark_passes() -> None:
    result = validate_watermark("2026-06-24", "2026-06-25", max_staleness_days=7)
    assert result.status == "PASS"
    assert result.code == "WATERMARK_VALID"


def test_watermark_ahead_of_source_is_blocking() -> None:
    result = validate_watermark("2026-07-01", "2026-06-25", max_staleness_days=7)
    assert result.status == "FAIL"
    assert result.code == "WATERMARK_AHEAD_OF_SOURCE"


def test_stale_watermark_is_blocking() -> None:
    result = validate_watermark("2026-05-01", "2026-06-25", max_staleness_days=7)
    assert result.status == "FAIL"
    assert result.code == "WATERMARK_STALE"


def test_strict_event_time_incremental_misses_late_row() -> None:
    rows = annotate_arrival_dates(_events(), id_field="id", overrides={"a": "2026-05-24"})
    selected = select_incremental_by_event_time(rows, "2026-05-20")
    assert {r["id"] for r in selected} == {"c"}
    assert "a" not in {r["id"] for r in selected}


def test_late_arrival_detector_finds_row_behind_watermark() -> None:
    rows = annotate_arrival_dates(_events(), id_field="id", overrides={"a": "2026-05-24"})
    late = detect_late_arrivals(rows, "2026-05-20", "2026-05-21", "2026-05-25")
    assert [r["id"] for r in late] == ["a"]


def test_safe_backfill_recovers_only_missing_key() -> None:
    rows = _events()
    result = safe_backfill(
        rows,
        start_date="2026-05-17",
        end_date="2026-05-20",
        existing_keys={"b", "c"},
        key_field="id",
    )
    assert result["new_row_count"] == 1
    assert result["new_rows"][0]["id"] == "a"


def test_backfill_upsert_rerun_is_idempotent() -> None:
    existing = [{"id": "b", "event_date": "2026-05-20"}]
    incoming = [{"id": "a", "event_date": "2026-05-18"}]
    merged, inserted, _ = apply_upsert(existing, incoming, key_field="id")
    rerun, inserted_again, _ = apply_upsert(merged, incoming, key_field="id")
    assert inserted == 1
    assert inserted_again == 0
    assert len(rerun) == 2


def test_temporal_slo_detects_freshness_breach() -> None:
    events = evaluate_temporal_slo(
        {"run_id": "r1", "as_of_date": "2026-06-26", "latest_loaded_event_date": "2026-06-20", "watermark_date": "2026-06-25", "expected_rows": 100, "loaded_rows": 100},
        {"max_freshness_lag_days": 2, "critical_freshness_lag_days": 4, "min_completeness_ratio": 0.99, "critical_completeness_ratio": 0.98, "max_watermark_lag_days": 2},
    )
    event = next(e for e in events if e.code == "FRESHNESS_SLO_BREACH")
    assert event.severity == "CRITICAL"


def test_temporal_slo_detects_completeness_breach() -> None:
    events = evaluate_temporal_slo(
        {"run_id": "r1", "as_of_date": "2026-06-26", "latest_loaded_event_date": "2026-06-25", "watermark_date": "2026-06-25", "expected_rows": 100, "loaded_rows": 95},
        {"max_freshness_lag_days": 2, "critical_freshness_lag_days": 4, "min_completeness_ratio": 0.99, "critical_completeness_ratio": 0.98, "max_watermark_lag_days": 2},
    )
    event = next(e for e in events if e.code == "COMPLETENESS_SLO_BREACH")
    assert event.severity == "CRITICAL"


def test_clean_temporal_slo_has_no_events() -> None:
    events = evaluate_temporal_slo(
        {"run_id": "r1", "as_of_date": "2026-06-26", "latest_loaded_event_date": "2026-06-25", "watermark_date": "2026-06-25", "expected_rows": 100, "loaded_rows": 100},
        {"max_freshness_lag_days": 2, "critical_freshness_lag_days": 4, "min_completeness_ratio": 0.99, "critical_completeness_ratio": 0.98, "max_watermark_lag_days": 2},
    )
    assert events == []


def test_critical_alert_is_escalated() -> None:
    events = evaluate_temporal_slo(
        {"run_id": "r1", "as_of_date": "2026-06-26", "latest_loaded_event_date": "2026-06-20", "watermark_date": "2026-06-18", "expected_rows": 100, "loaded_rows": 95},
        {"max_freshness_lag_days": 2, "critical_freshness_lag_days": 4, "min_completeness_ratio": 0.99, "critical_completeness_ratio": 0.98, "max_watermark_lag_days": 2},
    )
    alerts = alerts_with_escalation(events, {"primary_channel": "p", "secondary_channel": "s", "escalate_after_minutes": 30, "escalate_severities": ["CRITICAL"]})
    assert any(a["escalation_level"] == "ESCALATED" for a in alerts)
    assert all(a["delivery_status"].startswith("SIMULATED") for a in alerts)
