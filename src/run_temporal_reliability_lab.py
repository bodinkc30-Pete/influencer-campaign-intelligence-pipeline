from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import timedelta
from pathlib import Path

from src.temporal_reliability import (
    alerts_with_escalation,
    annotate_arrival_dates,
    apply_upsert,
    dataclass_rows,
    dated_rows,
    detect_late_arrivals,
    evaluate_temporal_slo,
    parse_iso_date,
    safe_backfill,
    select_incremental_by_event_time,
    validate_watermark,
)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run_lab(source_dir: Path, performance_csv: Path, output_dir: Path, config_path: Path) -> dict:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    raw_rows = read_csv(performance_csv)
    temporal_rows = dated_rows(raw_rows, date_field="event_date")
    if not temporal_rows:
        raise RuntimeError("no ISO event_date rows available for temporal reliability lab")

    key_field = "campaign_performance_id"
    event_dates = sorted(parse_iso_date(r["event_date"]) for r in temporal_rows if parse_iso_date(r["event_date"]) is not None)
    min_event = event_dates[0]
    max_event = event_dates[-1]
    expected_rows = len({r[key_field] for r in temporal_rows})

    source_files = sorted(source_dir.glob("*.xlsx"))
    source_hashes_before = {p.name: sha256_file(p) for p in source_files}

    experiments: list[dict] = []
    incidents: list[dict] = []
    timeline: list[dict] = []
    run_ledger: list[dict] = []
    watermark_evidence: list[dict] = []
    late_evidence: list[dict] = []
    backfill_evidence: list[dict] = []

    late_cfg = config["late_arrival"]
    watermark_date = late_cfg["watermark_date"]
    previous_cutoff = late_cfg["previous_arrival_cutoff"]
    current_cutoff = late_cfg["current_arrival_cutoff"]
    watermark_dt = parse_iso_date(watermark_date)
    if watermark_dt is None:
        raise RuntimeError("invalid configured watermark_date")

    # Pick a real source row inside the governed backfill lookback window.
    lookback_days = int(late_cfg["backfill_lookback_days"])
    backfill_start = (watermark_dt - timedelta(days=lookback_days)).isoformat()
    late_candidates = [
        r for r in temporal_rows
        if parse_iso_date(r["event_date"]) is not None
        and parse_iso_date(backfill_start) <= parse_iso_date(r["event_date"]) <= watermark_dt
    ]
    if not late_candidates:
        raise RuntimeError("no source row available inside controlled late-arrival window")
    late_source_row = sorted(late_candidates, key=lambda r: (r["event_date"], r[key_field]))[-1]
    late_id = late_source_row[key_field]
    synthetic_late_arrival = (parse_iso_date(previous_cutoff) + timedelta(days=3)).isoformat()
    annotated = annotate_arrival_dates(
        temporal_rows,
        id_field=key_field,
        overrides={late_id: synthetic_late_arrival},
    )

    # TEMP-001: strict event-time incremental misses a late arrival behind the watermark.
    incremental_selected = select_incremental_by_event_time(annotated, watermark_date)
    late_rows = detect_late_arrivals(
        annotated,
        watermark_date,
        previous_cutoff,
        current_cutoff,
    )
    late_detected = any(r[key_field] == late_id for r in late_rows)
    strict_missed_late = late_id not in {r[key_field] for r in incremental_selected}
    temp1_pass = late_detected and strict_missed_late
    experiments.append({
        "experiment_id": "TEMP-001",
        "failure_type": "late_arriving_data",
        "risk": "A pipeline can report SUCCESS while event-time filtering silently misses a record that arrives after the watermark.",
        "hypothesis": "A real performance row with synthetic late arrival metadata and event_date <= watermark will be missed by strict event-time incremental selection but detected by the late-arrival control.",
        "injection": f"performance_id={late_id}; event_date={late_source_row['event_date']}; synthetic_arrival_date={synthetic_late_arrival}",
        "detection": "LATE_ARRIVAL_BEHIND_WATERMARK",
        "actual_result": f"strict_incremental_selected={len(incremental_selected)}; late_detected={len(late_rows)}; target_missed={strict_missed_late}",
        "pass_fail": "PASS" if temp1_pass else "FAIL",
        "recovery": f"bounded backfill window {backfill_start}..{watermark_date}",
        "reconciliation": "late record must be present exactly once after backfill",
    })
    late_evidence.append({
        "experiment_id": "TEMP-001",
        "performance_id": late_id,
        "campaign_id": late_source_row.get("campaign_id", ""),
        "performance_scope": late_source_row.get("performance_scope", ""),
        "event_date": late_source_row["event_date"],
        "synthetic_arrival_date": synthetic_late_arrival,
        "watermark_date": watermark_date,
        "previous_arrival_cutoff": previous_cutoff,
        "current_arrival_cutoff": current_cutoff,
        "strict_incremental_selected": "no" if strict_missed_late else "yes",
        "late_arrival_detected": "yes" if late_detected else "no",
        "metadata_semantics": "controlled synthetic arrival date; source event record and lineage are real project history",
        "status": "PASS" if temp1_pass else "FAIL",
    })
    run_ledger.append({
        "run_id": "temporal_late_arrival_detection",
        "experiment_id": "TEMP-001",
        "status": "SUCCESS" if temp1_pass else "FAILED",
        "stage": "LATE_DATA_GATE",
        "watermark_date": watermark_date,
        "expected_rows": expected_rows,
        "loaded_rows": expected_rows - 1,
        "late_arrival_count": len(late_rows),
        "commit_status": "BLOCKED_PENDING_BACKFILL" if temp1_pass else "UNKNOWN",
        "failure_code": "LATE_ARRIVAL_BEHIND_WATERMARK" if temp1_pass else "LATE_ARRIVAL_NOT_DETECTED",
    })
    incidents.append({
        "incident_id": "INC-TEMP-001",
        "experiment_id": "TEMP-001",
        "symptom": "Strict event-time incremental selection omitted a source performance record even though the batch logic itself completed.",
        "trigger": "Controlled synthetic late arrival after the prior arrival cutoff.",
        "mechanism": "event_date <= watermark while arrival_date entered the system later.",
        "evidence": f"performance_id={late_id}; event_date={late_source_row['event_date']}; watermark={watermark_date}; synthetic_arrival={synthetic_late_arrival}",
        "verified_cause": "Strict event-time predicate alone has no late-arrival recovery path.",
        "fix": "Detect arrivals behind the watermark and open a bounded backfill window.",
        "recovery": "TEMP-004 safe backfill",
        "preventive_control": "Arrival-aware late-data gate + bounded lookback/backfill contract.",
        "status": "RECOVERED" if temp1_pass else "OPEN",
    })
    timeline.extend([
        {"incident_id": "INC-TEMP-001", "step_order": 1, "step": "INJECT", "detail": f"synthetic arrival {synthetic_late_arrival} for real performance_id={late_id}"},
        {"incident_id": "INC-TEMP-001", "step_order": 2, "step": "DETECT", "detail": f"late_rows={len(late_rows)}; target_detected={late_detected}"},
        {"incident_id": "INC-TEMP-001", "step_order": 3, "step": "CONTAIN", "detail": "do not advance trusted completeness state until backfill reconciliation"},
        {"incident_id": "INC-TEMP-001", "step_order": 4, "step": "RECOVER", "detail": f"backfill window={backfill_start}..{watermark_date}"},
    ])

    # TEMP-002: future/ahead watermark.
    ahead_watermark = (max_event + timedelta(days=15)).isoformat()
    ahead_result = validate_watermark(
        ahead_watermark,
        max_event.isoformat(),
        max_staleness_days=int(config["watermark"]["max_staleness_days"]),
    )
    temp2_pass = ahead_result.status == "FAIL" and ahead_result.code == "WATERMARK_AHEAD_OF_SOURCE"
    experiments.append({
        "experiment_id": "TEMP-002",
        "failure_type": "watermark_ahead_of_source",
        "risk": "A future watermark can permanently skip valid records whose event dates fall behind the corrupted pointer.",
        "hypothesis": "A watermark beyond the maximum observed governed event date must block the run.",
        "injection": f"watermark={ahead_watermark}; max_observed_event_date={max_event.isoformat()}",
        "detection": ahead_result.code,
        "actual_result": ahead_result.evidence,
        "pass_fail": "PASS" if temp2_pass else "FAIL",
        "recovery": f"restore watermark to governed last successful event date <= {max_event.isoformat()}",
        "reconciliation": "watermark must revalidate before incremental processing resumes",
    })
    watermark_evidence.append({"experiment_id": "TEMP-002", **ahead_result.__dict__})
    run_ledger.append({
        "run_id": "temporal_bad_watermark_ahead",
        "experiment_id": "TEMP-002",
        "status": "FAILED" if temp2_pass else "SUCCESS",
        "stage": "WATERMARK_GATE",
        "watermark_date": ahead_watermark,
        "expected_rows": expected_rows,
        "loaded_rows": 0,
        "late_arrival_count": 0,
        "commit_status": "NOT_STARTED",
        "failure_code": ahead_result.code,
    })

    # TEMP-003: stale watermark.
    stale_watermark = (max_event - timedelta(days=30)).isoformat()
    stale_result = validate_watermark(
        stale_watermark,
        max_event.isoformat(),
        max_staleness_days=int(config["watermark"]["max_staleness_days"]),
    )
    temp3_pass = stale_result.status == "FAIL" and stale_result.code == "WATERMARK_STALE"
    experiments.append({
        "experiment_id": "TEMP-003",
        "failure_type": "stale_watermark",
        "risk": "A stale checkpoint creates backlog and freshness/completeness degradation even when the pipeline keeps running.",
        "hypothesis": "A watermark lagging the source maximum beyond the governed threshold must fail validation and trigger recovery/backfill planning.",
        "injection": f"watermark={stale_watermark}; max_observed_event_date={max_event.isoformat()}",
        "detection": stale_result.code,
        "actual_result": stale_result.evidence,
        "pass_fail": "PASS" if temp3_pass else "FAIL",
        "recovery": "run bounded catch-up/backfill, reconcile row completeness, then advance state",
        "reconciliation": "stale lag must return within threshold after recovery",
    })
    watermark_evidence.append({"experiment_id": "TEMP-003", **stale_result.__dict__})
    run_ledger.append({
        "run_id": "temporal_stale_watermark",
        "experiment_id": "TEMP-003",
        "status": "FAILED" if temp3_pass else "SUCCESS",
        "stage": "WATERMARK_GATE",
        "watermark_date": stale_watermark,
        "expected_rows": expected_rows,
        "loaded_rows": 0,
        "late_arrival_count": 0,
        "commit_status": "NOT_STARTED",
        "failure_code": stale_result.code,
    })

    # TEMP-004: safe bounded backfill + idempotent rerun.
    baseline_existing = [r for r in temporal_rows if r[key_field] != late_id]
    existing_keys = {r[key_field] for r in baseline_existing}
    backfill = safe_backfill(
        temporal_rows,
        start_date=backfill_start,
        end_date=watermark_date,
        existing_keys=existing_keys,
        key_field=key_field,
    )
    merged, inserted, updated = apply_upsert(baseline_existing, backfill["new_rows"], key_field=key_field)
    rerun, inserted_again, updated_again = apply_upsert(merged, backfill["new_rows"], key_field=key_field)
    unique_after = len({r[key_field] for r in rerun})
    late_count_after = sum(1 for r in rerun if r[key_field] == late_id)
    temp4_pass = (
        backfill["new_row_count"] == 1
        and inserted == 1
        and inserted_again == 0
        and updated_again == 0
        and unique_after == expected_rows
        and late_count_after == 1
    )
    experiments.append({
        "experiment_id": "TEMP-004",
        "failure_type": "safe_backfill_and_idempotency",
        "risk": "A recovery backfill can create duplicates or collide with already-loaded history.",
        "hypothesis": "A bounded business-key upsert recovers the missed late row exactly once and a repeated backfill inserts zero new rows.",
        "injection": f"existing dataset intentionally omits performance_id={late_id}",
        "detection": "BACKFILL_RECONCILIATION",
        "actual_result": f"new_rows={backfill['new_row_count']}; inserted={inserted}; rerun_inserted={inserted_again}; unique_after={unique_after}",
        "pass_fail": "PASS" if temp4_pass else "FAIL",
        "recovery": "bounded event-date backfill + business-key upsert",
        "reconciliation": f"late_id_count={late_count_after}; unique_rows={unique_after}/{expected_rows}",
    })
    backfill_evidence.extend([
        {
            "experiment_id": "TEMP-004",
            "phase": "FIRST_BACKFILL",
            "start_date": backfill["start_date"],
            "end_date": backfill["end_date"],
            "source_window_rows": backfill["source_window_rows"],
            "unique_source_keys": backfill["unique_source_keys"],
            "skipped_existing_keys": backfill["skipped_existing_keys"],
            "new_row_count": backfill["new_row_count"],
            "inserted_rows": inserted,
            "updated_rows": updated,
            "total_unique_rows_after": len({r[key_field] for r in merged}),
            "backfill_fingerprint": backfill["backfill_fingerprint"],
            "status": "PASS" if inserted == 1 else "FAIL",
        },
        {
            "experiment_id": "TEMP-004",
            "phase": "IDEMPOTENT_RERUN",
            "start_date": backfill["start_date"],
            "end_date": backfill["end_date"],
            "source_window_rows": backfill["source_window_rows"],
            "unique_source_keys": backfill["unique_source_keys"],
            "skipped_existing_keys": backfill["skipped_existing_keys"],
            "new_row_count": backfill["new_row_count"],
            "inserted_rows": inserted_again,
            "updated_rows": updated_again,
            "total_unique_rows_after": unique_after,
            "backfill_fingerprint": backfill["backfill_fingerprint"],
            "status": "PASS" if inserted_again == 0 and unique_after == expected_rows else "FAIL",
        },
    ])
    run_ledger.append({
        "run_id": "temporal_safe_backfill",
        "experiment_id": "TEMP-004",
        "status": "SUCCESS" if temp4_pass else "FAILED",
        "stage": "BACKFILL_COMMIT",
        "watermark_date": watermark_date,
        "expected_rows": expected_rows,
        "loaded_rows": unique_after,
        "late_arrival_count": len(late_rows),
        "commit_status": "COMMITTED_IDEMPOTENT",
        "failure_code": "",
    })
    timeline.extend([
        {"incident_id": "INC-TEMP-001", "step_order": 5, "step": "BACKFILL", "detail": f"new_rows={backfill['new_row_count']}; inserted={inserted}"},
        {"incident_id": "INC-TEMP-001", "step_order": 6, "step": "RERUN", "detail": f"same backfill inserted_again={inserted_again}"},
        {"incident_id": "INC-TEMP-001", "step_order": 7, "step": "RECONCILE", "detail": f"unique_rows={unique_after}/{expected_rows}; late_record_count={late_count_after}"},
    ])

    # TEMP-005: freshness/completeness SLO breach + escalation + clean recovery.
    as_of_date = (max_event + timedelta(days=1)).isoformat()
    degraded_run = {
        "run_id": "temporal_slo_breach",
        "as_of_date": as_of_date,
        "latest_loaded_event_date": (max_event - timedelta(days=5)).isoformat(),
        "watermark_date": (max_event - timedelta(days=7)).isoformat(),
        "expected_rows": expected_rows,
        "loaded_rows": expected_rows - 10,
    }
    slo_events = evaluate_temporal_slo(degraded_run, config["slo"])
    slo_alerts = alerts_with_escalation(slo_events, config["alert_escalation"])
    recovery_run = {
        "run_id": "temporal_slo_recovery",
        "as_of_date": as_of_date,
        "latest_loaded_event_date": max_event.isoformat(),
        "watermark_date": max_event.isoformat(),
        "expected_rows": expected_rows,
        "loaded_rows": expected_rows,
    }
    recovery_events = evaluate_temporal_slo(recovery_run, config["slo"])
    temp5_pass = len(slo_events) >= 3 and any(e.severity == "CRITICAL" for e in slo_events) and len(recovery_events) == 0
    experiments.append({
        "experiment_id": "TEMP-005",
        "failure_type": "freshness_completeness_slo_and_alert_escalation",
        "risk": "A run may be technically successful but serve stale or incomplete history without an operational SLO signal.",
        "hypothesis": "Degraded freshness/completeness/watermark metrics must emit SLO events and simulated escalation; a reconciled recovery run must emit no SLO breach.",
        "injection": f"latest_event={degraded_run['latest_loaded_event_date']}; loaded_rows={degraded_run['loaded_rows']}/{expected_rows}; watermark={degraded_run['watermark_date']}",
        "detection": ";".join(e.code for e in slo_events),
        "actual_result": f"events={len(slo_events)}; alerts={len(slo_alerts)}; recovery_events={len(recovery_events)}",
        "pass_fail": "PASS" if temp5_pass else "FAIL",
        "recovery": "complete backfill/replay, advance watermark only after reconciliation, reevaluate SLO",
        "reconciliation": f"recovery_loaded={expected_rows}/{expected_rows}; recovery_events={len(recovery_events)}",
    })
    run_ledger.extend([
        {
            "run_id": degraded_run["run_id"],
            "experiment_id": "TEMP-005",
            "status": "SUCCESS_WITH_DATA_SLO_BREACH",
            "stage": "SERVE_MONITOR",
            "watermark_date": degraded_run["watermark_date"],
            "expected_rows": expected_rows,
            "loaded_rows": degraded_run["loaded_rows"],
            "late_arrival_count": 0,
            "commit_status": "COMMITTED_BUT_NOT_TRUSTED",
            "failure_code": ";".join(e.code for e in slo_events),
        },
        {
            "run_id": recovery_run["run_id"],
            "experiment_id": "TEMP-005",
            "status": "SUCCESS",
            "stage": "SERVE_MONITOR",
            "watermark_date": recovery_run["watermark_date"],
            "expected_rows": expected_rows,
            "loaded_rows": expected_rows,
            "late_arrival_count": 0,
            "commit_status": "COMMITTED_TRUSTED",
            "failure_code": "",
        },
    ])
    incidents.append({
        "incident_id": "INC-TEMP-005",
        "experiment_id": "TEMP-005",
        "symptom": "Pipeline status is successful but served data breaches freshness/completeness SLOs.",
        "trigger": "Controlled degraded temporal run metrics.",
        "mechanism": "Latest event and watermark lag behind the controlled as-of date while 10 expected rows are missing.",
        "evidence": ";".join(e.code for e in slo_events),
        "verified_cause": "Operational success status alone does not represent data freshness/completeness correctness.",
        "fix": "Data SLO gate + alert escalation + recovery replay/backfill.",
        "recovery": f"latest_event={max_event.isoformat()}; loaded_rows={expected_rows}/{expected_rows}; recovery_events=0",
        "preventive_control": "Freshness/completeness/watermark SLO monitoring with simulated escalation evidence.",
        "status": "RECOVERED" if temp5_pass else "OPEN",
    })
    timeline.extend([
        {"incident_id": "INC-TEMP-005", "step_order": 1, "step": "INJECT", "detail": "degraded freshness, completeness and watermark lag metrics"},
        {"incident_id": "INC-TEMP-005", "step_order": 2, "step": "DETECT", "detail": ";".join(e.code for e in slo_events)},
        {"incident_id": "INC-TEMP-005", "step_order": 3, "step": "ALERT", "detail": f"primary/escalated alert evidence rows={len(slo_alerts)}"},
        {"incident_id": "INC-TEMP-005", "step_order": 4, "step": "RECOVER", "detail": f"recovery rows={expected_rows}/{expected_rows}; watermark={max_event.isoformat()}"},
        {"incident_id": "INC-TEMP-005", "step_order": 5, "step": "RECONCILE", "detail": f"recovery SLO events={len(recovery_events)}"},
    ])

    # SLO run-level dashboard rows. SLA intentionally remains undefined.
    slo_runs: list[dict] = []
    for run in [degraded_run, recovery_run]:
        events = slo_events if run["run_id"] == degraded_run["run_id"] else recovery_events
        freshness = (parse_iso_date(run["as_of_date"]) - parse_iso_date(run["latest_loaded_event_date"])).days
        completeness = run["loaded_rows"] / run["expected_rows"]
        watermark_lag = (parse_iso_date(run["as_of_date"]) - parse_iso_date(run["watermark_date"])).days
        slo_runs.append({
            "run_id": run["run_id"],
            "as_of_date": run["as_of_date"],
            "latest_loaded_event_date": run["latest_loaded_event_date"],
            "watermark_date": run["watermark_date"],
            "expected_rows": run["expected_rows"],
            "loaded_rows": run["loaded_rows"],
            "freshness_lag_days": freshness,
            "completeness_ratio": round(completeness, 6),
            "watermark_lag_days": watermark_lag,
            "slo_event_count": len(events),
            "slo_status": "PASS" if not events else "BREACH",
        })

    slo_contract = [
        {"service_level_type": "SLA", "metric": "external_business_commitment", "target": "", "status": "NOT_DEFINED", "meaning": "No approved external/business SLA exists in project source; do not invent one."},
        {"service_level_type": "SLO", "metric": "freshness_lag_days", "target": f"<= {config['slo']['max_freshness_lag_days']}", "status": "IMPLEMENTED", "meaning": "Latest loaded governed event should stay within the internal freshness objective."},
        {"service_level_type": "SLO", "metric": "completeness_ratio", "target": f">= {config['slo']['min_completeness_ratio']}", "status": "IMPLEMENTED", "meaning": "Loaded temporal rows / expected governed rows."},
        {"service_level_type": "SLO", "metric": "watermark_lag_days", "target": f"<= {config['slo']['max_watermark_lag_days']}", "status": "IMPLEMENTED", "meaning": "Governed watermark should not trail controlled as-of date beyond objective."},
    ]

    controls = [
        {"control_id": "TMP-C01", "control": "Arrival-aware late-data detector", "prevents_or_detects": "Event-time rows arriving behind watermark", "stage": "INCREMENTAL", "status": "IMPLEMENTED"},
        {"control_id": "TMP-C02", "control": "Watermark ahead/staleness validation", "prevents_or_detects": "Corrupt/future/stale checkpoint", "stage": "PRE_RUN", "status": "IMPLEMENTED"},
        {"control_id": "TMP-C03", "control": "Bounded backfill window", "prevents_or_detects": "Uncontrolled full-history replay", "stage": "RECOVERY", "status": "IMPLEMENTED"},
        {"control_id": "TMP-C04", "control": "Business-key upsert + idempotent backfill", "prevents_or_detects": "Duplicate replay/backfill collision", "stage": "BACKFILL_COMMIT", "status": "IMPLEMENTED"},
        {"control_id": "TMP-C05", "control": "Freshness/completeness/watermark SLO", "prevents_or_detects": "SUCCESS status with stale/incomplete data", "stage": "SERVE_MONITOR", "status": "IMPLEMENTED"},
        {"control_id": "TMP-C06", "control": "Severity-based alert escalation evidence", "prevents_or_detects": "Unacknowledged critical data SLO breach", "stage": "ALERT", "status": "SIMULATED"},
    ]

    source_integrity: list[dict] = []
    for filename, before_hash in sorted(source_hashes_before.items()):
        after_hash = sha256_file(source_dir / filename)
        source_integrity.append({
            "source_filename": filename,
            "before_sha256": before_hash,
            "after_sha256": after_hash,
            "hash_match": "yes" if before_hash == after_hash else "no",
            "status": "PASS" if before_hash == after_hash else "FAIL",
        })

    experiment_passes = sum(1 for row in experiments if row["pass_fail"] == "PASS")
    reconciliation = [
        {"metric": "controlled_experiments", "value": len(experiments), "status": "PASS"},
        {"metric": "experiments_passed", "value": experiment_passes, "status": "PASS" if experiment_passes == len(experiments) else "FAIL"},
        {"metric": "source_performance_rows", "value": len(raw_rows), "status": "PASS"},
        {"metric": "valid_temporal_event_rows", "value": expected_rows, "status": "PASS"},
        {"metric": "invalid_or_non_date_event_rows_excluded", "value": len(raw_rows) - len(temporal_rows), "status": "PASS"},
        {"metric": "late_arrivals_detected", "value": len(late_rows), "status": "PASS" if late_detected else "FAIL"},
        {"metric": "backfill_inserted_rows", "value": inserted, "status": "PASS" if inserted == 1 else "FAIL"},
        {"metric": "backfill_rerun_inserted_rows", "value": inserted_again, "status": "PASS" if inserted_again == 0 else "FAIL"},
        {"metric": "reconciled_unique_temporal_rows", "value": unique_after, "status": "PASS" if unique_after == expected_rows else "FAIL"},
        {"metric": "slo_breach_events", "value": len(slo_events), "status": "PASS" if len(slo_events) >= 3 else "FAIL"},
        {"metric": "alert_evidence_rows", "value": len(slo_alerts), "status": "PASS" if len(slo_alerts) >= len(slo_events) else "FAIL"},
        {"metric": "recovery_slo_events", "value": len(recovery_events), "status": "PASS" if len(recovery_events) == 0 else "FAIL"},
        {"metric": "source_hashes_unchanged", "value": sum(1 for r in source_integrity if r["status"] == "PASS"), "status": "PASS" if all(r["status"] == "PASS" for r in source_integrity) else "FAIL"},
    ]

    write_csv(output_dir / "reliability_temporal_experiments_v3.csv", experiments)
    write_csv(output_dir / "reliability_temporal_incidents_v3.csv", incidents)
    write_csv(output_dir / "reliability_temporal_incident_timeline_v3.csv", timeline)
    write_csv(output_dir / "reliability_temporal_run_ledger_v3.csv", run_ledger)
    write_csv(output_dir / "reliability_late_arrival_evidence_v3.csv", late_evidence)
    write_csv(output_dir / "reliability_watermark_validation_v3.csv", watermark_evidence)
    write_csv(output_dir / "reliability_backfill_evidence_v3.csv", backfill_evidence)
    write_csv(output_dir / "reliability_temporal_slo_runs_v3.csv", slo_runs)
    write_csv(output_dir / "reliability_temporal_monitoring_events_v3.csv", dataclass_rows(slo_events))
    write_csv(output_dir / "reliability_temporal_alert_escalation_v3.csv", slo_alerts)
    write_csv(output_dir / "reliability_sla_slo_contract_v3.csv", slo_contract)
    write_csv(output_dir / "reliability_temporal_prevention_controls_v3.csv", controls)
    write_csv(output_dir / "reliability_temporal_reconciliation_v3.csv", reconciliation)
    write_csv(output_dir / "reliability_temporal_source_integrity_v3.csv", source_integrity)

    summary = {
        "lab_version": "temporal-reliability-v3",
        "source_workbook_count": len(source_files),
        "source_performance_rows": len(raw_rows),
        "valid_temporal_event_rows": expected_rows,
        "event_date_min": min_event.isoformat(),
        "event_date_max": max_event.isoformat(),
        "controlled_experiments": len(experiments),
        "experiments_passed": experiment_passes,
        "late_arrival_count": len(late_rows),
        "backfill_inserted_rows": inserted,
        "backfill_rerun_inserted_rows": inserted_again,
        "slo_breach_events": len(slo_events),
        "alert_evidence_rows": len(slo_alerts),
        "recovery_slo_events": len(recovery_events),
        "sla_status": "NOT_DEFINED",
        "status": "PASS" if experiment_passes == len(experiments) and all(r["status"] == "PASS" for r in reconciliation) else "FAIL",
        "guardrail": "arrival timestamps are controlled synthetic metadata; event records/lineage are source-derived",
    }
    write_json(output_dir / "reliability_temporal_run_summary_v3.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--performance-csv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    summary = run_lab(args.source_dir, args.performance_csv, args.output_dir, args.config)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
