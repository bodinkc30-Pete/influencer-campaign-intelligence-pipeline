from __future__ import annotations

import statistics
from collections import defaultdict
from typing import Iterable


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


def median_or_none(values: list[float]) -> float | None:
    return float(statistics.median(values)) if values else None


def known_bool(value: object | None) -> bool | None:
    text = str(value or "").strip().casefold()
    if text in {"true", "1", "yes", "y", "posted", "ลงแล้ว", "เรียบร้อย", "confirm", "confirmed"}:
        return True
    if text in {"false", "0", "no", "n", "not posted", "ยังไม่ลง", "not confirmed"}:
        return False
    return None


def _empty_feature(master: dict[str, str]) -> dict[str, object]:
    return {
        "influencer_id": master["influencer_id"],
        "platform": master.get("platform", ""),
        "canonical_handle": master.get("canonical_handle", ""),
        "identity_confidence": master.get("identity_confidence", ""),
        "master_workbook_count": int(float(master.get("workbook_count") or 0)),
        "campaign_count": 0,
        "brand_count": 0,
        "selected_campaign_count": 0,
        "selected_known_campaign_count": 0,
        "selected_rate": None,
        "confirmed_campaign_count": 0,
        "confirmed_known_campaign_count": 0,
        "confirmed_rate": None,
        "campaign_history_dq_warn_count": 0,
        "fee_known_campaign_count": 0,
        "fee_observed_min": None,
        "fee_observed_median": None,
        "fee_observed_max": None,
        "follower_observed_min": None,
        "follower_observed_median": None,
        "follower_observed_max": None,
        "engagement_observed_min": None,
        "engagement_observed_median": None,
        "engagement_observed_max": None,
        "deliverable_count": 0,
        "posted_known_deliverable_count": 0,
        "posted_deliverable_count": 0,
        "posted_rate": None,
        "performance_record_count": 0,
        "performance_campaign_count": 0,
        "views_record_count": 0,
        "views_total": 0.0,
        "views_average": None,
        "views_median": None,
        "views_max": None,
        "interaction_record_count": 0,
        "interactions_total": 0.0,
        "weighted_content_engagement_rate": None,
        "gmv_record_count": 0,
        "gmv_observed_median": None,
        "gmv_observed_max": None,
        "sales_record_count": 0,
        "sales_observed_median": None,
        "sales_observed_max": None,
        "orders_record_count": 0,
        "orders_observed_median": None,
        "orders_observed_max": None,
        "has_campaign_history": False,
        "has_performance_history": False,
        "has_fee_history": False,
        "has_post_history": False,
        "feature_version": "v1",
    }


