from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from typing import Iterable, Sequence


@dataclass(frozen=True)
class WatermarkValidation:
    status: str
    code: str
    watermark_date: str
    max_observed_event_date: str
    lag_days: int
    evidence: str


@dataclass(frozen=True)
class TemporalMonitoringEvent:
    run_id: str
    severity: str
    code: str
    metric: str
    observed_value: str
    threshold: str
    evidence: str


def parse_iso_date(value: object) -> date | None:
    text = str(value or "").strip()
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None


def dated_rows(rows: Iterable[dict], *, date_field: str = "event_date") -> list[dict]:
    result: list[dict] = []
    for row in rows:
        if parse_iso_date(row.get(date_field)) is not None:
            result.append(dict(row))
    return result


def annotate_arrival_dates(
    rows: Sequence[dict],
    *,
    id_field: str,
    date_field: str = "event_date",
    default_delay_days: int = 1,
    overrides: dict[str, str] | None = None,
) -> list[dict]:
    overrides = overrides or {}
    result: list[dict] = []
    for row in rows:
        event_date = parse_iso_date(row.get(date_field))
        if event_date is None:
            continue
        item = dict(row)
        item_id = str(item.get(id_field, ""))
        arrival = overrides.get(item_id)
        if arrival is None:
            arrival = (event_date + timedelta(days=default_delay_days)).isoformat()
        if parse_iso_date(arrival) is None:
            raise ValueError(f"invalid arrival date for {item_id}: {arrival!r}")
        item["arrival_date"] = arrival
        result.append(item)
    return result


def select_incremental_by_event_time(
    rows: Sequence[dict],
    watermark_date: str,
    *,
    date_field: str = "event_date",
) -> list[dict]:
    watermark = parse_iso_date(watermark_date)
    if watermark is None:
        raise ValueError(f"invalid watermark_date: {watermark_date!r}")
    result: list[dict] = []
    for row in rows:
        event_date = parse_iso_date(row.get(date_field))
        if event_date is not None and event_date > watermark:
            result.append(dict(row))
    return result


def detect_late_arrivals(
    rows: Sequence[dict],
    watermark_date: str,
    previous_arrival_cutoff: str,
    current_arrival_cutoff: str,
    *,
    date_field: str = "event_date",
    arrival_field: str = "arrival_date",
) -> list[dict]:
    watermark = parse_iso_date(watermark_date)
    previous_cutoff = parse_iso_date(previous_arrival_cutoff)
    current_cutoff = parse_iso_date(current_arrival_cutoff)
    if None in {watermark, previous_cutoff, current_cutoff}:
        raise ValueError("watermark/cutoff dates must use YYYY-MM-DD")
    if current_cutoff < previous_cutoff:
        raise ValueError("current_arrival_cutoff must be >= previous_arrival_cutoff")

    result: list[dict] = []
    for row in rows:
        event_date = parse_iso_date(row.get(date_field))
        arrival_date = parse_iso_date(row.get(arrival_field))
        if event_date is None or arrival_date is None:
            continue
        if event_date <= watermark and previous_cutoff < arrival_date <= current_cutoff:
            result.append(dict(row))
    return result


def validate_watermark(
    watermark_date: str,
    max_observed_event_date: str,
    *,
    max_staleness_days: int,
) -> WatermarkValidation:
    watermark = parse_iso_date(watermark_date)
    max_observed = parse_iso_date(max_observed_event_date)
    if watermark is None or max_observed is None:
        return WatermarkValidation(
            "FAIL",
            "WATERMARK_INVALID_FORMAT",
            watermark_date,
            max_observed_event_date,
            0,
            "watermark and max observed event date must use YYYY-MM-DD",
        )

    if watermark > max_observed:
        lag = (watermark - max_observed).days
        return WatermarkValidation(
            "FAIL",
            "WATERMARK_AHEAD_OF_SOURCE",
            watermark.isoformat(),
            max_observed.isoformat(),
            -lag,
            f"watermark is {lag} day(s) ahead of the maximum observed event date",
        )

    lag = (max_observed - watermark).days
    if lag > max_staleness_days:
        return WatermarkValidation(
            "FAIL",
            "WATERMARK_STALE",
            watermark.isoformat(),
            max_observed.isoformat(),
            lag,
            f"watermark trails the maximum observed event date by {lag} day(s), threshold={max_staleness_days}",
        )

    return WatermarkValidation(
        "PASS",
        "WATERMARK_VALID",
        watermark.isoformat(),
        max_observed.isoformat(),
        lag,
        f"watermark lag={lag} day(s) within threshold={max_staleness_days}",
    )


