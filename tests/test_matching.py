import copy

import pytest

from src.matching import load_config, rank_candidates


BASE_CONFIG = {
    "config_version": "matching-v1",
    "scenario_id": "test",
    "scenario_type": "synthetic_portfolio_demo",
    "scenario_name": "test scenario",
    "platform": "tiktok",
    "max_fee": 3000,
    "require_fee_history": True,
    "minimum_campaign_count": 1,
    "reject_campaign_history_dq_warn": False,
    "shortlist_size": 10,
    "neutral_missing_score": 50,
    "caps": {"campaign_count": 5, "brand_count": 3},
    "weights": {
        "historical_experience": 0.15,
        "cross_brand_experience": 0.10,
        "selection_history": 0.15,
        "view_performance": 0.20,
        "budget_headroom": 0.15,
        "operational_reliability": 0.10,
        "data_confidence": 0.15,
    },
    "guardrails": {
        "machine_learning": False,
        "fuzzy_identity_resolution": False,
        "category_fit_enabled": False,
        "persona_fit_enabled": False,
        "audience_fit_enabled": False,
        "recency_enabled": False,
    },
}


def row(influencer_id, handle, fee="2000", campaigns="2", brands="2", selected_rate="0.5", views="1000", post=True, dq="0"):
    return {
        "influencer_id": influencer_id,
        "platform": "tiktok",
        "canonical_handle": handle,
        "identity_confidence": "deterministic_exact",
        "campaign_count": campaigns,
        "brand_count": brands,
        "selected_known_campaign_count": "2",
        "selected_rate": selected_rate,
        "campaign_history_dq_warn_count": dq,
        "fee_observed_median": fee,
        "views_record_count": "1" if views != "" else "0",
        "views_median": views,
        "posted_rate": "1" if post else "",
        "has_fee_history": "True" if fee != "" else "False",
        "has_performance_history": "True" if views != "" else "False",
        "has_post_history": "True" if post else "False",
    }


def test_config_weights_must_sum_to_one():
    bad = copy.deepcopy(BASE_CONFIG)
    bad["weights"]["data_confidence"] = 0.20
    with pytest.raises(ValueError):
        load_config(bad)


def test_v1_rejects_ml_or_fuzzy_guardrail():
    bad = copy.deepcopy(BASE_CONFIG)
    bad["guardrails"]["machine_learning"] = True
    with pytest.raises(ValueError):
        load_config(bad)


def test_fee_over_budget_is_ineligible():
    cfg = load_config(BASE_CONFIG)
    result = rank_candidates([row("1", "a", fee="3500")], cfg)[0]
    assert result["eligibility_status"] == "ineligible"
    assert "fee_over_budget" in result["eligibility_reasons"]


def test_unknown_fee_is_ineligible_when_required():
    cfg = load_config(BASE_CONFIG)
    result = rank_candidates([row("1", "a", fee="")], cfg)[0]
    assert result["eligibility_status"] == "ineligible"
    assert "fee_history_required" in result["eligibility_reasons"]


def test_missing_performance_still_scores_with_neutral_and_lower_confidence():
    cfg = load_config(BASE_CONFIG)
    scored = rank_candidates([row("1", "a", views=""), row("2", "b", views="5000")], cfg)
    a = next(r for r in scored if r["influencer_id"] == "1")
    b = next(r for r in scored if r["influencer_id"] == "2")
    assert a["view_performance_score"] == 50
    assert a["data_confidence_score"] < b["data_confidence_score"]
    assert "neutral view score" in a["cautions"]


def test_higher_view_evidence_gets_higher_view_score():
    cfg = load_config(BASE_CONFIG)
    scored = rank_candidates([row("1", "a", views="100"), row("2", "b", views="10000")], cfg)
    a = next(r for r in scored if r["influencer_id"] == "1")
    b = next(r for r in scored if r["influencer_id"] == "2")
    assert b["view_performance_score"] > a["view_performance_score"]


def test_ranking_is_deterministic_for_same_input_and_config():
    cfg = load_config(BASE_CONFIG)
    inputs = [row("1", "b", views="1000"), row("2", "a", views="1000")]
    first = rank_candidates(copy.deepcopy(inputs), cfg)
    second = rank_candidates(copy.deepcopy(inputs), cfg)
    assert [(r["influencer_id"], r["rank"]) for r in first] == [(r["influencer_id"], r["rank"]) for r in second]


def test_only_eligible_candidates_receive_rank():
    cfg = load_config(BASE_CONFIG)
    results = rank_candidates([row("1", "a", fee="2000"), row("2", "b", fee="4000")], cfg)
    eligible = next(r for r in results if r["influencer_id"] == "1")
    rejected = next(r for r in results if r["influencer_id"] == "2")
    assert eligible["rank"] == 1
    assert rejected["rank"] is None


def test_zero_fee_is_allowed_but_flagged_as_source_convention_caution():
    cfg = load_config(BASE_CONFIG)
    result = rank_candidates([row("1", "a", fee="0")], cfg)[0]
    assert result["eligibility_status"] == "eligible"
    assert result["budget_headroom_score"] == 100
    assert "source convention" in result["cautions"]