def build_historical_features(
    masters: Iterable[dict[str, str]],
    campaign_facts: Iterable[dict[str, str]],
    campaign_registry: Iterable[dict[str, str]],
    deliverables: Iterable[dict[str, str]],
    performance: Iterable[dict[str, str]],
) -> list[dict[str, object]]:
    masters = list(masters)
    features = {m["influencer_id"]: _empty_feature(m) for m in masters}
    campaign_to_brand = {r["campaign_id"]: r.get("brand_id", "") for r in campaign_registry}

    campaign_sets: dict[str, set[str]] = defaultdict(set)
    brand_sets: dict[str, set[str]] = defaultdict(set)
    fee_values: dict[str, list[float]] = defaultdict(list)
    follower_values: dict[str, list[float]] = defaultdict(list)
    engagement_values: dict[str, list[float]] = defaultdict(list)

    for row in campaign_facts:
        inf_id = row.get("influencer_id", "")
        if inf_id not in features:
            continue
        f = features[inf_id]
        campaign_id = row.get("campaign_id", "")
        if campaign_id:
            campaign_sets[inf_id].add(campaign_id)
            brand_id = campaign_to_brand.get(campaign_id, "")
            if brand_id:
                brand_sets[inf_id].add(brand_id)

        selected = row.get("selected_status", "")
        if selected in {"selected", "not_selected"}:
            f["selected_known_campaign_count"] += 1
            if selected == "selected":
                f["selected_campaign_count"] += 1

        confirmed = row.get("confirmed_status", "")
        if confirmed in {"confirmed", "not_confirmed"}:
            f["confirmed_known_campaign_count"] += 1
            if confirmed == "confirmed":
                f["confirmed_campaign_count"] += 1

        if row.get("campaign_history_dq_status") == "WARN":
            f["campaign_history_dq_warn_count"] += 1

        if row.get("fee_status") == "consistent":
            lo = parse_float(row.get("fee_min"))
            hi = parse_float(row.get("fee_max"))
            if lo is not None and hi is not None and abs(lo - hi) < 1e-9:
                fee_values[inf_id].append(lo)

        for key in ("follower_snapshot_min", "follower_snapshot_max"):
            value = parse_float(row.get(key))
            if value is not None:
                follower_values[inf_id].append(value)
        for key in ("engagement_snapshot_min", "engagement_snapshot_max"):
            value = parse_float(row.get(key))
            if value is not None:
                engagement_values[inf_id].append(value)

    posted_known: dict[str, int] = defaultdict(int)
    posted_true: dict[str, int] = defaultdict(int)
    for row in deliverables:
        inf_id = row.get("influencer_id", "")
        if inf_id not in features:
            continue
        features[inf_id]["deliverable_count"] += 1
        state = known_bool(row.get("posted_raw"))
        if state is not None:
            posted_known[inf_id] += 1
            if state:
                posted_true[inf_id] += 1

    perf_campaigns: dict[str, set[str]] = defaultdict(set)
    view_values: dict[str, list[float]] = defaultdict(list)
    gmv_values: dict[str, list[float]] = defaultdict(list)
    sales_values: dict[str, list[float]] = defaultdict(list)
    order_values: dict[str, list[float]] = defaultdict(list)
    interaction_rows: dict[str, int] = defaultdict(int)
    interaction_totals: dict[str, float] = defaultdict(float)
    interaction_views: dict[str, float] = defaultdict(float)

    for row in performance:
        inf_id = row.get("influencer_id", "")
        if inf_id not in features:
            continue
        f = features[inf_id]
        f["performance_record_count"] += 1
        if row.get("campaign_id"):
            perf_campaigns[inf_id].add(row["campaign_id"])

        views = parse_float(row.get("views"))
        if views is not None:
            view_values[inf_id].append(views)

        interactions = []
        for key in ("likes", "comments", "saves", "shares"):
            value = parse_float(row.get(key))
            if value is not None:
                interactions.append(value)
        if views is not None and views > 0 and interactions:
            interaction_rows[inf_id] += 1
            interaction_totals[inf_id] += sum(interactions)
            interaction_views[inf_id] += views

        gmv = parse_float(row.get("gmv"))
        if gmv is not None:
            gmv_values[inf_id].append(gmv)
        sales = parse_float(row.get("sales_amount"))
        if sales is not None:
            sales_values[inf_id].append(sales)
        orders = parse_float(row.get("orders"))
        if orders is not None:
            order_values[inf_id].append(orders)

    for inf_id, f in features.items():
        f["campaign_count"] = len(campaign_sets[inf_id])
        f["brand_count"] = len(brand_sets[inf_id])
        known_sel = f["selected_known_campaign_count"]
        f["selected_rate"] = (f["selected_campaign_count"] / known_sel) if known_sel else None
        known_conf = f["confirmed_known_campaign_count"]
        f["confirmed_rate"] = (f["confirmed_campaign_count"] / known_conf) if known_conf else None

        fees = fee_values[inf_id]
        f["fee_known_campaign_count"] = len(fees)
        if fees:
            f["fee_observed_min"] = min(fees)
            f["fee_observed_median"] = median_or_none(fees)
            f["fee_observed_max"] = max(fees)

        followers = follower_values[inf_id]
        if followers:
            f["follower_observed_min"] = min(followers)
            f["follower_observed_median"] = median_or_none(followers)
            f["follower_observed_max"] = max(followers)

        engagements = engagement_values[inf_id]
        if engagements:
            f["engagement_observed_min"] = min(engagements)
            f["engagement_observed_median"] = median_or_none(engagements)
            f["engagement_observed_max"] = max(engagements)

        f["posted_known_deliverable_count"] = posted_known[inf_id]
        f["posted_deliverable_count"] = posted_true[inf_id]
        f["posted_rate"] = (posted_true[inf_id] / posted_known[inf_id]) if posted_known[inf_id] else None
        f["performance_campaign_count"] = len(perf_campaigns[inf_id])

        views = view_values[inf_id]
        f["views_record_count"] = len(views)
        if views:
            f["views_total"] = sum(views)
            f["views_average"] = sum(views) / len(views)
            f["views_median"] = median_or_none(views)
            f["views_max"] = max(views)

        f["interaction_record_count"] = interaction_rows[inf_id]
        f["interactions_total"] = interaction_totals[inf_id]
        if interaction_views[inf_id] > 0:
            f["weighted_content_engagement_rate"] = interaction_totals[inf_id] / interaction_views[inf_id]

        for prefix, values in (("gmv", gmv_values[inf_id]), ("sales", sales_values[inf_id]), ("orders", order_values[inf_id])):
            f[f"{prefix}_record_count"] = len(values)
            if values:
                f[f"{prefix}_observed_median"] = median_or_none(values)
                f[f"{prefix}_observed_max"] = max(values)

        f["has_campaign_history"] = bool(f["campaign_count"])
        f["has_performance_history"] = bool(f["performance_record_count"])
        f["has_fee_history"] = bool(f["fee_known_campaign_count"])
        f["has_post_history"] = bool(f["posted_known_deliverable_count"])

    return sorted(features.values(), key=lambda r: (str(r["canonical_handle"]), str(r["influencer_id"])))


