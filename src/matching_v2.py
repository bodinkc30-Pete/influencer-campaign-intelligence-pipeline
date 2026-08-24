from __future__ import annotations

import math
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Iterable, Mapping

from .requirement_normalization import normalize_audience_age, normalize_audience_gender


@dataclass(frozen=True)
class MatchingV2Config:
    config_version: str
    shortlist_size: int
    neutral_missing_score: float
    campaign_count_cap: float
    brand_count_cap: float
    individual_budget_scopes: frozenset[str]
    weights: dict[str, float]


REQUIRED_WEIGHT_KEYS = {
    "audience_gender_fit",
    "audience_age_fit",
    "theme_experience_fit",
    "persona_experience_fit",
    "content_style_experience_fit",
    "historical_experience",
    "cross_brand_experience",
    "selection_history",
    "view_performance",
    "budget_headroom",
    "operational_reliability",
    "data_confidence",
}


def parse_float(value: object | None) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    text = str(value).strip().replace(",", "")
    if not text or text in {"-", "#DIV/0!", "#N/A", "#VALUE!", "#REF!", "#NAME?"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def parse_int(value: object | None, default: int = 0) -> int:
    number = parse_float(value)
    return int(number) if number is not None else default


def parse_bool(value: object | None) -> bool:
    return str(value or "").strip().casefold() in {"true", "1", "yes", "y"}


def known_bool(value: object | None) -> bool | None:
    text = str(value or "").strip().casefold()
    if text in {"true", "1", "yes", "y", "posted", "ลงแล้ว", "เรียบร้อย", "confirm", "confirmed"}:
        return True
    if text in {"false", "0", "no", "n", "not posted", "ยังไม่ลง", "not confirmed"}:
        return False
    return None


def median_or_none(values: list[float]) -> float | None:
    return float(statistics.median(values)) if values else None


def split_tags(value: object | None) -> set[str]:
    return {part.strip() for part in str(value or "").split(";") if part.strip()}


def load_v2_config(data: Mapping[str, object]) -> MatchingV2Config:
    weights = {str(k): float(v) for k, v in dict(data.get("weights") or {}).items()}
    if set(weights) != REQUIRED_WEIGHT_KEYS:
        missing = sorted(REQUIRED_WEIGHT_KEYS - set(weights))
        extra = sorted(set(weights) - REQUIRED_WEIGHT_KEYS)
        raise ValueError(f"Matching v2 weight keys invalid; missing={missing}, extra={extra}")
    if any(value < 0 for value in weights.values()):
        raise ValueError("Matching v2 weights cannot be negative")
    if not math.isclose(sum(weights.values()), 1.0, rel_tol=0, abs_tol=1e-9):
        raise ValueError("Matching v2 weights must sum to 1.0")

    guardrails = dict(data.get("guardrails") or {})
    if guardrails.get("machine_learning") is not False:
        raise ValueError("Matching v2 does not allow machine learning")
    if guardrails.get("fuzzy_identity_resolution") is not False:
        raise ValueError("Matching v2 does not allow fuzzy identity resolution")
    if guardrails.get("target_campaign_leakage") != "forbidden":
        raise ValueError("Matching v2 requires target_campaign_leakage='forbidden'")
    if guardrails.get("automatic_requirement_inheritance") is not False:
        raise ValueError("Matching v2 does not allow automatic requirement inheritance")

    caps = dict(data.get("caps") or {})
    return MatchingV2Config(
        config_version=str(data.get("config_version") or "matching-v2"),
        shortlist_size=int(data.get("shortlist_size") or 30),
        neutral_missing_score=float(data.get("neutral_missing_score") or 50.0),
        campaign_count_cap=float(caps.get("campaign_count") or 5),
        brand_count_cap=float(caps.get("brand_count") or 3),
        individual_budget_scopes=frozenset(str(x) for x in (data.get("individual_budget_scopes") or ["influencer_tiktok"])),
        weights=weights,
    )


def _bounded_score(value: float, cap: float) -> float:
    if cap <= 0:
        return 0.0
    return max(0.0, min(100.0, (value / cap) * 100.0))


def _percentile_ranks(values_by_id: dict[str, float]) -> dict[str, float]:
    if not values_by_id:
        return {}
    ordered = sorted(values_by_id.items(), key=lambda x: (x[1], x[0]))
    n = len(ordered)
    result: dict[str, float] = {}
    i = 0
    while i < n:
        j = i + 1
        while j < n and math.isclose(ordered[j][1], ordered[i][1], rel_tol=0, abs_tol=1e-12):
            j += 1
        average_position = ((i + 1) + j) / 2.0
        percentile = 100.0 if n == 1 else ((average_position - 1.0) / (n - 1.0)) * 100.0
        for k in range(i, j):
            result[ordered[k][0]] = percentile
        i = j
    return result


def _target_requirement_dimensions(requirement: Mapping[str, object], budget_cap: float | None) -> dict[str, bool]:
    return {
        "audience_gender_fit": str(requirement.get("target_gender_mode", "")) not in {"", "unknown", "unmapped"},
        "audience_age_fit": parse_int(requirement.get("target_age_min"), -1) >= 0 and parse_int(requirement.get("target_age_max"), -1) >= 0,
        "theme_experience_fit": bool(split_tags(requirement.get("campaign_theme_tags"))),
        "persona_experience_fit": bool(split_tags(requirement.get("persona_tags"))),
        "content_style_experience_fit": bool(split_tags(requirement.get("content_style_tags"))),
        "historical_experience": True,
        "cross_brand_experience": True,
        "selection_history": True,
        "view_performance": True,
        "budget_headroom": budget_cap is not None,
        "operational_reliability": True,
        "data_confidence": True,
    }


def _age_overlap_score(target_min: int | None, target_max: int | None, dominant_band: str, neutral: float) -> float | None:
    if target_min is None or target_max is None:
        return None
    if not dominant_band or "-" not in dominant_band:
        return neutral
    try:
        low, high = [int(x) for x in dominant_band.split("-", 1)]
    except ValueError:
        return neutral
    intersection = max(0, min(target_max, high) - max(target_min, low) + 1)
    band_width = max(1, high - low + 1)
    return max(0.0, min(100.0, (intersection / band_width) * 100.0))


def _gender_fit_score(requirement: Mapping[str, object], dominant_gender: str, evidence_count: int, neutral: float) -> float | None:
    mode = str(requirement.get("target_gender_mode", ""))
    if mode in {"", "unknown", "unmapped"}:
        return None
    if evidence_count <= 0:
        return neutral
    if mode == "all":
        return 100.0
    if mode == "female_only":
        return {"female": 100.0, "mixed": 70.0, "male": 0.0}.get(dominant_gender, neutral)
    if mode == "male_only":
        return {"male": 100.0, "mixed": 70.0, "female": 0.0}.get(dominant_gender, neutral)
    if mode == "mixed_weighted":
        female = parse_float(requirement.get("female_target_share")) or 0.5
        male = parse_float(requirement.get("male_target_share")) or 0.5
        if dominant_gender == "mixed":
            return 100.0
        preferred = "female" if female > male else "male" if male > female else "mixed"
        if preferred == "mixed":
            return 80.0
        return 90.0 if dominant_gender == preferred else 50.0
    return neutral


def _tag_coverage_score(target_tags: object | None, history_tags: set[str]) -> float | None:
    target = split_tags(target_tags)
    if not target:
        return None
    if not history_tags:
        return 0.0
    return (len(target & history_tags) / len(target)) * 100.0


def build_target_excluded_context(
    target_campaign_id: str,
    masters: Iterable[Mapping[str, str]],
    campaign_facts: Iterable[Mapping[str, str]],
    campaign_registry: Iterable[Mapping[str, str]],
    deliverables: Iterable[Mapping[str, str]],
    performance: Iterable[Mapping[str, str]],
    campaign_observations: Iterable[Mapping[str, str]],
    normalized_requirements: Mapping[str, Mapping[str, object]],
) -> tuple[dict[str, dict[str, object]], dict[str, int]]:
    """Build leakage-guarded feature context with target-campaign rows excluded before aggregation."""
    masters = list(masters)
    campaign_facts = list(campaign_facts)
    campaign_registry = list(campaign_registry)
    deliverables = list(deliverables)
    performance = list(performance)
    campaign_observations = list(campaign_observations)

    campaign_to_brand = {row["campaign_id"]: row.get("brand_id", "") for row in campaign_registry}
    features: dict[str, dict[str, object]] = {
        row["influencer_id"]: {
            "influencer_id": row["influencer_id"],
            "canonical_handle": row.get("canonical_handle", ""),
            "platform": row.get("platform", ""),
            "identity_confidence": row.get("identity_confidence", ""),
        }
        for row in masters
    }

    campaign_sets: dict[str, set[str]] = defaultdict(set)
    brand_sets: dict[str, set[str]] = defaultdict(set)
    selected_known: Counter[str] = Counter()
    selected_true: Counter[str] = Counter()
    dq_warn: Counter[str] = Counter()
    fee_values: dict[str, list[float]] = defaultdict(list)

    excluded_campaign_fact_rows = 0
    for row in campaign_facts:
        if row.get("campaign_id") == target_campaign_id:
            excluded_campaign_fact_rows += 1
            continue
        iid = row.get("influencer_id", "")
        if iid not in features:
            continue
        cid = row.get("campaign_id", "")
        if cid:
            campaign_sets[iid].add(cid)
            brand = campaign_to_brand.get(cid, "")
            if brand:
                brand_sets[iid].add(brand)
        selected = row.get("selected_status", "")
        if selected in {"selected", "not_selected"}:
            selected_known[iid] += 1
            if selected == "selected":
                selected_true[iid] += 1
        if row.get("campaign_history_dq_status") == "WARN":
            dq_warn[iid] += 1
        if row.get("fee_status") == "consistent":
            low = parse_float(row.get("fee_min"))
            high = parse_float(row.get("fee_max"))
            if low is not None and high is not None and math.isclose(low, high, rel_tol=0, abs_tol=1e-9):
                fee_values[iid].append(low)

    posted_known: Counter[str] = Counter()
    posted_true: Counter[str] = Counter()
    excluded_deliverable_rows = 0
    for row in deliverables:
        if row.get("campaign_id") == target_campaign_id:
            excluded_deliverable_rows += 1
            continue
        iid = row.get("influencer_id", "")
        if iid not in features:
            continue
        state = known_bool(row.get("posted_raw"))
        if state is not None:
            posted_known[iid] += 1
            if state:
                posted_true[iid] += 1

    view_values: dict[str, list[float]] = defaultdict(list)
    performance_count: Counter[str] = Counter()
    excluded_performance_rows = 0
    for row in performance:
        if row.get("campaign_id") == target_campaign_id:
            excluded_performance_rows += 1
            continue
        iid = row.get("influencer_id", "")
        if iid not in features:
            continue
        performance_count[iid] += 1
        views = parse_float(row.get("views"))
        if views is not None:
            view_values[iid].append(views)

    view_medians = {iid: median_or_none(values) for iid, values in view_values.items() if values}
    view_percentiles = _percentile_ranks({iid: value for iid, value in view_medians.items() if value is not None})

    gender_counts: dict[str, Counter[str]] = defaultdict(Counter)
    age_counts: dict[str, Counter[str]] = defaultdict(Counter)
    theme_experience: dict[str, set[str]] = defaultdict(set)
    persona_experience: dict[str, set[str]] = defaultdict(set)
    style_experience: dict[str, set[str]] = defaultdict(set)
    seen_pairs: set[tuple[str, str]] = set()
    excluded_observation_rows = 0
    excluded_requirement_pairs = 0

    for row in campaign_observations:
        cid = row.get("campaign_id", "")
        if cid == target_campaign_id:
            excluded_observation_rows += 1
            if row.get("influencer_id"):
                excluded_requirement_pairs += 1
            continue
        iid = row.get("influencer_id", "")
        if iid not in features:
            continue
        gender, _method = normalize_audience_gender(row.get("audience_gender_raw", ""))
        if gender in {"female", "male", "mixed"}:
            gender_counts[iid][gender] += 1
        low, high, _age_method = normalize_audience_age(row.get("audience_age_raw", ""))
        if low is not None and high is not None:
            age_counts[iid][f"{low}-{high}"] += 1

        pair = (iid, cid)
        if not cid or pair in seen_pairs:
            continue
        seen_pairs.add(pair)
        req = normalized_requirements.get(cid)
        if not req:
            continue
        theme_experience[iid].update(split_tags(req.get("campaign_theme_tags")))
        persona_experience[iid].update(split_tags(req.get("persona_tags")))
        style_experience[iid].update(split_tags(req.get("content_style_tags")))

    for iid, feature in features.items():
        feature["campaign_count_ex_target"] = len(campaign_sets[iid])
        feature["brand_count_ex_target"] = len(brand_sets[iid])
        feature["selected_known_count_ex_target"] = selected_known[iid]
        feature["selected_rate_ex_target"] = (selected_true[iid] / selected_known[iid]) if selected_known[iid] else None
        feature["campaign_history_dq_warn_count_ex_target"] = dq_warn[iid]
        feature["fee_observed_median_ex_target"] = median_or_none(fee_values[iid])
        feature["fee_history_count_ex_target"] = len(fee_values[iid])
        feature["posted_rate_ex_target"] = (posted_true[iid] / posted_known[iid]) if posted_known[iid] else None
        feature["posted_known_count_ex_target"] = posted_known[iid]
        feature["performance_record_count_ex_target"] = performance_count[iid]
        feature["views_median_ex_target"] = view_medians.get(iid)
        feature["view_percentile_ex_target"] = view_percentiles.get(iid)

        gender_total = sum(gender_counts[iid].values())
        feature["audience_gender_observation_count_ex_target"] = gender_total
        feature["audience_gender_dominant_ex_target"] = gender_counts[iid].most_common(1)[0][0] if gender_total else "unknown"
        age_total = sum(age_counts[iid].values())
        feature["audience_age_observation_count_ex_target"] = age_total
        feature["audience_age_dominant_band_ex_target"] = age_counts[iid].most_common(1)[0][0] if age_total else ""
        feature["theme_experience_tags_ex_target"] = ";".join(sorted(theme_experience[iid]))
        feature["persona_experience_tags_ex_target"] = ";".join(sorted(persona_experience[iid]))
        feature["content_style_experience_tags_ex_target"] = ";".join(sorted(style_experience[iid]))

    audit = {
        "excluded_campaign_fact_rows": excluded_campaign_fact_rows,
        "excluded_deliverable_rows": excluded_deliverable_rows,
        "excluded_performance_rows": excluded_performance_rows,
        "excluded_campaign_observation_rows": excluded_observation_rows,
        "excluded_requirement_experience_pairs": excluded_requirement_pairs,
        "target_campaign_rows_used_in_score": 0,
    }
    return features, audit


def _data_confidence(feature: Mapping[str, object]) -> float:
    score = 0.0
    identity = str(feature.get("identity_confidence", ""))
    score += 10.0 if identity == "deterministic_exact" else 8.0 if identity == "reviewed_evidence" else 0.0
    score += 15.0 if parse_int(feature.get("selected_known_count_ex_target")) > 0 else 0.0
    score += 10.0 if parse_int(feature.get("fee_history_count_ex_target")) > 0 else 0.0
    score += 20.0 if parse_int(feature.get("performance_record_count_ex_target")) > 0 else 0.0
    score += 15.0 if parse_int(feature.get("posted_known_count_ex_target")) > 0 else 0.0
    score += 10.0 if parse_int(feature.get("audience_gender_observation_count_ex_target")) > 0 else 0.0
    score += 10.0 if parse_int(feature.get("audience_age_observation_count_ex_target")) > 0 else 0.0
    if any(
        split_tags(feature.get(key))
        for key in ("theme_experience_tags_ex_target", "persona_experience_tags_ex_target", "content_style_experience_tags_ex_target")
    ):
        score += 5.0
    score += 5.0 if parse_int(feature.get("campaign_history_dq_warn_count_ex_target")) == 0 else 0.0
    return max(0.0, min(100.0, score))


def score_target_campaign(
    target_requirement: Mapping[str, object],
    target_budget_row: Mapping[str, object],
    target_context: Mapping[str, Mapping[str, object]],
    config: MatchingV2Config,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    if target_requirement.get("fit_readiness") != "ready_for_rule_based_fit":
        raise ValueError("Target campaign is not ready_for_rule_based_fit")

    budget_scope = str(target_budget_row.get("primary_budget_scope", ""))
    raw_budget = parse_float(target_budget_row.get("primary_candidate_budget_amount"))
    budget_cap = raw_budget if raw_budget is not None and budget_scope in config.individual_budget_scopes else None
    active = _target_requirement_dimensions(target_requirement, budget_cap)
    active_weight_sum = sum(config.weights[key] for key, enabled in active.items() if enabled)
    if active_weight_sum <= 0:
        raise ValueError("No active matching dimensions for target campaign")

    target_min = parse_int(target_requirement.get("target_age_min"), -1)
    target_max = parse_int(target_requirement.get("target_age_max"), -1)
    if target_min < 0 or target_max < 0:
        target_min = target_max = None

    records: list[dict[str, object]] = []
    for iid, feature in target_context.items():
        reasons: list[str] = []
        if str(feature.get("platform", "")).casefold() != str(target_requirement.get("platform", "")).casefold():
            reasons.append("platform_mismatch")

        fee = parse_float(feature.get("fee_observed_median_ex_target"))
        if budget_cap is not None and fee is not None and fee > budget_cap:
            reasons.append("fee_over_explicit_individual_budget")

        neutral = config.neutral_missing_score
        components: dict[str, float | None] = {
            "audience_gender_fit": _gender_fit_score(
                target_requirement,
                str(feature.get("audience_gender_dominant_ex_target", "unknown")),
                parse_int(feature.get("audience_gender_observation_count_ex_target")),
                neutral,
            ),
            "audience_age_fit": _age_overlap_score(
                target_min,
                target_max,
                str(feature.get("audience_age_dominant_band_ex_target", "")),
                neutral,
            ),
            "theme_experience_fit": _tag_coverage_score(
                target_requirement.get("campaign_theme_tags"),
                split_tags(feature.get("theme_experience_tags_ex_target")),
            ),
            "persona_experience_fit": _tag_coverage_score(
                target_requirement.get("persona_tags"),
                split_tags(feature.get("persona_experience_tags_ex_target")),
            ),
            "content_style_experience_fit": _tag_coverage_score(
                target_requirement.get("content_style_tags"),
                split_tags(feature.get("content_style_experience_tags_ex_target")),
            ),
            "historical_experience": _bounded_score(parse_int(feature.get("campaign_count_ex_target")), config.campaign_count_cap),
            "cross_brand_experience": _bounded_score(parse_int(feature.get("brand_count_ex_target")), config.brand_count_cap),
            "selection_history": (parse_float(feature.get("selected_rate_ex_target")) or 0.0) * 100.0 if feature.get("selected_rate_ex_target") not in (None, "") else neutral,
            "view_performance": parse_float(feature.get("view_percentile_ex_target")) if feature.get("view_percentile_ex_target") not in (None, "") else neutral,
            "budget_headroom": max(0.0, min(100.0, (1.0 - (fee / budget_cap)) * 100.0)) if budget_cap is not None and fee is not None else (neutral if budget_cap is not None else None),
            "operational_reliability": (parse_float(feature.get("posted_rate_ex_target")) or 0.0) * 100.0 if feature.get("posted_rate_ex_target") not in (None, "") else neutral,
            "data_confidence": _data_confidence(feature),
        }

        weighted_total = None
        if not reasons:
            weighted_total = sum(
                float(components[key]) * config.weights[key]
                for key in config.weights
                if active[key] and components[key] is not None
            ) / active_weight_sum

        positives: list[str] = ["Target-campaign evidence excluded before feature aggregation."]
        cautions: list[str] = []
        if components["audience_gender_fit"] is not None:
            positives.append(f"Audience-gender evidence fit score {components['audience_gender_fit']:.1f}/100.")
        if components["audience_age_fit"] is not None:
            positives.append(f"Audience-age evidence fit score {components['audience_age_fit']:.1f}/100.")
        for field, label in (
            ("theme_experience_fit", "theme"),
            ("persona_experience_fit", "persona-requirement"),
            ("content_style_experience_fit", "content-style"),
        ):
            value = components[field]
            if value is not None and value > 0:
                positives.append(f"Historical {label} exposure covers {value:.1f}% of target tags.")
            elif value == 0:
                cautions.append(f"No non-target historical {label} exposure matched the target tags.")
        if budget_cap is None:
            cautions.append("Per-influencer budget eligibility not applied because target budget scope is not governed as individual.")
        elif fee is None:
            cautions.append("No non-target exact fee history; budget score uses neutral missing-evidence value.")
        if parse_int(feature.get("audience_gender_observation_count_ex_target")) == 0:
            cautions.append("No non-target audience-gender evidence; neutral missing-evidence score used.")
        if parse_int(feature.get("audience_age_observation_count_ex_target")) == 0:
            cautions.append("No non-target audience-age evidence; neutral missing-evidence score used.")
        if parse_int(feature.get("campaign_history_dq_warn_count_ex_target")) > 0:
            cautions.append("Non-target campaign-history DQ warning exists and lowers data confidence.")

        records.append({
            "scenario_id": f"replay_{target_requirement.get('campaign_id')}_matching_v2",
            "config_version": config.config_version,
            "target_campaign_id": target_requirement.get("campaign_id", ""),
            "target_campaign_display_name": target_requirement.get("campaign_display_name", ""),
            "target_brand_id": target_requirement.get("brand_id", ""),
            "target_platform": target_requirement.get("platform", ""),
            "influencer_id": iid,
            "canonical_handle": feature.get("canonical_handle", ""),
            "eligibility_status": "eligible" if not reasons else "ineligible",
            "eligibility_reasons": ";".join(reasons),
            "active_weight_sum": active_weight_sum,
            "audience_gender_fit_score": components["audience_gender_fit"],
            "audience_age_fit_score": components["audience_age_fit"],
            "theme_experience_fit_score": components["theme_experience_fit"],
            "persona_experience_fit_score": components["persona_experience_fit"],
            "content_style_experience_fit_score": components["content_style_experience_fit"],
            "historical_experience_score": components["historical_experience"],
            "cross_brand_experience_score": components["cross_brand_experience"],
            "selection_history_score": components["selection_history"],
            "view_performance_score": components["view_performance"],
            "budget_headroom_score": components["budget_headroom"],
            "operational_reliability_score": components["operational_reliability"],
            "data_confidence_score": components["data_confidence"],
            "total_score": weighted_total,
            "rank": None,
            "budget_eligibility_applied": budget_cap is not None,
            "target_individual_budget_cap": budget_cap,
            "fee_observed_median_ex_target": fee,
            "campaign_count_ex_target": feature.get("campaign_count_ex_target", 0),
            "brand_count_ex_target": feature.get("brand_count_ex_target", 0),
            "views_median_ex_target": feature.get("views_median_ex_target"),
            "audience_gender_dominant_ex_target": feature.get("audience_gender_dominant_ex_target", "unknown"),
            "audience_age_dominant_band_ex_target": feature.get("audience_age_dominant_band_ex_target", ""),
            "positive_reasons": " | ".join(positives),
            "cautions": " | ".join(cautions),
            "leakage_guard_status": "PASS",
            "matching_version": "v2",
        })

    eligible = [row for row in records if row["eligibility_status"] == "eligible"]
    eligible.sort(key=lambda row: (-float(row["total_score"]), str(row["canonical_handle"]), str(row["influencer_id"])))
    for rank, row in enumerate(eligible, start=1):
        row["rank"] = rank

    run = {
        "scenario_id": f"replay_{target_requirement.get('campaign_id')}_matching_v2",
        "config_version": config.config_version,
        "scenario_type": "historical_replay_leakage_guarded",
        "target_campaign_id": target_requirement.get("campaign_id", ""),
        "target_campaign_display_name": target_requirement.get("campaign_display_name", ""),
        "target_brand_id": target_requirement.get("brand_id", ""),
        "fit_readiness": target_requirement.get("fit_readiness", ""),
        "normalization_confidence": target_requirement.get("normalization_confidence", ""),
        "budget_scope": budget_scope,
        "budget_eligibility_applied": budget_cap is not None,
        "target_individual_budget_cap": budget_cap,
        "candidate_input_rows": len(records),
        "eligible_candidates": len(eligible),
        "ineligible_candidates": len(records) - len(eligible),
        "shortlist_size": min(config.shortlist_size, len(eligible)),
        "active_weight_sum": active_weight_sum,
        "machine_learning": False,
        "fuzzy_identity_resolution": False,
        "target_campaign_leakage": "forbidden",
        "matching_version": "v2",
    }
    return records, run
