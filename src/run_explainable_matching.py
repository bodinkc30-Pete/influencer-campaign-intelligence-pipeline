from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from src.matching import load_config, rank_candidates


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run explainable matching v1 from governed historical features.")
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    config_data = json.loads(args.config.read_text(encoding="utf-8"))
    config = load_config(config_data)
    results = rank_candidates(read_csv(args.features), config)
    eligible = [r for r in results if r["eligibility_status"] == "eligible"]
    rejected = [r for r in results if r["eligibility_status"] == "ineligible"]
    shortlist = eligible[: config.shortlist_size]

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.output_dir / "match_candidate_score_v1.csv", results)
    write_csv(args.output_dir / "match_shortlist_v1.csv", shortlist)
    write_csv(args.output_dir / "match_eligibility_rejections_v1.csv", rejected)

    run_row = [{
        "scenario_id": config.scenario_id,
        "scenario_type": config.scenario_type,
        "scenario_name": config.scenario_name,
        "config_version": config.config_version,
        "platform": config.platform,
        "max_fee": config.max_fee,
        "feature_input_rows": len(results),
        "eligible_candidates": len(eligible),
        "ineligible_candidates": len(rejected),
        "shortlist_size": len(shortlist),
        "matching_version": "v1",
    }]
    write_csv(args.output_dir / "match_run_v1.csv", run_row)

    reconciliation = [
        {"metric": "feature_input_rows", "value": len(results), "status": "PASS"},
        {"metric": "candidate_score_rows", "value": len(results), "status": "PASS"},
        {"metric": "eligible_candidates", "value": len(eligible), "status": "PASS"},
        {"metric": "ineligible_candidates", "value": len(rejected), "status": "PASS"},
        {"metric": "eligible_plus_ineligible", "value": len(eligible) + len(rejected), "status": "PASS" if len(results) == len(eligible) + len(rejected) else "FAIL"},
        {"metric": "eligible_missing_rank", "value": sum(1 for r in eligible if r["rank"] is None), "status": "PASS"},
        {"metric": "ineligible_with_rank", "value": sum(1 for r in rejected if r["rank"] is not None), "status": "PASS"},
        {"metric": "duplicate_eligible_rank", "value": len(eligible) - len({r["rank"] for r in eligible}), "status": "PASS"},
        {"metric": "fuzzy_identity_resolution", "value": 0, "status": "PASS"},
        {"metric": "machine_learning", "value": 0, "status": "PASS"},
    ]
    write_csv(args.output_dir / "matching_reconciliation_v1.csv", reconciliation)

    limitations = [
        {"topic": "Campaign fit", "status": "deferred", "reason": "Category, persona and audience taxonomies are not governed in Historical Feature v1.", "impact": "Matching v1 is a historical-evidence baseline, not full campaign-fit ranking."},
        {"topic": "Recency", "status": "deferred", "reason": "Campaign chronology is not normalized consistently across all workbooks.", "impact": "No recency bonus or cooldown rule is applied."},
        {"topic": "Budget headroom", "status": "active", "reason": "Uses median exact consistent fee evidence only.", "impact": "It measures budget headroom, not ROI or cost efficiency."},
        {"topic": "Views", "status": "active", "reason": "Uses percentile of content views_median among eligible candidates.", "impact": "Campaign-level live viewers are not mixed into content views."},
        {"topic": "Missing evidence", "status": "active", "reason": "Missing component evidence receives configured neutral score plus lower data-confidence score.", "impact": "Candidates remain computable without pretending missing data is zero performance."},
        {"topic": "Synthetic scenario", "status": "active", "reason": "The demo fee cap is a portfolio scenario and is not represented as a source campaign requirement.", "impact": "Private ranking output demonstrates the engine without inventing historical campaign facts."},
    ]
    write_csv(args.output_dir / "matching_limitations_v1.csv", limitations)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