def backfill_fingerprint(rows: Sequence[dict], *, key_field: str) -> str:
    digest = hashlib.sha256()
    for value in sorted(str(row.get(key_field, "")) for row in rows):
        digest.update(value.encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def safe_backfill(
    rows: Sequence[dict],
    *,
    start_date: str,
    end_date: str,
    existing_keys: set[str],
    key_field: str,
    date_field: str = "event_date",
) -> dict:
    start = parse_iso_date(start_date)
    end = parse_iso_date(end_date)
    if start is None or end is None:
        raise ValueError("backfill start/end dates must use YYYY-MM-DD")
    if end < start:
        raise ValueError("backfill end_date must be >= start_date")

    by_key: dict[str, dict] = {}
    source_window_rows = 0
    duplicate_source_keys = 0
    for row in rows:
        event_date = parse_iso_date(row.get(date_field))
        if event_date is None or not (start <= event_date <= end):
            continue
        source_window_rows += 1
        key = str(row.get(key_field, "")).strip()
        if not key:
            continue
        if key in by_key:
            duplicate_source_keys += 1
        by_key[key] = dict(row)

    new_rows = [row for key, row in sorted(by_key.items()) if key not in existing_keys]
    skipped_existing = sum(1 for key in by_key if key in existing_keys)
    return {
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "source_window_rows": source_window_rows,
        "unique_source_keys": len(by_key),
        "duplicate_source_keys": duplicate_source_keys,
        "skipped_existing_keys": skipped_existing,
        "new_rows": new_rows,
        "new_row_count": len(new_rows),
        "backfill_fingerprint": backfill_fingerprint(new_rows, key_field=key_field),
    }


def apply_upsert(
    existing_rows: Sequence[dict],
    incoming_rows: Sequence[dict],
    *,
    key_field: str,
) -> tuple[list[dict], int, int]:
    merged: dict[str, dict] = {}
    for row in existing_rows:
        key = str(row.get(key_field, "")).strip()
        if key:
            merged[key] = dict(row)
    before = set(merged)
    updated = 0
    for row in incoming_rows:
        key = str(row.get(key_field, "")).strip()
        if not key:
            continue
        if key in merged and merged[key] != row:
            updated += 1
        merged[key] = dict(row)
    inserted = len(set(merged) - before)
    return [merged[key] for key in sorted(merged)], inserted, updated


def evaluate_temporal_slo(run: dict, thresholds: dict) -> list[TemporalMonitoringEvent]:
    run_id = str(run.get("run_id", ""))
    as_of = parse_iso_date(run.get("as_of_date"))
    latest_event = parse_iso_date(run.get("latest_loaded_event_date"))
    watermark = parse_iso_date(run.get("watermark_date"))
    if None in {as_of, latest_event, watermark}:
        raise ValueError("run as_of/latest_loaded_event/watermark dates must use YYYY-MM-DD")

    expected_rows = int(run.get("expected_rows", 0) or 0)
    loaded_rows = int(run.get("loaded_rows", 0) or 0)
    if expected_rows <= 0:
        raise ValueError("expected_rows must be > 0")

    freshness_lag_days = max(0, (as_of - latest_event).days)
    watermark_lag_days = max(0, (as_of - watermark).days)
    completeness_ratio = loaded_rows / expected_rows

    events: list[TemporalMonitoringEvent] = []
    max_freshness = int(thresholds.get("max_freshness_lag_days", 0) or 0)
    critical_freshness = int(thresholds.get("critical_freshness_lag_days", max_freshness) or max_freshness)
    if freshness_lag_days > max_freshness:
        severity = "CRITICAL" if freshness_lag_days > critical_freshness else "WARN"
        events.append(TemporalMonitoringEvent(
            run_id,
            severity,
            "FRESHNESS_SLO_BREACH",
            "freshness_lag_days",
            str(freshness_lag_days),
            str(max_freshness),
            f"latest_loaded_event_date={latest_event.isoformat()} as_of={as_of.isoformat()}",
        ))

    min_completeness = float(thresholds.get("min_completeness_ratio", 1.0))
    critical_completeness = float(thresholds.get("critical_completeness_ratio", min_completeness))
    if completeness_ratio < min_completeness:
        severity = "CRITICAL" if completeness_ratio < critical_completeness else "WARN"
        events.append(TemporalMonitoringEvent(
            run_id,
            severity,
            "COMPLETENESS_SLO_BREACH",
            "completeness_ratio",
            f"{completeness_ratio:.6f}",
            f"{min_completeness:.6f}",
            f"loaded_rows={loaded_rows} expected_rows={expected_rows}",
        ))

    max_watermark_lag = int(thresholds.get("max_watermark_lag_days", 0) or 0)
    if watermark_lag_days > max_watermark_lag:
        events.append(TemporalMonitoringEvent(
            run_id,
            "WARN",
            "WATERMARK_LAG_HIGH",
            "watermark_lag_days",
            str(watermark_lag_days),
            str(max_watermark_lag),
            f"watermark_date={watermark.isoformat()} as_of={as_of.isoformat()}",
        ))

    return events


def alerts_with_escalation(events: Sequence[TemporalMonitoringEvent], policy: dict) -> list[dict]:
    primary_channel = str(policy.get("primary_channel", "portfolio_lab_primary"))
    secondary_channel = str(policy.get("secondary_channel", "portfolio_lab_secondary"))
    escalate_after_minutes = int(policy.get("escalate_after_minutes", 30) or 30)
    escalate_severities = {str(v).upper() for v in policy.get("escalate_severities", ["CRITICAL"])}

    alerts: list[dict] = []
    for index, event in enumerate(events, start=1):
        alerts.append({
            "alert_id": f"ALT-{event.run_id}-{index:02d}-P",
            "run_id": event.run_id,
            "severity": event.severity,
            "alert_code": event.code,
            "channel": primary_channel,
            "escalation_level": "PRIMARY",
            "escalate_after_minutes": "",
            "delivery_status": "SIMULATED_DELIVERED",
            "message": event.evidence,
        })
        if event.severity.upper() in escalate_severities:
            alerts.append({
                "alert_id": f"ALT-{event.run_id}-{index:02d}-E",
                "run_id": event.run_id,
                "severity": event.severity,
                "alert_code": event.code,
                "channel": secondary_channel,
                "escalation_level": "ESCALATED",
                "escalate_after_minutes": escalate_after_minutes,
                "delivery_status": "SIMULATED_ESCALATED",
                "message": f"unresolved {event.code} escalated after {escalate_after_minutes} minutes in controlled lab",
            })
    return alerts


def dataclass_rows(values: Sequence[object]) -> list[dict]:
    return [asdict(value) for value in values]
