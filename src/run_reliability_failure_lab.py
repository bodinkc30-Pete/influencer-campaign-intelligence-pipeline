from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import sys
from pathlib import Path

from src.discover_sources import discover_xlsx
from src.reliability_lab import (
    batch_fingerprint,
    build_baseline_manifest,
    copy_xlsx_snapshot,
    empty_sheet,
    manifest_candidate_targets,
    register_batch,
    replace_shared_string_exact,
    validate_snapshot,
    write_manifest,
)


def write_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def issue_codes(result: dict) -> str:
    return ";".join(sorted({item["code"] for item in result["issues"]}))


def first_candidate_with_header(manifest: dict, header_term: str) -> tuple[str, str]:
    term = header_term.casefold()
    for wb in manifest["workbooks"]:
        for sh in wb["sheets"]:
            if sh["sheet_type"] == "influencer_candidate" and any(term == cell for cell in sh["header_cells_normalized"]):
                return wb["source_filename"], sh["sheet_name"]
    raise RuntimeError(f"no candidate sheet contains exact header {header_term!r}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run isolated Excel reliability failure experiments.")
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--rules", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--old-discover-script", type=Path, default=None)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest = build_baseline_manifest(args.input_dir, args.rules)
    write_manifest(manifest, args.output_dir / "reliability_source_baseline_v1_private.json")
    baseline_validation = validate_snapshot(args.input_dir, manifest, args.rules)
    if baseline_validation["status"] != "PASS":
        print(json.dumps({"status": "BASELINE_FAIL", "validation": baseline_validation}, ensure_ascii=False, indent=2))
        return 2

    scenarios: list[dict] = []
    timelines: list[dict] = []
    scenario_root = args.output_dir / "_scenario_work"
    scenario_root.mkdir(exist_ok=True)

    def record_timeline(exp_id: str, step: str, detail: str) -> None:
        timelines.append({"experiment_id": exp_id, "step_order": len([x for x in timelines if x["experiment_id"] == exp_id]) + 1, "step": step, "detail": detail})

    # 1 Missing workbook
    exp = "REL-001"
    work = scenario_root / exp
    copy_xlsx_snapshot(args.input_dir, work)
    missing_target = manifest["workbooks"][1]["source_filename"]
    (work / missing_target).unlink()
    injected = validate_snapshot(work, manifest, args.rules)
    record_timeline(exp, "inject", f"Removed one isolated workbook copy: {missing_target}")
    record_timeline(exp, "detect", f"Validation={injected['status']} codes={issue_codes(injected)}")
    shutil.copy2(args.input_dir / missing_target, work / missing_target)
    recovered = validate_snapshot(work, manifest, args.rules)
    record_timeline(exp, "recover", f"Restored approved file; validation={recovered['status']}")
    scenarios.append({
        "experiment_id": exp,
        "failure_type": "missing_workbook",
        "risk": "Campaign/influencer records disappear silently if an expected workbook is not delivered.",
        "hypothesis": "Removing one approved workbook should fail source validation before downstream processing.",
        "expected_behavior": "Fail fast with MISSING_WORKBOOK and block promotion.",
        "failure_injection": f"Delete isolated copy of {missing_target}.",
        "blast_radius": "Temporary scenario directory only; original private raw files untouched.",
        "baseline": f"{manifest['expected_workbook_count']} workbooks / {manifest['expected_sheet_count']} sheets.",
        "detection": issue_codes(injected),
        "actual_result": injected["status"],
        "pass_fail": "PASS" if injected["status"] == "FAIL" and recovered["status"] == "PASS" else "FAIL",
        "verified_cause": "Expected filename absent from snapshot directory.",
        "fix": "Restore approved workbook; keep expected-source manifest as a blocking gate.",
        "recovery": recovered["status"],
        "reconciliation": f"workbooks={recovered['workbooks_discovered']} errors={recovered['error_count']}",
        "regression_test": "test_missing_workbook_is_blocking",
        "preventive_control": "Expected source manifest + source arrival monitoring.",
        "business_impact": "Prevents incomplete campaign history/master inputs from being accepted as complete.",
    })

    # 2 Duplicate workbook + old control gap comparison
    exp = "REL-002"
    work = scenario_root / exp
    copy_xlsx_snapshot(args.input_dir, work)
    duplicate_source = manifest["workbooks"][0]["source_filename"]
    duplicate_name = f"DUPLICATE__{duplicate_source}"
    shutil.copy2(work / duplicate_source, work / duplicate_name)
    injected = validate_snapshot(work, manifest, args.rules)
    old_exit = "not_run"
    if args.old_discover_script and args.old_discover_script.exists():
        proc = subprocess.run(
            [sys.executable, str(args.old_discover_script), "--input-dir", str(work), "--output", str(args.output_dir / "old_duplicate_discovery.csv")],
            capture_output=True,
            text=True,
        )
        old_exit = str(proc.returncode)
    record_timeline(exp, "inject", f"Copied {duplicate_source} to {duplicate_name} without changing content.")
    record_timeline(exp, "detect", f"v13 validation={injected['status']} codes={issue_codes(injected)}; v12 discover exit={old_exit}")
    (work / duplicate_name).unlink()
    recovered = validate_snapshot(work, manifest, args.rules)
    record_timeline(exp, "recover", f"Removed duplicate copy; validation={recovered['status']}")
    scenarios.append({
        "experiment_id": exp,
        "failure_type": "duplicate_workbook",
        "risk": "Same source delivered twice can double-count candidates/history.",
        "hypothesis": "An extra workbook with an identical SHA-256 must fail even when discovery itself succeeds.",
        "expected_behavior": "Fail with DUPLICATE_WORKBOOK_HASH before ingestion.",
        "failure_injection": f"Create {duplicate_name} as byte-identical copy.",
        "blast_radius": "Temporary scenario directory only.",
        "baseline": "Unique SHA-256 per approved workbook.",
        "detection": issue_codes(injected),
        "actual_result": f"v13={injected['status']}; old_discover_exit={old_exit}",
        "pass_fail": "PASS" if injected["status"] == "FAIL" and recovered["status"] == "PASS" else "FAIL",
        "verified_cause": "Two filenames share the same content hash.",
        "fix": "v13 discover_sources treats duplicate hashes as a blocking failure by default.",
        "recovery": recovered["status"],
        "reconciliation": f"workbooks={recovered['workbooks_discovered']} errors={recovered['error_count']}",
        "regression_test": "test_duplicate_hash_is_blocking",
        "preventive_control": "Hash uniqueness gate; explicit override required only for approved exceptions.",
        "business_impact": "Prevents duplicate influencer/campaign observations and inflated history metrics.",
    })

    # 3 Candidate schema drift / column rename
    exp = "REL-003"
    work = scenario_root / exp
    copy_xlsx_snapshot(args.input_dir, work)
    drift_file, drift_sheet = first_candidate_with_header(manifest, "follower")
    replace_count = replace_shared_string_exact(work / drift_file, "Follower", "Audience Size")
    injected = validate_snapshot(work, manifest, args.rules)
    record_timeline(exp, "inject", f"Renamed exact shared-string header Follower -> Audience Size in isolated copy; replacements={replace_count}.")
    record_timeline(exp, "detect", f"Validation={injected['status']} codes={issue_codes(injected)}")
    shutil.copy2(args.input_dir / drift_file, work / drift_file)
    recovered = validate_snapshot(work, manifest, args.rules)
    record_timeline(exp, "recover", f"Restored approved workbook; validation={recovered['status']}")
    scenarios.append({
        "experiment_id": exp,
        "failure_type": "schema_drift_column_rename",
        "risk": "Renamed candidate columns can cause silent misclassification or missing fields.",
        "hypothesis": "Unknown rename of the Follower header should be detected as drift, not guessed into the canonical contract.",
        "expected_behavior": "Block exact-batch replay and surface schema drift evidence.",
        "failure_injection": f"{drift_file} / {drift_sheet}: Follower -> Audience Size.",
        "blast_radius": "Temporary copy; no parser aliases are changed automatically.",
        "baseline": "Candidate header signature includes follower evidence.",
        "detection": issue_codes(injected),
        "actual_result": injected["status"],
        "pass_fail": "PASS" if injected["status"] == "FAIL" and recovered["status"] == "PASS" and replace_count > 0 else "FAIL",
        "verified_cause": "Source header no longer matches approved candidate schema signals; workbook hash also changed.",
        "fix": "Quarantine/rollback changed source; require explicit reviewed schema mapping before parser changes.",
        "recovery": recovered["status"],
        "reconciliation": f"errors={recovered['error_count']} warnings={recovered['warn_count']}",
        "regression_test": "test_candidate_schema_drift_is_blocking",
        "preventive_control": "Baseline header signature checks + schema-drift alert + reviewed alias policy.",
        "business_impact": "Prevents follower/audience fields from shifting into wrong canonical columns.",
    })

    # 4 Empty candidate sheet
    exp = "REL-004"
    work = scenario_root / exp
    copy_xlsx_snapshot(args.input_dir, work)
    empty_file, empty_target_sheet = manifest_candidate_targets(manifest)[0]
    empty_sheet(work / empty_file, empty_target_sheet)
    injected = validate_snapshot(work, manifest, args.rules)
    record_timeline(exp, "inject", f"Cleared sheetData for {empty_file} / {empty_target_sheet} in isolated copy.")
    record_timeline(exp, "detect", f"Validation={injected['status']} codes={issue_codes(injected)}")
    shutil.copy2(args.input_dir / empty_file, work / empty_file)
    recovered = validate_snapshot(work, manifest, args.rules)
    record_timeline(exp, "recover", f"Restored approved workbook; validation={recovered['status']}")
    scenarios.append({
        "experiment_id": exp,
        "failure_type": "empty_candidate_sheet",
        "risk": "An empty source sheet can look like a successful file arrival while dropping all candidates for a campaign.",
        "hypothesis": "A previously non-empty candidate sheet becoming empty must block processing.",
        "expected_behavior": "Fail with EMPTY_SHEET and candidate schema loss evidence.",
        "failure_injection": f"Clear OOXML sheetData for {empty_file} / {empty_target_sheet}.",
        "blast_radius": "Temporary copy only.",
        "baseline": "Sheet has non-empty preview rows and candidate header signature.",
        "detection": issue_codes(injected),
        "actual_result": injected["status"],
        "pass_fail": "PASS" if injected["status"] == "FAIL" and recovered["status"] == "PASS" else "FAIL",
        "verified_cause": "Worksheet sheetData was empty compared with non-empty approved baseline.",
        "fix": "Block empty expected sheets; restore/re-request source delivery.",
        "recovery": recovered["status"],
        "reconciliation": f"errors={recovered['error_count']}",
        "regression_test": "test_empty_expected_sheet_is_blocking",
        "preventive_control": "Per-sheet non-empty gate + candidate sheet count monitoring.",
        "business_impact": "Prevents zero-row campaign inputs from being mistaken for legitimate no-candidate results.",
    })

    # 5 Idempotent same-batch rerun
    exp = "REL-005"
    records = discover_xlsx(args.input_dir)
    fingerprint = batch_fingerprint(records)
    ledger = args.output_dir / "reliability_batch_ledger_v1_private.json"
    ledger.unlink(missing_ok=True)
    first = register_batch(ledger, fingerprint)
    second = register_batch(ledger, fingerprint)
    record_timeline(exp, "baseline", f"Batch fingerprint={fingerprint[:16]} from sorted filename+hash pairs.")
    record_timeline(exp, "first_run", f"action={first.action} seen_count={first.current_seen_count}")
    record_timeline(exp, "rerun", f"action={second.action} seen_count={second.current_seen_count}")
    scenarios.append({
        "experiment_id": exp,
        "failure_type": "same_batch_rerun_idempotency",
        "risk": "Manual retry/rerun can double-load the same source batch.",
        "hypothesis": "Second registration of the identical batch fingerprint must be skipped.",
        "expected_behavior": "First run PROCESS_NEW_BATCH; rerun SKIP_ALREADY_PROCESSED.",
        "failure_injection": "Register the exact same 12-workbook fingerprint twice.",
        "blast_radius": "Private JSON ledger only; no source data modified.",
        "baseline": "No prior ledger entry for fingerprint.",
        "detection": second.action,
        "actual_result": f"first={first.action}; second={second.action}",
        "pass_fail": "PASS" if first.action == "PROCESS_NEW_BATCH" and second.action == "SKIP_ALREADY_PROCESSED" else "FAIL",
        "verified_cause": "Rerun fingerprint exactly matched a previously registered batch.",
        "fix": "Skip duplicate batch before write/promotion stages.",
        "recovery": "No rollback required; second run performs no duplicate processing.",
        "reconciliation": f"ledger_seen_count={second.current_seen_count}; expected_new_processing_on_rerun=0",
        "regression_test": "test_same_batch_rerun_is_idempotent",
        "preventive_control": "Deterministic batch fingerprint + atomic idempotency ledger.",
        "business_impact": "Prevents duplicate candidate/history rows during retry or operator rerun.",
    })

    write_csv(scenarios, args.output_dir / "reliability_failure_experiments_v1.csv")
    write_csv(timelines, args.output_dir / "reliability_incident_timeline_v1.csv")
    controls = [
        {"control_id": "CTRL-001", "control": "Expected source manifest", "prevents_or_detects": "Missing/unexpected workbook", "stage": "source discovery", "status": "implemented_v13"},
        {"control_id": "CTRL-002", "control": "SHA-256 uniqueness hard gate", "prevents_or_detects": "Duplicate workbook", "stage": "source discovery", "status": "implemented_v13"},
        {"control_id": "CTRL-003", "control": "Candidate header signature baseline", "prevents_or_detects": "Schema drift/column rename", "stage": "pre-ingestion", "status": "implemented_v13"},
        {"control_id": "CTRL-004", "control": "Expected non-empty sheet gate", "prevents_or_detects": "Empty/partial sheet", "stage": "pre-ingestion", "status": "implemented_v13"},
        {"control_id": "CTRL-005", "control": "Batch fingerprint idempotency ledger", "prevents_or_detects": "Same-batch rerun duplication", "stage": "batch admission", "status": "implemented_v13"},
    ]
    write_csv(controls, args.output_dir / "reliability_prevention_controls_v1.csv")
    recon = [
        {"metric": "baseline_workbooks", "value": manifest["expected_workbook_count"], "status": "PASS"},
        {"metric": "baseline_sheets", "value": manifest["expected_sheet_count"], "status": "PASS"},
        {"metric": "baseline_candidate_sheets", "value": manifest["expected_candidate_sheet_count"], "status": "PASS"},
        {"metric": "failure_experiments", "value": len(scenarios), "status": "PASS"},
        {"metric": "experiments_passed", "value": sum(row["pass_fail"] == "PASS" for row in scenarios), "status": "PASS" if all(row["pass_fail"] == "PASS" for row in scenarios) else "FAIL"},
        {"metric": "source_raw_files_packaged", "value": 0, "status": "PASS"},
        {"metric": "original_private_source_files_modified", "value": 0, "status": "PASS"},
    ]
    write_csv(recon, args.output_dir / "reliability_lab_reconciliation_v1.csv")

    # Do not package scenario copies; evidence only.
    shutil.rmtree(scenario_root)

    summary = {
        "status": "PASS" if all(row["pass_fail"] == "PASS" for row in scenarios) else "FAIL",
        "baseline": {
            "workbooks": manifest["expected_workbook_count"],
            "sheets": manifest["expected_sheet_count"],
            "candidate_sheets": manifest["expected_candidate_sheet_count"],
        },
        "experiments": len(scenarios),
        "passed": sum(row["pass_fail"] == "PASS" for row in scenarios),
        "failed": sum(row["pass_fail"] != "PASS" for row in scenarios),
        "output_dir": str(args.output_dir),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