FEATURE_CONTRACT = [
    ("campaign_count", "count", "Distinct campaign source-instances observed for the influencer.", "Campaign History", "Safe for reuse evidence; campaign names are technical source instances until business verification."),
    ("brand_count", "count", "Distinct brands observed through campaign history.", "Campaign History", "Brand registry names remain business-verification pending."),
    ("selected_rate", "ratio", "Selected campaigns / campaigns with known selected status.", "Campaign History", "Conflict/unknown selection states are excluded from the denominator."),
    ("fee_observed_median", "THB", "Median exact consistent fixed/free fee observed in candidate history.", "Campaign History", "Conflicting/range/unknown fees are not forced into a single amount."),
    ("follower_observed_median", "count", "Median observed follower snapshot across source campaign facts.", "Campaign History", "Not a recency-aware latest follower count."),
    ("engagement_observed_median", "source ratio", "Median source engagement snapshot.", "Campaign History", "Source engagement definitions may differ; do not compare as a universal KPI without metric definition alignment."),
    ("deliverable_count", "count", "Canonical content deliverables linked to the influencer.", "Deliverable History", "Only identity-resolved promoted deliverables are included."),
    ("posted_rate", "ratio", "Posted deliverables / deliverables with known post status.", "Deliverable History", "Unknown post states are excluded from denominator."),
    ("views_median", "count", "Median source-reported content views.", "Influencer Performance", "Does not mix campaign-level live viewers."),
    ("weighted_content_engagement_rate", "ratio", "Total known likes/comments/saves/shares divided by total views for rows with views and interaction evidence.", "Influencer Performance", "Calculated only from influencer/content records; not campaign ads/live metrics."),
    ("gmv_observed_median", "source currency", "Median source field explicitly labelled GMV.", "Influencer Performance", "GMV is not merged with revenue or generic sales_amount."),
    ("sales_observed_median", "source currency", "Median source field mapped to sales_amount.", "Influencer Performance", "Sales is not assumed equal to GMV or revenue."),
    ("campaign_history_dq_warn_count", "count", "Campaign×Influencer facts carrying DQ warnings.", "Campaign History DQ", "Used as confidence evidence, not as an automatic rejection rule."),
    ("identity_confidence", "categorical", "Golden Master identity confidence from deterministic or reviewed evidence.", "Golden Master", "No fuzzy auto-merge is used."),
]
