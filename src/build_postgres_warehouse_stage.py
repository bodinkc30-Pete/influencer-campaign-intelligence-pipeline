from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from .warehouse_contract import (
        TABLE_CONTRACTS,
        add_parsed_date,
        blank_primary_keys,
        duplicate_primary_keys,
        foreign_key_violations,
        read_csv,
        simulate_idempotent_upsert,
        table_fingerprint,
        validate_required_columns,
        write_csv,
    )
except ImportError:
    from warehouse_contract import (
        TABLE_CONTRACTS,
        add_parsed_date,
        blank_primary_keys,
        duplicate_primary_keys,
        foreign_key_violations,
        read_csv,
        simulate_idempotent_upsert,
        table_fingerprint,
        validate_required_columns,
        write_csv,
    )


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build PostgreSQL load-ready staging CSVs from governed canonical CSVs.")
    p.add_argument("--influencer-master", type=Path, required=True)
    p.add_argument("--identity-alias", type=Path, required=True)
    p.add_argument("--brand-registry", type=Path, required=True)
    p.add_argument("--campaign-registry", type=Path, required=True)
    p.add_argument("--campaign-requirement", type=Path, required=True)
    p.add_argument("--campaign-influencer", type=Path, required=True)
    p.add_argument("--campaign-deliverable", type=Path, required=True)
    p.add_argument("--influencer-performance", type=Path, required=True)
    p.add_argument("--campaign-performance", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    return p.parse_args()


def build_tables(args: argparse.Namespace) -> dict[str, list[dict[str, str]]]:
    tables = {
        "dim_influencer": read_csv(args.influencer_master),
        "influencer_identity_alias": read_csv(args.identity_alias),
        "dim_brand": read_csv(args.brand_registry),
        "dim_campaign": read_csv(args.campaign_registry),
        "campaign_requirement": read_csv(args.campaign_requirement),
        "fact_campaign_influencer": read_csv(args.campaign_influencer),
        "fact_campaign_deliverable": read_csv(args.campaign_deliverable),
        "fact_influencer_performance": read_csv(args.influencer_performance),
        "fact_campaign_performance": read_csv(args.campaign_performance),
    }

    tables["fact_campaign_deliverable"] = [
        add_parsed_date(add_parsed_date(row, "scheduled_date", "scheduled_date"), "posted_date", "posted_date")
        for row in tables["fact_campaign_deliverable"]
    ]
    tables["fact_influencer_performance"] = [
        add_parsed_date(row, "measurement_date", "measurement_date")
        for row in tables["fact_influencer_performance"]
    ]
    tables["fact_campaign_performance"] = [
        add_parsed_date(row, "event_date", "event_date")
        for row in tables["fact_campaign_performance"]
    ]
    return tables


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    tables = build_tables(args)

    problems: list[str] = []
    checks: list[dict[str, object]] = []
    for name, rows in tables.items():
        missing = validate_required_columns(name, rows)
        dup = duplicate_primary_keys(name, rows)
        blank = blank_primary_keys(name, rows)
        problems.extend(missing)
        if dup:
            problems.append(f"{name}:DUPLICATE_PRIMARY_KEY:{len(dup)}")
        if blank:
            problems.append(f"{name}:BLANK_PRIMARY_KEY:{len(blank)}")
        first, second, changed = simulate_idempotent_upsert(rows, TABLE_CONTRACTS[name].primary_key)
        checks.append({
            "table_name": name,
            "source_rows": len(rows),
            "unique_primary_keys": first,
            "rerun_rows": second,
            "rerun_changed_rows": changed,
            "fingerprint": table_fingerprint(rows, TABLE_CONTRACTS[name].primary_key),
            "status": "PASS" if not missing and not dup and not blank and first == second and changed == 0 else "FAIL",
        })

    fk = foreign_key_violations(tables)
    if fk:
        problems.append(f"FOREIGN_KEY_VIOLATIONS:{len(fk)}")

    for name, rows in tables.items():
        write_csv(args.output_dir / f"{name}.csv", rows)
    write_csv(args.output_dir / "warehouse_preflight_checks.csv", checks)
    write_csv(args.output_dir / "warehouse_fk_violations.csv", fk, fieldnames=[
        "child_table", "child_columns", "child_key", "parent_table", "parent_columns"
    ])
    (args.output_dir / "warehouse_preflight_summary.json").write_text(
        json.dumps({
            "status": "PASS" if not problems else "FAIL",
            "table_count": len(tables),
            "foreign_key_violation_count": len(fk),
            "problem_count": len(problems),
            "problems": problems,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    if problems:
        print(json.dumps({"status": "FAIL", "problems": problems}, ensure_ascii=False))
        return 2
    print(json.dumps({"status": "PASS", "tables": {k: len(v) for k, v in tables.items()}}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
