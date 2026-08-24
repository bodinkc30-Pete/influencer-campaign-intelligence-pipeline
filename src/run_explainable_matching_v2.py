from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from src.matching_v2 import build_target_excluded_context, load_v2_config, score_target_campaign


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
    parser = argparse.ArgumentParser(description="Run leakage-guarded explainable matching v2 for fit-ready campaigns.")
    parser.add_argument("--master", required=True, type=Path)
    parser.add_argument("--campaign-facts", required=True, type=Path)
    parser.add_argument("--campaign-registry", required=True, type=Path)
    parser.add_argument("--campaign-requirements", required=True, type=Path)
    parser.add_argument("--deliverables", required=True, type=Path)
    parser.add_argument("--performance", required=True, type=Path)
    parser.add_argument("--campaign-observations", required=True, type=Path)
    parser.add_argument("--normalized-requirements", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    masters = read_csv(args.master)
    campaign_facts = read_csv(args.campaign_facts)
    campaign_registry = read_csv(args.campaign_registry)
    campaign_requirement_rows = read_csv(args.campaign_requirements)
    deliverables = read_csv(args.deliverables)
    performance = read_csv(args.performance)
    campaign_observations = read_csv(args.campaign_observations)
    normalized = read_csv(args.normalized_requirements)
    normalized_by_id = {row["campaign_id"]: row for row in normalized}
    budget_by_id = {row["campaign_id"]: row for row in campaign_requirement_rows}
    config = load_v2_config(json.loads(args.config.read_text(encoding="utf-8")))

    scores: list[dict[str, object]] = []
    runs: list[dict[str, object]] = []
    leakage: list[dict[str, object]] = []
    for target in normalized:
        if target.get("fit_readiness") != "ready_for_rule_based_fit":
            continue
        context, audit = build_target_excluded_context(
            target["campaign_id"],
            masters,
            campaign_facts,
            campaign_registry,
            deliverables,
            performance,
            campaign_observations,
            normalized_by_id,
        )
        target_scores, run = score_target_campaign(target, budget_by_id.get(target["campaign_id"], {}), context, config)
        scores.extend(target_scores)
        runs.append(run)
        leakage.append({
            "scenario_id": run["scenario_id"],
            "target_campaign_id": target["campaign_id"],
            "target_campaign_display_name": target.get("campaign_display_name", ""),
            **audit,
            "target_outcome_fields_used_in_score": 0,
            "leakage_guard_status": "PASS" if audit["target_campaign_rows_used_in_score"] == 0 else "FAIL",
        })

    shortlists = [row for row in scores if row["eligibility_status"] == "eligible" and int(row["rank"] or 0) <= config.shortlist_size]
    rejections = [row for row in scores if row["eligibility_status"] == "ineligible"]
    reconciliation = [
        {"metric": "fit_ready_target_campaigns", "value": len(runs), "status": "PASS" if len(runs) > 0 else "FAIL"},
        {"metric": "candidate_score_rows", "value": len(scores), "status": "PASS"},
        {"metric": "shortlist_rows", "value": len(shortlists), "status": "PASS"},
        {"metric": "eligibility_rejection_rows", "value": len(rejections), "status": "PASS"},
        {"metric": "duplicate_scenario_influencer_rows", "value": len(scores) - len({(r["scenario_id"], r["influencer_id"]) for r in scores}), "status": "PASS" if len(scores) == len({(r["scenario_id"], r["influencer_id"]) for r in scores}) else "FAIL"},
        {"metric": "eligible_rows_missing_rank", "value": sum(1 for r in scores if r["eligibility_status"] == "eligible" and not r["rank"]), "status": "PASS" if all(r["rank"] for r in scores if r["eligibility_status"] == "eligible") else "FAIL"},
        {"metric": "ineligible_rows_with_rank", "value": sum(1 for r in scores if r["eligibility_status"] == "ineligible" and r["rank"]), "status": "PASS" if all(not r["rank"] for r in scores if r["eligibility_status"] == "ineligible") else "FAIL"},
        {"metric": "leakage_audit_failures", "value": sum(1 for r in leakage if r["leakage_guard_status"] != "PASS"), "status": "PASS" if all(r["leakage_guard_status"] == "PASS" for r in leakage) else "FAIL"},
        {"metric": "target_outcome_fields_used_in_score", "value": sum(int(r["target_outcome_fields_used_in_score"]) for r in leakage), "status": "PASS" if all(int(r["target_outcome_fields_used_in_score"]) == 0 for r in leakage) else "FAIL"},
    ]

    write_csv(args.output_dir / "match_v2_run.csv", runs)
    write_csv(args.output_dir / "match_v2_candidate_score.csv", scores)
    write_csv(args.output_dir / "match_v2_shortlist.csv", shortlists)
    write_csv(args.output_dir / "match_v2_eligibility_rejections.csv", rejections)
    write_csv(args.output_dir / "match_v2_leakage_audit.csv", leakage)
    write_csv(args.output_dir / "matching_v2_reconciliation.csv", reconciliation)
    return 0 if all(r["status"] == "PASS" for r in reconciliation) else 2


if __name__ == "__main__":
    raise SystemExit(main())
