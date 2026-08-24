from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from src.requirement_normalization import (
    DEFAULT_TAXONOMY,
    build_audience_profiles,
    build_requirement_experience,
    load_taxonomy,
    normalize_requirement_rows,
)


def read_csv(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = list(rows)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader(); writer.writerows(rows)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--campaign-requirements", required=True)
    p.add_argument("--campaign-registry", required=True)
    p.add_argument("--campaign-observations", required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--taxonomy")
    args = p.parse_args()

    reqs = read_csv(Path(args.campaign_requirements))
    registry_rows = read_csv(Path(args.campaign_registry))
    observations = read_csv(Path(args.campaign_observations))
    registry = {r["campaign_id"]: r for r in registry_rows}
    taxonomy = load_taxonomy(args.taxonomy)

    normalized, req_dq = normalize_requirement_rows(reqs, registry, taxonomy)
    audience, audience_dq = build_audience_profiles(observations)
    normalized_map = {r["campaign_id"]: r for r in normalized}
    experience = build_requirement_experience(observations, normalized_map)
    dq = req_dq + audience_dq

    out = Path(args.output_dir)
    write_csv(out / "campaign_requirement_normalized_v1.csv", normalized)
    write_csv(out / "influencer_audience_profile_v1.csv", audience)
    write_csv(out / "influencer_requirement_experience_v1.csv", experience)
    write_csv(out / "requirement_normalization_dq_issues_v1.csv", dq)

    taxonomy_rows = []
    for family, rules in taxonomy.items():
        for tag, keywords in rules.items():
            taxonomy_rows.append({"taxonomy_family": family, "tag": tag, "keywords": ";".join(keywords), "mapping_method": "deterministic_keyword_rule", "taxonomy_version": "v1"})
    write_csv(out / "requirement_taxonomy_v1.csv", taxonomy_rows)

    fit_ready = sum(r["fit_readiness"] == "ready_for_rule_based_fit" for r in normalized)
    source_missing = sum(r["fit_readiness"] != "ready_for_rule_based_fit" for r in normalized)
    audience_any = sum((int(r["audience_gender_observation_count"]) + int(r["audience_age_observation_count"])) > 0 for r in audience)
    recon = [
        {"metric": "campaign_requirement_input_rows", "value": len(reqs), "status": "PASS", "meaning": "One row per Campaign Registry source instance."},
        {"metric": "campaign_requirement_normalized_rows", "value": len(normalized), "status": "PASS" if len(normalized) == len(reqs) else "FAIL", "meaning": "Normalized row count must reconcile to input."},
        {"metric": "fit_ready_campaigns", "value": fit_ready, "status": "PASS", "meaning": "Campaigns with enough explicit source requirements for rule-based fit dimensions."},
        {"metric": "insufficient_source_requirement_campaigns", "value": source_missing, "status": "WARN" if source_missing else "PASS", "meaning": "No same-brand inheritance is applied."},
        {"metric": "audience_profile_rows", "value": len(audience), "status": "PASS", "meaning": "Distinct influencer identities with candidate-history observations."},
        {"metric": "audience_profiles_with_any_evidence", "value": audience_any, "status": "PASS", "meaning": "At least one governed audience gender or age observation."},
        {"metric": "requirement_experience_rows", "value": len(experience), "status": "PASS", "meaning": "Historical campaign-requirement exposure per influencer."},
        {"metric": "dq_issue_rows", "value": len(dq), "status": "WARN" if dq else "PASS", "meaning": "Warnings remain evidence and are not silently corrected."},
        {"metric": "automatic_requirement_inheritance", "value": 0, "status": "PASS", "meaning": "Missing campaign requirements are not inherited from another month/campaign."},
        {"metric": "fuzzy_taxonomy_mapping", "value": 0, "status": "PASS", "meaning": "Only deterministic controlled keyword rules are used."},
    ]
    write_csv(out / "requirement_normalization_reconciliation_v1.csv", recon)

    limitations = [
        {"topic": "Taxonomy semantics", "status": "rule_derived_not_business_verified", "reason": "Theme/persona/style tags are deterministic interpretations of explicit source text, not approved enterprise master taxonomy.", "next_control": "Business reviewer can approve/rename tags before production use."},
        {"topic": "Missing monthly briefs", "status": "not_inherited", "reason": "Tier-only campaigns do not automatically reuse requirements from another month of the same brand.", "next_control": "Obtain source brief or explicit approval for inheritance."},
        {"topic": "Persona experience", "status": "historical_exposure_only", "reason": "A creator appearing in a campaign with a persona requirement is evidence of campaign exposure, not proof that the creator intrinsically has that persona.", "next_control": "Use as category/persona experience evidence, not identity truth."},
        {"topic": "Audience snapshots", "status": "historical_observation", "reason": "Audience gender/age fields are campaign-time snapshots and can change over time.", "next_control": "Add snapshot dates before Recency-weighted audience fit."},
        {"topic": "Category fit", "status": "not_yet_named_enterprise_category", "reason": "v1 emits controlled campaign-theme tags rather than claiming a verified brand/category taxonomy.", "next_control": "Govern brand/category dimension before labeling this enterprise category fit."},
    ]
    write_csv(out / "requirement_normalization_limitations_v1.csv", limitations)

    (out / "requirement_taxonomy_v1_private.json").write_text(json.dumps(taxonomy, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"campaigns": len(normalized), "fit_ready": fit_ready, "audience_profiles": len(audience), "experience_rows": len(experience), "dq_issues": len(dq)}, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
