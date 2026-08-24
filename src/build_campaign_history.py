from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Iterable

from src.xlsx_probe import read_sheet_rows

FORBIDDEN_OUTPUT_FIELDS = {
    "address", "shipping_address", "phone", "phone_number", "tracking", "tracking_number",
    "ที่อยู่", "ที่อยู่จัดส่ง", "เบอร์โทร", "เลขพัสดุ",
}

REQUIREMENT_LABELS = {
    "persona_raw": re.compile(r"^persona\s*influencer$", re.I),
    "target_content_raw": re.compile(r"^target\s*content$", re.I),
    "content_style_raw": re.compile(r"^content\s*style$", re.I),
    "target_gender_raw": re.compile(r"^gender$", re.I),
    "target_age_raw": re.compile(r"^age\s*groups?$", re.I),
    "pain_point_raw": re.compile(r"^pain\s*point$", re.I),
    "platform_raw": re.compile(r"^platform$", re.I),
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file_obj:
        return list(csv.DictReader(file_obj))


def write_csv(rows: list[dict[str, object]], path: Path, fields: list[str] | None = None) -> None:
    if not rows:
        raise ValueError(f"cannot write empty output: {path}")
    if fields is None:
        fields = list(rows[0].keys())
    forbidden = {field.casefold() for field in fields} & {field.casefold() for field in FORBIDDEN_OUTPUT_FIELDS}
    if forbidden:
        raise ValueError(f"PII fields are forbidden from campaign history outputs: {sorted(forbidden)}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as file_obj:
        writer = csv.DictWriter(file_obj, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def stable_id(prefix: str, *parts: str) -> str:
    seed = "|".join(parts)
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def text(value: object) -> str:
    return "" if value is None else str(value).strip()


def first_number(value: str) -> float | None:
    cleaned = value.replace(",", "")
    matches = re.findall(r"(?<![\w.])\d+(?:\.\d+)?", cleaned)
    if not matches:
        return None
    for raw in matches:
        number = float(raw)
        if number >= 1000:
            return number
    return float(matches[0])


def next_nonempty(row: list[object | None], start_index: int) -> str:
    for value in row[start_index + 1 :]:
        candidate = text(value)
        if candidate:
            return candidate
    return ""


def classify_budget_scope(raw: str) -> str:
    normalized = raw.casefold()
    if "influencer" in normalized and "tiktok" in normalized:
        return "influencer_tiktok"
    if "งบรวม" in normalized or "งบประมาณรวม" in normalized:
        return "campaign_total"
    return "candidate_pool_unspecified"


def extract_requirement_rows(
    rows: list[list[object | None]],
    stop_before_row: int,
) -> tuple[dict[str, str], list[dict[str, object]]]:
    fields = {key: "" for key in REQUIREMENT_LABELS}
    field_sources: list[str] = []
    budgets: list[dict[str, object]] = []
    for row_number, row in enumerate(rows[: max(0, stop_before_row - 1)], start=1):
        for col_index, value in enumerate(row):
            raw = text(value)
            if not raw:
                continue
            for field, pattern in REQUIREMENT_LABELS.items():
                if pattern.fullmatch(raw):
                    resolved = next_nonempty(row, col_index)
                    if resolved and not fields[field]:
                        fields[field] = resolved
                        field_sources.append(f"row {row_number}:{raw}")
            if re.search(r"budget|งบประมาณ", raw, re.I):
                # Budget amounts must be present in the same source cell.
                # A bare column header such as "BUDGET" must not borrow digits
                # from adjacent headers such as "30-day sales" or "select 8".
                amount = first_number(raw)
                if amount is not None:
                    budgets.append(
                        {
                            "source_row_number": row_number,
                            "budget_scope": classify_budget_scope(raw),
                            "budget_amount": amount,
                            "currency": "THB",
                            "budget_source_raw": raw,
                        }
                    )
    fields["requirement_source_rows"] = " || ".join(field_sources)
    return fields, budgets


def select_primary_budget(budgets: list[dict[str, object]]) -> tuple[float | str, str, str]:
    precedence = {"influencer_tiktok": 0, "candidate_pool_unspecified": 1, "campaign_total": 2}
    if not budgets:
        return "", "", ""
    chosen = sorted(budgets, key=lambda row: (precedence.get(str(row["budget_scope"]), 9), int(row["source_row_number"])))[0]
    return float(chosen["budget_amount"]), str(chosen["budget_scope"]), str(chosen["budget_source_raw"])


def load_campaign_map(path: Path) -> list[dict[str, object]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    campaigns = payload.get("campaigns", [])
    if not isinstance(campaigns, list) or not campaigns:
        raise ValueError("campaign map must contain a non-empty campaigns list")
    keys: set[tuple[str, str]] = set()
    for row in campaigns:
        key = (str(row["source_filename"]), str(row["source_sheet_name"]))
        if key in keys:
            raise ValueError(f"duplicate campaign-map source key: {key}")
        keys.add(key)
    return campaigns


def build_registries(campaign_map: list[dict[str, object]]) -> tuple[list[dict[str, object]], list[dict[str, object]], dict[tuple[str, str], str]]:
    brands: dict[str, dict[str, object]] = {}
    campaigns: list[dict[str, object]] = []
    source_to_campaign: dict[tuple[str, str], str] = {}
    for item in campaign_map:
        canonical_brand = str(item["canonical_brand_name"]).strip()
        brand_id = stable_id("brd", canonical_brand.casefold())
        brands.setdefault(
            brand_id,
            {
                "brand_id": brand_id,
                "canonical_brand_name": canonical_brand,
                "brand_mapping_method": item.get("brand_mapping_method", "private_mapping_config"),
                "brand_mapping_confidence": item.get("brand_mapping_confidence", "medium"),
                "business_verification_status": item.get("business_verification_status", "pending"),
            },
        )
        source_filename = str(item["source_filename"])
        source_sheet_name = str(item["source_sheet_name"])
        campaign_id = stable_id("cmp", source_filename.casefold(), source_sheet_name.casefold())
        source_to_campaign[(source_filename, source_sheet_name)] = campaign_id
        campaigns.append(
            {
                "campaign_id": campaign_id,
                "brand_id": brand_id,
                "campaign_display_name": item.get("campaign_display_name", f"{canonical_brand} | {source_sheet_name.strip()}"),
                "source_filename": source_filename,
                "candidate_sheet_name": source_sheet_name,
                "campaign_period_label": item.get("campaign_period_label", ""),
                "period_resolution_method": item.get("period_resolution_method", "source_unspecified"),
                "period_confidence": item.get("period_confidence", ""),
                "platform": item.get("platform", "tiktok"),
                "campaign_name_status": item.get("campaign_name_status", "technical_source_instance_not_business_verified"),
                "campaign_registry_version": "v1",
            }
        )
    return sorted(brands.values(), key=lambda row: str(row["canonical_brand_name"]).casefold()), sorted(campaigns, key=lambda row: (str(row["source_filename"]).casefold(), str(row["candidate_sheet_name"]).casefold())), source_to_campaign


def bool_state(raw: str) -> bool | None:
    value = raw.strip().casefold()
    if value in {"true", "1", "yes", "y"}:
        return True
    if value in {"false", "0", "no", "n"}:
        return False
    return None


def float_or_none(raw: str) -> float | None:
    value = raw.strip()
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def status_summary(values: Iterable[bool | None]) -> tuple[str, int, int, int]:
    known = [value for value in values if value is not None]
    true_count = sum(value is True for value in known)
    false_count = sum(value is False for value in known)
    if true_count and false_count:
        return "conflict", len(known), true_count, false_count
    if true_count:
        return "selected" if true_count else "unknown", len(known), true_count, false_count
    if false_count:
        return "not_selected", len(known), true_count, false_count
    return "unknown", 0, 0, 0


def fact_status(values: Iterable[bool | None], positive_label: str) -> tuple[str, int, int, int]:
    known = [value for value in values if value is not None]
    true_count = sum(value is True for value in known)
    false_count = sum(value is False for value in known)
    if true_count and false_count:
        status = "conflict"
    elif true_count:
        status = positive_label
    elif false_count:
        status = f"not_{positive_label}"
    else:
        status = "unknown"
    return status, len(known), true_count, false_count


def min_max(values: Iterable[float | None]) -> tuple[float | str, float | str]:
    nums = [value for value in values if value is not None]
    if not nums:
        return "", ""
    return min(nums), max(nums)


def build_history(
    observations: list[dict[str, str]],
    source_to_campaign: dict[tuple[str, str], str],
    master_ids: set[str],
) -> tuple[list[dict[str, object]], list[dict[str, object]], dict[str, int]]:
    history: list[dict[str, object]] = []
    unmapped = 0
    missing_master = 0
    for row in observations:
        key = (row["source_filename"], row["source_sheet_name"])
        campaign_id = source_to_campaign.get(key)
        if not campaign_id:
            unmapped += 1
            continue
        influencer_id = row.get("influencer_id", "")
        if influencer_id not in master_ids:
            missing_master += 1
            continue
        history.append(
            {
                "campaign_observation_id": stable_id("cobs", campaign_id, row["source_row_hash"]),
                "campaign_id": campaign_id,
                "influencer_id": influencer_id,
                "canonical_handle": row.get("canonical_handle_candidate", ""),
                "source_filename": row["source_filename"],
                "source_sheet_name": row["source_sheet_name"],
                "source_row_number": row["source_row_number"],
                "source_row_hash": row["source_row_hash"],
                "tier_section_raw": row.get("section_context_raw", ""),
                "follower_snapshot": row.get("follower_normalized", ""),
                "engagement_snapshot": row.get("engagement_normalized", ""),
                "candidate_fee_amount": row.get("fee_amount_normalized", ""),
                "fee_model": row.get("fee_model", ""),
                "fee_unit": row.get("fee_unit", ""),
                "historical_sales_snapshot": row.get("historical_sales_normalized", ""),
                "audience_gender_raw": row.get("audience_gender_raw", ""),
                "audience_age_raw": row.get("audience_age_raw", ""),
                "selected_observation": row.get("selected_raw", ""),
                "confirmed_observation": row.get("confirmed_raw", ""),
                "pet_type_raw": row.get("pet_type_raw", ""),
                "source_pii_present": row.get("pii_present", ""),
                "identity_dq_status": row.get("dq_status", ""),
                "identity_dq_codes": row.get("dq_codes", ""),
                "identity_review_id": row.get("identity_review_id", ""),
                "identity_review_decision": row.get("identity_review_decision", ""),
                "history_version": "v1",
            }
        )

    groups: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for row in history:
        groups[(str(row["campaign_id"]), str(row["influencer_id"]))].append(row)

    facts: list[dict[str, object]] = []
    selection_conflicts = 0
    confirmation_conflicts = 0
    fee_conflicts = 0
    duplicate_pairs = 0
    for (campaign_id, influencer_id), rows in sorted(groups.items()):
        selected_status, selected_known, selected_true, selected_false = fact_status(
            [bool_state(str(row["selected_observation"])) for row in rows], "selected"
        )
        confirmed_status, confirmed_known, confirmed_true, confirmed_false = fact_status(
            [bool_state(str(row["confirmed_observation"])) for row in rows], "confirmed"
        )
        fees = [float_or_none(str(row["candidate_fee_amount"])) for row in rows]
        fee_min, fee_max = min_max(fees)
        fee_values = {value for value in fees if value is not None}
        fee_status = "missing" if not fee_values else ("consistent" if len(fee_values) == 1 else "conflict")
        follower_min, follower_max = min_max(float_or_none(str(row["follower_snapshot"])) for row in rows)
        engagement_min, engagement_max = min_max(float_or_none(str(row["engagement_snapshot"])) for row in rows)
        sales_min, sales_max = min_max(float_or_none(str(row["historical_sales_snapshot"])) for row in rows)
        dq_codes: list[str] = []
        if len(rows) > 1:
            duplicate_pairs += 1
            dq_codes.append("DQ_DUPLICATE_CAMPAIGN_INFLUENCER_SOURCE")
        if selected_status == "conflict":
            selection_conflicts += 1
            dq_codes.append("DQ_SELECTED_STATUS_CONFLICT")
        if confirmed_status == "conflict":
            confirmation_conflicts += 1
            dq_codes.append("DQ_CONFIRMED_STATUS_CONFLICT")
        if fee_status == "conflict":
            fee_conflicts += 1
            dq_codes.append("DQ_FEE_CONFLICT")
        facts.append(
            {
                "campaign_influencer_id": stable_id("cinf", campaign_id, influencer_id),
                "campaign_id": campaign_id,
                "influencer_id": influencer_id,
                "canonical_handle": rows[0]["canonical_handle"],
                "observation_count": len(rows),
                "selected_status": selected_status,
                "selected_known_observations": selected_known,
                "selected_true_observations": selected_true,
                "selected_false_observations": selected_false,
                "confirmed_status": confirmed_status,
                "confirmed_known_observations": confirmed_known,
                "confirmed_true_observations": confirmed_true,
                "confirmed_false_observations": confirmed_false,
                "fee_status": fee_status,
                "fee_min": fee_min,
                "fee_max": fee_max,
                "fee_models": " || ".join(sorted({str(row["fee_model"]) for row in rows if str(row["fee_model"])})),
                "follower_snapshot_min": follower_min,
                "follower_snapshot_max": follower_max,
                "engagement_snapshot_min": engagement_min,
                "engagement_snapshot_max": engagement_max,
                "historical_sales_snapshot_min": sales_min,
                "historical_sales_snapshot_max": sales_max,
                "tier_sections_raw": " || ".join(sorted({str(row["tier_section_raw"]) for row in rows if str(row["tier_section_raw"])})),
                "source_occurrences": " || ".join(sorted({f"{row['source_filename']} | {row['source_sheet_name']} | row {row['source_row_number']}" for row in rows})),
                "campaign_history_dq_status": "WARN" if dq_codes else "PASS",
                "campaign_history_dq_codes": ";".join(dq_codes),
                "history_version": "v1",
            }
        )
    stats = {
        "resolved_observations_input": len(observations),
        "campaign_observations_mapped": len(history),
        "unmapped_campaign_observations": unmapped,
        "missing_master_observations": missing_master,
        "fact_campaign_influencer_records": len(facts),
        "duplicate_campaign_influencer_pairs": duplicate_pairs,
        "selection_conflict_pairs": selection_conflicts,
        "confirmation_conflict_pairs": confirmation_conflicts,
        "fee_conflict_pairs": fee_conflicts,
    }
    return history, facts, stats


def build_requirements(
    raw_dir: Path,
    campaigns: list[dict[str, object]],
    history: list[dict[str, object]],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    by_campaign_history: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in history:
        by_campaign_history[str(row["campaign_id"])].append(row)

    requirements: list[dict[str, object]] = []
    budget_rows: list[dict[str, object]] = []
    for campaign in campaigns:
        campaign_id = str(campaign["campaign_id"])
        source_filename = str(campaign["source_filename"])
        sheet_name = str(campaign["candidate_sheet_name"])
        source_rows = by_campaign_history.get(campaign_id, [])
        header_rows = [int(str(row.get("source_row_number", "0"))) for row in source_rows]
        # We need the first detected candidate section header, which is always before the first observation.
        # Use source rows from the resolved observation input through the stored tier sections only as a safe fallback.
        first_observation_row = min(header_rows) if header_rows else 1
        workbook_rows = read_sheet_rows(raw_dir / source_filename, sheet_name, max_cols=30)
        # Scan all rows before the first candidate observation. Header labels can sit immediately above it.
        fields, budgets = extract_requirement_rows(workbook_rows, stop_before_row=first_observation_row)
        primary_budget, budget_scope, budget_raw = select_primary_budget(budgets)
        tier_sections = sorted({str(row.get("tier_section_raw", "")) for row in source_rows if str(row.get("tier_section_raw", ""))})
        nonempty_requirement_fields = sum(bool(fields[key]) for key in REQUIREMENT_LABELS)
        if nonempty_requirement_fields:
            requirement_status = "explicit_source_fields"
        elif budgets and tier_sections:
            requirement_status = "budget_and_tier_sections_only"
        elif budgets:
            requirement_status = "budget_only"
        elif tier_sections:
            requirement_status = "tier_sections_only"
        else:
            requirement_status = "source_missing"
        requirements.append(
            {
                "campaign_id": campaign_id,
                "primary_candidate_budget_amount": primary_budget,
                "primary_budget_scope": budget_scope,
                "primary_budget_source_raw": budget_raw,
                "budget_currency": "THB" if primary_budget != "" else "",
                "tier_sections_raw": " || ".join(tier_sections),
                "persona_raw": fields["persona_raw"],
                "target_content_raw": fields["target_content_raw"],
                "content_style_raw": fields["content_style_raw"],
                "target_gender_raw": fields["target_gender_raw"],
                "target_age_raw": fields["target_age_raw"],
                "pain_point_raw": fields["pain_point_raw"],
                "platform_raw": fields["platform_raw"],
                "requirement_status": requirement_status,
                "requirement_inheritance_applied": False,
                "requirement_source_rows": fields["requirement_source_rows"],
                "requirement_version": "v1",
            }
        )
        for budget in budgets:
            budget_rows.append(
                {
                    "campaign_budget_observation_id": stable_id("cbud", campaign_id, str(budget["source_row_number"]), str(budget["budget_scope"]), str(budget["budget_amount"])),
                    "campaign_id": campaign_id,
                    "source_filename": source_filename,
                    "source_sheet_name": sheet_name,
                    **budget,
                    "budget_observation_version": "v1",
                }
            )
    return requirements, budget_rows



def build_campaign_summary(
    campaigns: list[dict[str, object]],
    requirements: list[dict[str, object]],
    facts: list[dict[str, object]],
) -> list[dict[str, object]]:
    req_by_campaign = {str(row["campaign_id"]): row for row in requirements}
    facts_by_campaign: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in facts:
        facts_by_campaign[str(row["campaign_id"])].append(row)
    result: list[dict[str, object]] = []
    for campaign in campaigns:
        campaign_id = str(campaign["campaign_id"])
        rows = facts_by_campaign.get(campaign_id, [])
        req = req_by_campaign.get(campaign_id, {})
        selected_counts = {status: 0 for status in ["selected", "not_selected", "conflict", "unknown"]}
        confirmed_counts = {status: 0 for status in ["confirmed", "not_confirmed", "conflict", "unknown"]}
        for row in rows:
            selected_counts[str(row.get("selected_status", "unknown"))] = selected_counts.get(str(row.get("selected_status", "unknown")), 0) + 1
            confirmed_counts[str(row.get("confirmed_status", "unknown"))] = confirmed_counts.get(str(row.get("confirmed_status", "unknown")), 0) + 1
        result.append(
            {
                "campaign_id": campaign_id,
                "brand_id": campaign["brand_id"],
                "campaign_display_name": campaign["campaign_display_name"],
                "campaign_period_label": campaign["campaign_period_label"],
                "candidate_sheet_name": campaign["candidate_sheet_name"],
                "candidate_influencer_count": len(rows),
                "source_observation_count": sum(int(row.get("observation_count", 0)) for row in rows),
                "selected_count": selected_counts.get("selected", 0),
                "not_selected_count": selected_counts.get("not_selected", 0),
                "selection_conflict_count": selected_counts.get("conflict", 0),
                "selection_unknown_count": selected_counts.get("unknown", 0),
                "confirmed_count": confirmed_counts.get("confirmed", 0),
                "confirmation_conflict_count": confirmed_counts.get("conflict", 0),
                "dq_warn_pair_count": sum(str(row.get("campaign_history_dq_status")) == "WARN" for row in rows),
                "primary_candidate_budget_amount": req.get("primary_candidate_budget_amount", ""),
                "primary_budget_scope": req.get("primary_budget_scope", ""),
                "requirement_status": req.get("requirement_status", ""),
                "campaign_summary_version": "v1",
            }
        )
    return result

def main() -> int:
    parser = argparse.ArgumentParser(description="Build private Brand/Campaign registries and Golden-Master-linked campaign history.")
    parser.add_argument("--resolved-observations", required=True, type=Path)
    parser.add_argument("--golden-master", required=True, type=Path)
    parser.add_argument("--campaign-map", required=True, type=Path)
    parser.add_argument("--raw-dir", required=True, type=Path)
    parser.add_argument("--brand-output", required=True, type=Path)
    parser.add_argument("--campaign-output", required=True, type=Path)
    parser.add_argument("--requirement-output", required=True, type=Path)
    parser.add_argument("--budget-observation-output", required=True, type=Path)
    parser.add_argument("--history-observation-output", required=True, type=Path)
    parser.add_argument("--fact-output", required=True, type=Path)
    parser.add_argument("--summary-output", required=True, type=Path)
    parser.add_argument("--dq-issues-output", required=True, type=Path)
    parser.add_argument("--reconciliation-output", required=True, type=Path)
    args = parser.parse_args()

    observations = read_csv(args.resolved_observations)
    master = read_csv(args.golden_master)
    campaign_map = load_campaign_map(args.campaign_map)
    brands, campaigns, source_to_campaign = build_registries(campaign_map)
    master_ids = {row["influencer_id"] for row in master}
    history, facts, history_stats = build_history(observations, source_to_campaign, master_ids)
    requirements, budgets = build_requirements(args.raw_dir, campaigns, history)
    campaign_summary = build_campaign_summary(campaigns, requirements, facts)
    dq_issues = [row for row in facts if row.get("campaign_history_dq_status") == "WARN"]

    campaign_sources = {(str(row["source_filename"]), str(row["candidate_sheet_name"])) for row in campaigns}
    observation_sources = {(row["source_filename"], row["source_sheet_name"]) for row in observations}
    missing_registry_sources = sorted(observation_sources - campaign_sources)
    unused_registry_sources = sorted(campaign_sources - observation_sources)
    reconciliation = [
        {"metric": "brand_registry_records", "value": len(brands), "status": "PASS"},
        {"metric": "campaign_registry_records", "value": len(campaigns), "status": "PASS"},
        {"metric": "campaign_requirement_records", "value": len(requirements), "status": "PASS" if len(requirements) == len(campaigns) else "FAIL"},
        {"metric": "resolved_observations_input", "value": history_stats["resolved_observations_input"], "status": "PASS"},
        {"metric": "campaign_observations_mapped", "value": history_stats["campaign_observations_mapped"], "status": "PASS" if history_stats["campaign_observations_mapped"] == history_stats["resolved_observations_input"] else "FAIL"},
        {"metric": "unmapped_campaign_observations", "value": history_stats["unmapped_campaign_observations"], "status": "PASS" if history_stats["unmapped_campaign_observations"] == 0 else "FAIL"},
        {"metric": "missing_master_observations", "value": history_stats["missing_master_observations"], "status": "PASS" if history_stats["missing_master_observations"] == 0 else "FAIL"},
        {"metric": "fact_campaign_influencer_records", "value": history_stats["fact_campaign_influencer_records"], "status": "PASS"},
        {"metric": "campaign_summary_records", "value": len(campaign_summary), "status": "PASS" if len(campaign_summary) == len(campaigns) else "FAIL"},
        {"metric": "campaign_history_dq_issue_records", "value": len(dq_issues), "status": "WARN" if dq_issues else "PASS"},
        {"metric": "duplicate_campaign_influencer_pairs", "value": history_stats["duplicate_campaign_influencer_pairs"], "status": "WARN" if history_stats["duplicate_campaign_influencer_pairs"] else "PASS"},
        {"metric": "selection_conflict_pairs", "value": history_stats["selection_conflict_pairs"], "status": "WARN" if history_stats["selection_conflict_pairs"] else "PASS"},
        {"metric": "confirmation_conflict_pairs", "value": history_stats["confirmation_conflict_pairs"], "status": "WARN" if history_stats["confirmation_conflict_pairs"] else "PASS"},
        {"metric": "fee_conflict_pairs", "value": history_stats["fee_conflict_pairs"], "status": "WARN" if history_stats["fee_conflict_pairs"] else "PASS"},
        {"metric": "missing_campaign_registry_sources", "value": len(missing_registry_sources), "status": "PASS" if not missing_registry_sources else "FAIL"},
        {"metric": "unused_campaign_registry_sources", "value": len(unused_registry_sources), "status": "WARN" if unused_registry_sources else "PASS"},
        {"metric": "pii_value_columns_emitted", "value": 0, "status": "PASS"},
        {"metric": "requirement_inheritance_applied", "value": 0, "status": "PASS"},
    ]

    write_csv(brands, args.brand_output)
    write_csv(campaigns, args.campaign_output)
    write_csv(requirements, args.requirement_output)
    write_csv(budgets or [{"campaign_budget_observation_id": "", "campaign_id": "", "source_filename": "", "source_sheet_name": "", "source_row_number": "", "budget_scope": "", "budget_amount": "", "currency": "", "budget_source_raw": "", "budget_observation_version": "v1"}], args.budget_observation_output)
    write_csv(history, args.history_observation_output)
    write_csv(facts, args.fact_output)
    write_csv(campaign_summary, args.summary_output)
    if dq_issues:
        write_csv(dq_issues, args.dq_issues_output)
    else:
        write_csv([{key: "" for key in facts[0].keys()}], args.dq_issues_output)
    write_csv(reconciliation, args.reconciliation_output)

    failed = [row for row in reconciliation if row["status"] == "FAIL"]
    print(
        " ".join(
            [
                f"brands={len(brands)}",
                f"campaigns={len(campaigns)}",
                f"requirements={len(requirements)}",
                f"budget_observations={len(budgets)}",
                f"campaign_observations={len(history)}",
                f"fact_campaign_influencer={len(facts)}",
                f"campaign_summary={len(campaign_summary)}",
                f"dq_issue_records={len(dq_issues)}",
                f"reconciliation_failures={len(failed)}",
            ]
        )
    )
    return 2 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
