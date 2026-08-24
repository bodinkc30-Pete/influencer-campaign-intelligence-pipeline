import pytest

from src.matching_v2 import (
    _age_overlap_score,
    _gender_fit_score,
    _tag_coverage_score,
    build_target_excluded_context,
    load_v2_config,
    score_target_campaign,
)


def cfg():
    return {
        "config_version": "matching-v2",
        "shortlist_size": 2,
        "neutral_missing_score": 50.0,
        "caps": {"campaign_count": 5, "brand_count": 3},
        "individual_budget_scopes": ["influencer_tiktok"],
        "weights": {
            "audience_gender_fit": 0.10,
            "audience_age_fit": 0.10,
            "theme_experience_fit": 0.12,
            "persona_experience_fit": 0.08,
            "content_style_experience_fit": 0.05,
            "historical_experience": 0.08,
            "cross_brand_experience": 0.05,
            "selection_history": 0.08,
            "view_performance": 0.12,
            "budget_headroom": 0.05,
            "operational_reliability": 0.05,
            "data_confidence": 0.12,
        },
        "guardrails": {
            "machine_learning": False,
            "fuzzy_identity_resolution": False,
            "target_campaign_leakage": "forbidden",
            "automatic_requirement_inheritance": False,
        },
    }


def test_v2_config_requires_weights_sum_to_one():
    data = cfg()
    data["weights"]["data_confidence"] = 0.50
    with pytest.raises(ValueError):
        load_v2_config(data)


def test_v2_config_requires_leakage_guard():
    data = cfg()
    data["guardrails"]["target_campaign_leakage"] = "allowed"
    with pytest.raises(ValueError):
        load_v2_config(data)


def test_age_overlap_uses_band_overlap():
    assert _age_overlap_score(25, 40, "25-34", 50.0) == 100.0
    assert _age_overlap_score(18, 28, "25-34", 50.0) == pytest.approx(40.0)


def test_gender_fit_all_accepts_any_observed_gender():
    req = {"target_gender_mode": "all"}
    assert _gender_fit_score(req, "male", 1, 50.0) == 100.0


def test_gender_fit_missing_evidence_is_neutral():
    req = {"target_gender_mode": "female_only"}
    assert _gender_fit_score(req, "unknown", 0, 50.0) == 50.0


def test_tag_coverage_is_target_coverage_not_fuzzy_similarity():
    assert _tag_coverage_score("skin_care;clinic_aesthetic", {"skin_care"}) == 50.0
    assert _tag_coverage_score("skin_care", {"hair_care"}) == 0.0


def test_target_campaign_rows_are_excluded_before_aggregation():
    masters = [{"influencer_id": "i1", "canonical_handle": "abc", "platform": "tiktok", "identity_confidence": "deterministic_exact"}]
    facts = [
        {"campaign_id": "target", "influencer_id": "i1", "selected_status": "selected", "campaign_history_dq_status": "PASS", "fee_status": "consistent", "fee_min": "100", "fee_max": "100"},
        {"campaign_id": "prior", "influencer_id": "i1", "selected_status": "not_selected", "campaign_history_dq_status": "PASS", "fee_status": "consistent", "fee_min": "200", "fee_max": "200"},
    ]
    registry = [{"campaign_id": "target", "brand_id": "b1"}, {"campaign_id": "prior", "brand_id": "b2"}]
    reqs = {
        "target": {"campaign_theme_tags": "skin_care", "persona_tags": "self_care", "content_style_tags": "real_review"},
        "prior": {"campaign_theme_tags": "hair_care", "persona_tags": "office_worker", "content_style_tags": "vlog"},
    }
    observations = [
        {"campaign_id": "target", "influencer_id": "i1", "audience_gender_raw": "female", "audience_age_raw": "25-34"},
        {"campaign_id": "prior", "influencer_id": "i1", "audience_gender_raw": "male", "audience_age_raw": "18-24"},
    ]
    context, audit = build_target_excluded_context("target", masters, facts, registry, [], [], observations, reqs)
    assert context["i1"]["campaign_count_ex_target"] == 1
    assert context["i1"]["selected_rate_ex_target"] == 0.0
    assert context["i1"]["fee_observed_median_ex_target"] == 200.0
    assert context["i1"]["audience_gender_dominant_ex_target"] == "male"
    assert context["i1"]["theme_experience_tags_ex_target"] == "hair_care"
    assert audit["excluded_campaign_fact_rows"] == 1
    assert audit["target_campaign_rows_used_in_score"] == 0


def test_campaign_total_does_not_become_individual_fee_cap():
    config = load_v2_config(cfg())
    req = {
        "campaign_id": "target", "campaign_display_name": "T", "brand_id": "b1", "platform": "tiktok",
        "fit_readiness": "ready_for_rule_based_fit", "normalization_confidence": "high", "target_gender_mode": "all",
        "target_age_min": "18", "target_age_max": "40", "campaign_theme_tags": "skin_care", "persona_tags": "", "content_style_tags": "",
    }
    context = {"i1": {"canonical_handle": "a", "platform": "tiktok", "identity_confidence": "deterministic_exact", "fee_observed_median_ex_target": 99999, "campaign_count_ex_target": 1, "brand_count_ex_target": 1, "selected_known_count_ex_target": 0, "selected_rate_ex_target": None, "campaign_history_dq_warn_count_ex_target": 0, "fee_history_count_ex_target": 1, "posted_rate_ex_target": None, "posted_known_count_ex_target": 0, "performance_record_count_ex_target": 0, "views_median_ex_target": None, "view_percentile_ex_target": None, "audience_gender_observation_count_ex_target": 0, "audience_gender_dominant_ex_target": "unknown", "audience_age_observation_count_ex_target": 0, "audience_age_dominant_band_ex_target": "", "theme_experience_tags_ex_target": "", "persona_experience_tags_ex_target": "", "content_style_experience_tags_ex_target": ""}}
    rows, run = score_target_campaign(req, {"primary_candidate_budget_amount": "1000", "primary_budget_scope": "campaign_total"}, context, config)
    assert rows[0]["eligibility_status"] == "eligible"
    assert rows[0]["budget_eligibility_applied"] is False
    assert run["budget_eligibility_applied"] is False


