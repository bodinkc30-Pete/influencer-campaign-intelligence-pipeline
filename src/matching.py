from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class MatchingConfig:
    config_version: str
    scenario_id: str
    scenario_type: str
    scenario_name: str
    platform: str
    max_fee: float
    require_fee_history: bool
    minimum_campaign_count: int
    reject_campaign_history_dq_warn: bool
    shortlist_size: int
    neutral_missing_score: float
    campaign_count_cap: float
    brand_count_cap: float
    weights: dict[str, float]


REQUIRED_WEIGHT_KEYS = {
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


def load_config(data: dict[str, object]) -> MatchingConfig:
    weights = {str(k): float(v) for k, v in dict(data.get("weights") or {}).items()}
    if set(weights) != REQUIRED_WEIGHT_KEYS:
        missing = sorted(REQUIRED_WEIGHT_KEYS - set(weights))
        extra = sorted(set(weights) - REQUIRED_WEIGHT_KEYS)
        raise ValueError(f"Matching weight keys invalid; missing={missing}, extra={extra}")
    if not math.isclose(sum(weights.values()), 1.0, rel_tol=0, abs_tol=1e-9):
        raise ValueError("Matching weights must sum to 1.0")
    if any(v < 0 for v in weights.values()):
        raise ValueError("Matching weights cannot be negative")

    caps = dict(data.get("caps") or {})
    guardrails = dict(data.get("guardrails") or {})
    if guardrails.get("machine_learning") is not False:
        raise ValueError("Matching v1 does not allow machine learning")
    if guardrails.get("fuzzy_identity_resolution") is not False:
        raise ValueError("Matching v1 does not allow fuzzy identity resolution")

    max_fee = float(data.get("max_fee") or 0)
    if max_fee <= 0:
        raise ValueError("max_fee must be greater than zero")

    return MatchingConfig(
        config_version=str(data.get("config_version") or "matching-v1"),
        scenario_id=str(data.get("scenario_id") or ""),
        scenario_type=str(data.get("scenario_type") or ""),
        scenario_name=str(data.get("scenario_name") or ""),
        platform=str(data.get("platform") or "").casefold(),
        max_fee=max_fee,
        require_fee_history=bool(data.get("require_fee_history", True)),
        minimum_campaign_count=int(data.get("minimum_campaign_count") or 0),
        reject_campaign_history_dq_warn=bool(data.get("reject_campaign_history_dq_warn", False)),
        shortlist_size=int(data.get("shortlist_size") or 30),
        neutral_missing_score=float(data.get("neutral_missing_score") or 50.0),
        campaign_count_cap=float(caps.get("campaign_count") or 5),
        brand_count_cap=float(caps.get("brand_count") or 3),
        weights=weights,
    )


def _bounded_score(value: float, cap: float) -> float:
    if cap <= 0:
        return 0.0
    return max(0.0, min(100.0, (value / cap) * 100.0))


def _percentile_ranks(values_by_id: dict[str, float]) -> dict[str, float]:
    """Return deterministic percentile ranks from 0-100; ties get the same average rank."""
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


def _eligibility(row: dict[str, str], config: MatchingConfig) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if str(row.get("platform", "")).casefold() != config.platform:
        reasons.append("platform_mismatch")

    campaign_count = parse_int(row.get("campaign_count"))
    if campaign_count < config.minimum_campaign_count:
        reasons.append("insufficient_campaign_history")

    fee = parse_float(row.get("fee_observed_median"))
    if fee is None and config.require_fee_history:
        reasons.append("fee_history_required")
    elif fee is not None and fee > config.max_fee:
        reasons.append("fee_over_budget")

    if config.reject_campaign_history_dq_warn and parse_int(row.get("campaign_history_dq_warn_count")) > 0:
        reasons.append("campaign_history_dq_warn")

    return (len(reasons) == 0, reasons)


def _data_confidence(row: dict[str, str]) -> float:
    score = 0.0
    identity = str(row.get("identity_confidence", ""))
    score += 10.0 if identity == "deterministic_exact" else 8.0 if identity == "reviewed_evidence" else 0.0
    score += 20.0 if parse_int(row.get("selected_known_campaign_count")) > 0 else 0.0
    score += 20.0 if parse_bool(row.get("has_fee_history")) else 0.0
    score += 25.0 if parse_bool(row.get("has_performance_history")) else 0.0
    score += 15.0 if parse_bool(row.get("has_post_history")) else 0.0
    score += 10.0 if parse_int(row.get("campaign_history_dq_warn_count")) == 0 else 0.0
    return max(0.0, min(100.0, score))


def _candidate_components(
    row: dict[str, str],
    config: MatchingConfig,
    view_percentiles: dict[str, float],
) -> dict[str, float]:
    neutral = config.neutral_missing_score
    campaign_count = float(parse_int(row.get("campaign_count")))
    brand_count = float(parse_int(row.get("brand_count")))
    selected_rate = parse_float(row.get("selected_rate"))
    posted_rate = parse_float(row.get("posted_rate"))
    fee = parse_float(row.get("fee_observed_median"))

    return {
        "historical_experience": _bounded_score(campaign_count, config.campaign_count_cap),
        "cross_brand_experience": _bounded_score(brand_count, config.brand_count_cap),
        "selection_history": (selected_rate * 100.0) if selected_rate is not None else neutral,
        "view_performance": view_percentiles.get(str(row.get("influencer_id", "")), neutral),
        "budget_headroom": max(0.0, min(100.0, (1.0 - (fee / config.max_fee)) * 100.0)) if fee is not None else neutral,
        "operational_reliability": (posted_rate * 100.0) if posted_rate is not None else neutral,
        "data_confidence": _data_confidence(row),
    }


def _positive_reasons(row: dict[str, str], components: dict[str, float], config: MatchingConfig) -> list[str]:
    fee = parse_float(row.get("fee_observed_median"))
    reasons = [
        f"Observed in {parse_int(row.get('campaign_count'))} campaign source-instance(s) across {parse_int(row.get('brand_count'))} brand(s).",
    ]
    if parse_float(row.get("selected_rate")) is not None:
        reasons.append(f"Historical selected rate is {parse_float(row.get('selected_rate')) * 100:.1f}% over known selection outcomes.")
    if parse_int(row.get("views_record_count")) > 0:
        reasons.append(f"Content-view performance score is {components['view_performance']:.1f}/100 within the eligible population.")
    if fee is not None:
        reasons.append(f"Median observed fee {fee:,.0f} is within the configured {config.max_fee:,.0f} cap.")
    if parse_bool(row.get("has_post_history")):
        reasons.append("Has governed deliverable post-status evidence.")
    reasons.append(f"Data confidence score is {components['data_confidence']:.1f}/100.")
    return reasons


def _cautions(row: dict[str, str]) -> list[str]:
    cautions: list[str] = []
    if not parse_bool(row.get("has_performance_history")):
        cautions.append("No promoted influencer/content performance history; neutral view score used.")
    if not parse_bool(row.get("has_post_history")):
        cautions.append("No governed deliverable post-status history; neutral operational score used.")
    fee = parse_float(row.get("fee_observed_median"))
    if fee is not None and abs(fee) < 1e-12:
        cautions.append("Observed median fee is 0; this may represent free/barter or a source convention and is not guaranteed future zero-cost booking.")
    if parse_int(row.get("campaign_history_dq_warn_count")) > 0:
        cautions.append("Campaign-history DQ warning exists; retained as confidence evidence.")
    if str(row.get("identity_confidence", "")) == "reviewed_evidence":
        cautions.append("Identity was promoted through governed manual-review evidence rather than exact-only clustering.")
    return cautions


def rank_candidates(
    feature_rows: Iterable[dict[str, str]],
    config: MatchingConfig,
) -> list[dict[str, object]]:
    rows = [dict(r) for r in feature_rows]

    eligible_flags: dict[str, tuple[bool, list[str]]] = {}
    eligible_view_values: dict[str, float] = {}
    for row in rows:
        inf_id = str(row.get("influencer_id", ""))
        eligible, reasons = _eligibility(row, config)
        eligible_flags[inf_id] = (eligible, reasons)
        if eligible:
            views = parse_float(row.get("views_median"))
            if views is not None and views >= 0:
                eligible_view_values[inf_id] = math.log1p(views)
    view_percentiles = _percentile_ranks(eligible_view_values)

    results: list[dict[str, object]] = []
    for row in rows:
        inf_id = str(row.get("influencer_id", ""))
        eligible, rejection_reasons = eligible_flags[inf_id]
        components = _candidate_components(row, config, view_percentiles) if eligible else {}
        total_score = (
            sum(config.weights[name] * components[name] for name in REQUIRED_WEIGHT_KEYS)
            if eligible
            else None
        )
        positives = _positive_reasons(row, components, config) if eligible else []
        cautions = _cautions(row) if eligible else []
        results.append({
            "scenario_id": config.scenario_id,
            "config_version": config.config_version,
            "influencer_id": inf_id,
            "canonical_handle": row.get("canonical_handle", ""),
            "platform": row.get("platform", ""),
            "eligibility_status": "eligible" if eligible else "ineligible",
            "eligibility_reasons": " | ".join(rejection_reasons),
            "historical_experience_score": components.get("historical_experience"),
            "cross_brand_experience_score": components.get("cross_brand_experience"),
            "selection_history_score": components.get("selection_history"),
            "view_performance_score": components.get("view_performance"),
            "budget_headroom_score": components.get("budget_headroom"),
            "operational_reliability_score": components.get("operational_reliability"),
            "data_confidence_score": components.get("data_confidence"),
            "total_score": total_score,
            "rank": None,
            "fee_observed_median": parse_float(row.get("fee_observed_median")),
            "campaign_count": parse_int(row.get("campaign_count")),
            "brand_count": parse_int(row.get("brand_count")),
            "views_median": parse_float(row.get("views_median")),
            "positive_reasons": " | ".join(positives),
            "cautions": " | ".join(cautions),
            "matching_version": "v1",
        })

    eligible_rows = [r for r in results if r["eligibility_status"] == "eligible"]
    eligible_rows.sort(
        key=lambda r: (
            -(float(r["total_score"]) if r["total_score"] is not None else -1.0),
            -(float(r["data_confidence_score"]) if r["data_confidence_score"] is not None else -1.0),
            -(float(r["view_performance_score"]) if r["view_performance_score"] is not None else -1.0),
            float(r["fee_observed_median"]) if r["fee_observed_median"] is not None else float("inf"),
            str(r["canonical_handle"]),
            str(r["influencer_id"]),
        )
    )
    for index, row in enumerate(eligible_rows, start=1):
        row["rank"] = index

    results.sort(
        key=lambda r: (
            0 if r["eligibility_status"] == "eligible" else 1,
            int(r["rank"]) if r["rank"] is not None else 10**9,
            str(r["canonical_handle"]),
        )
    )
    return results
