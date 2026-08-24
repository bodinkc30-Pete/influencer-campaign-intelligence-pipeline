from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from src.sheet_classifier import classify_sheet, load_rules
from src.xlsx_probe import iter_xlsx, probe_workbook


def build_inventory(input_dir: Path, rules_path: Path, overrides_path: Path | None = None) -> list[dict[str, object]]:
    rules = load_rules(rules_path, overrides_path)
    rows: list[dict[str, object]] = []
    for workbook_path in iter_xlsx(input_dir):
        for sheet in probe_workbook(
            workbook_path,
            max_rows=int(rules["candidate_header"]["scan_rows"]),
            max_cols=25,
        ):
            result = classify_sheet(
                sheet.sheet_name, sheet.preview_rows, rules, source_filename=workbook_path.name
            )
            rows.append(
                {
                    "source_filename": workbook_path.name,
                    "sheet_name": sheet.sheet_name,
                    "dimension": sheet.dimension or "",
                    "sheet_type": result.sheet_type,
                    "classification_confidence": result.confidence,
                    "classification_basis": result.basis,
                    "primary_header_row": result.primary_header_row or "",
                    "detected_header_rows": ",".join(str(x) for x in result.detected_header_rows),
                    "header_signature": ",".join(result.header_signature),
                }
            )
    return rows


def write_csv(rows: list[dict[str, object]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as file_obj:
        writer = csv.DictWriter(file_obj, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Inventory and classify workbook sheets without loading business rows.")
    parser.add_argument("--input-dir", required=True, type=Path)
    parser.add_argument("--rules", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--overrides", type=Path, default=None)
    parser.add_argument("--expected-sheets", type=int, default=None)
    parser.add_argument("--expected-candidate-sheets", type=int, default=None)
    args = parser.parse_args()

    rows = build_inventory(args.input_dir, args.rules, args.overrides)
    if not rows:
        raise SystemExit("ERROR: no sheets discovered")
    write_csv(rows, args.output)

    counts = Counter(row["sheet_type"] for row in rows)
    status = "PASS"
    failures: list[str] = []
    if args.expected_sheets is not None and len(rows) != args.expected_sheets:
        status = "FAIL"
        failures.append(f"expected {args.expected_sheets} sheets, discovered {len(rows)}")
    candidate_count = counts.get("influencer_candidate", 0)
    if args.expected_candidate_sheets is not None and candidate_count != args.expected_candidate_sheets:
        status = "FAIL"
        failures.append(
            f"expected {args.expected_candidate_sheets} influencer_candidate sheets, discovered {candidate_count}"
        )

    summary = {
        "status": status,
        "workbooks_discovered": len({row["source_filename"] for row in rows}),
        "sheets_discovered": len(rows),
        "classification_counts": dict(sorted(counts.items())),
        "candidate_sheets": candidate_count,
        "output": str(args.output),
        "failures": failures,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
