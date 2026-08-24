from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from src.candidate_adapter import adapt_candidate_sheet, load_contract
from src.sheet_classifier import classify_sheet, load_rules
from src.xlsx_probe import iter_xlsx, probe_workbook, read_sheet_rows


def write_csv(rows: list[dict[str, object]], output_path: Path, fieldnames: list[str]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as file_obj:
        writer = csv.DictWriter(file_obj, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract PII-safe candidate observations and enforce a DQ promotion gate."
    )
    parser.add_argument("--input-dir", required=True, type=Path)
    parser.add_argument("--rules", required=True, type=Path)
    parser.add_argument("--overrides", type=Path, default=None)
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--accepted-output", required=True, type=Path)
    parser.add_argument("--quarantine-output", required=True, type=Path)
    args = parser.parse_args()

    rules = load_rules(args.rules, args.overrides)
    contract = load_contract(args.contract)
    all_rows: list[dict[str, object]] = []
    candidate_sheet_count = 0

    for workbook_path in iter_xlsx(args.input_dir):
        for probe in probe_workbook(workbook_path, max_rows=20, max_cols=25):
            classification = classify_sheet(
                probe.sheet_name,
                probe.preview_rows,
                rules,
                source_filename=workbook_path.name,
            )
            if classification.sheet_type != "influencer_candidate":
                continue
            candidate_sheet_count += 1
            sheet_rows = read_sheet_rows(workbook_path, probe.sheet_name, max_cols=40)
            all_rows.extend(
                adapt_candidate_sheet(
                    workbook_path.name,
                    probe.sheet_name,
                    sheet_rows,
                    rules,
                    contract,
                )
            )

    if not all_rows:
        raise SystemExit("ERROR: no candidate observations extracted")

    accepted_rows = [row for row in all_rows if row["dq_status"] != "ERROR"]
    quarantined_rows = [row for row in all_rows if row["dq_status"] == "ERROR"]
    fieldnames = list(all_rows[0].keys())
    write_csv(accepted_rows, args.accepted_output, fieldnames)
    write_csv(quarantined_rows, args.quarantine_output, fieldnames)

    dq_counts = Counter(str(row["dq_status"]) for row in all_rows)
    dq_code_counts = Counter(
        code
        for row in all_rows
        for code in str(row["dq_codes"]).split(";")
        if code
    )
    gate_status = "FAIL" if quarantined_rows else ("WARN" if dq_counts.get("WARN", 0) else "PASS")
    summary = {
        "execution_status": "PASS",
        "data_quality_gate_status": gate_status,
        "candidate_sheets_processed": candidate_sheet_count,
        "candidate_observations": len(all_rows),
        "accepted_rows": len(accepted_rows),
        "quarantined_rows": len(quarantined_rows),
        "dq_status_counts": dict(sorted(dq_counts.items())),
        "dq_code_counts": dict(sorted(dq_code_counts.items())),
        "rows_with_pii_in_source": sum(bool(row["pii_present"]) for row in all_rows),
        "rows_with_identity_conflict": dq_code_counts.get("DQ_IDENTITY_CONFLICT", 0),
        "rows_with_unparsable_identity": dq_code_counts.get("DQ_IDENTITY_UNPARSABLE", 0),
        "accepted_output": str(args.accepted_output),
        "quarantine_output": str(args.quarantine_output),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 2 if gate_status == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