def test_explicit_individual_budget_can_reject_fee_over_cap():
    config = load_v2_config(cfg())
    req = {
        "campaign_id": "target", "campaign_display_name": "T", "brand_id": "b1", "platform": "tiktok",
        "fit_readiness": "ready_for_rule_based_fit", "normalization_confidence": "high", "target_gender_mode": "all",
        "target_age_min": "18", "target_age_max": "40", "campaign_theme_tags": "skin_care", "persona_tags": "", "content_style_tags": "",
    }
    context = {"i1": {"canonical_handle": "a", "platform": "tiktok", "identity_confidence": "deterministic_exact", "fee_observed_median_ex_target": 2000, "campaign_count_ex_target": 1, "brand_count_ex_target": 1, "selected_known_count_ex_target": 0, "selected_rate_ex_target": None, "campaign_history_dq_warn_count_ex_target": 0, "fee_history_count_ex_target": 1, "posted_rate_ex_target": None, "posted_known_count_ex_target": 0, "performance_record_count_ex_target": 0, "views_median_ex_target": None, "view_percentile_ex_target": None, "audience_gender_observation_count_ex_target": 0, "audience_gender_dominant_ex_target": "unknown", "audience_age_observation_count_ex_target": 0, "audience_age_dominant_band_ex_target": "", "theme_experience_tags_ex_target": "", "persona_experience_tags_ex_target": "", "content_style_experience_tags_ex_target": ""}}
    rows, _run = score_target_campaign(req, {"primary_candidate_budget_amount": "1000", "primary_budget_scope": "influencer_tiktok"}, context, config)
    assert rows[0]["eligibility_status"] == "ineligible"
    assert rows[0]["eligibility_reasons"] == "fee_over_explicit_individual_budget"
    assert rows[0]["rank"] is None


def test_missing_target_dimension_is_removed_from_active_weight_sum():
    config = load_v2_config(cfg())
    req = {
        "campaign_id": "target", "campaign_display_name": "T", "brand_id": "b1", "platform": "tiktok",
        "fit_readiness": "ready_for_rule_based_fit", "normalization_confidence": "high", "target_gender_mode": "all",
        "target_age_min": "18", "target_age_max": "40", "campaign_theme_tags": "skin_care", "persona_tags": "", "content_style_tags": "",
    }
    context = {"i1": {"canonical_handle": "a", "platform": "tiktok", "identity_confidence": "deterministic_exact", "fee_observed_median_ex_target": None, "campaign_count_ex_target": 0, "brand_count_ex_target": 0, "selected_known_count_ex_target": 0, "selected_rate_ex_target": None, "campaign_history_dq_warn_count_ex_target": 0, "fee_history_count_ex_target": 0, "posted_rate_ex_target": None, "posted_known_count_ex_target": 0, "performance_record_count_ex_target": 0, "views_median_ex_target": None, "view_percentile_ex_target": None, "audience_gender_observation_count_ex_target": 0, "audience_gender_dominant_ex_target": "unknown", "audience_age_observation_count_ex_target": 0, "audience_age_dominant_band_ex_target": "", "theme_experience_tags_ex_target": "", "persona_experience_tags_ex_target": "", "content_style_experience_tags_ex_target": ""}}
    _rows, run = score_target_campaign(req, {}, context, config)
    assert run["active_weight_sum"] == pytest.approx(1.0 - 0.08 - 0.05 - 0.05)


def test_eligible_ranking_is_deterministic_and_ineligible_unranked():
    config = load_v2_config(cfg())
    req = {
        "campaign_id": "target", "campaign_display_name": "T", "brand_id": "b1", "platform": "tiktok",
        "fit_readiness": "ready_for_rule_based_fit", "normalization_confidence": "high", "target_gender_mode": "all",
        "target_age_min": "18", "target_age_max": "40", "campaign_theme_tags": "skin_care", "persona_tags": "", "content_style_tags": "",
    }
    base = {"platform": "tiktok", "identity_confidence": "deterministic_exact", "fee_observed_median_ex_target": None, "campaign_count_ex_target": 1, "brand_count_ex_target": 1, "selected_known_count_ex_target": 0, "selected_rate_ex_target": None, "campaign_history_dq_warn_count_ex_target": 0, "fee_history_count_ex_target": 0, "posted_rate_ex_target": None, "posted_known_count_ex_target": 0, "performance_record_count_ex_target": 0, "views_median_ex_target": None, "view_percentile_ex_target": None, "audience_gender_observation_count_ex_target": 0, "audience_gender_dominant_ex_target": "unknown", "audience_age_observation_count_ex_target": 0, "audience_age_dominant_band_ex_target": "", "theme_experience_tags_ex_target": "", "persona_experience_tags_ex_target": "", "content_style_experience_tags_ex_target": ""}
    context = {"i2": {**base, "canonical_handle": "b"}, "i1": {**base, "canonical_handle": "a"}}
    rows, _ = score_target_campaign(req, {}, context, config)
    ranked = sorted(rows, key=lambda r: int(r["rank"] or 999))
    assert [r["canonical_handle"] for r in ranked] == ["a", "b"]
