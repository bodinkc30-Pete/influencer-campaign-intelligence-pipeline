from src.requirement_normalization import (
    age_overlap_score,
    build_audience_profiles,
    derive_tags,
    gender_fit_status,
    normalize_audience_age,
    normalize_audience_gender,
    normalize_platform,
    normalize_requirement_rows,
    normalize_target_gender,
    parse_age_range,
)


def test_platform_tiktok_is_deterministic():
    assert normalize_platform("TikTok") == ("tiktok", "exact_keyword")


def test_gender_both_is_all():
    out = normalize_target_gender("หญิง / ชาย")
    assert out["mode"] == "all"


def test_gender_percentages_are_preserved():
    out = normalize_target_gender("หญิง 70% / ชาย 30%")
    assert out["mode"] == "mixed_weighted"
    assert out["female_target_share"] == 0.7


def test_age_range_parses_dash_variants():
    assert parse_age_range("25–40 ปี")["age_min"] == 25
    assert parse_age_range("25–40 ปี")["age_max"] == 40


def test_age_range_rejects_bad_order():
    assert parse_age_range("40-20")["method"] == "invalid_range"


def test_audience_gender_detects_schema_shift():
    assert normalize_audience_gender("25-34")[0] == "invalid_age_in_gender"


def test_audience_age_detects_schema_shift():
    assert normalize_audience_age("ผู้หญิง")[2] == "schema_shift_detected"


def test_tag_derivation_is_exact_keyword_rule():
    tags, evidence = derive_tags("UGC diary real review", {"ugc": ["ugc"], "vlog": ["vlog"]})
    assert tags == ["ugc"]
    assert evidence


def test_requirement_missing_is_not_inherited():
    req = [{"campaign_id": "c1", "requirement_status": "tier_sections_only", "persona_raw": "", "target_content_raw": "", "content_style_raw": "", "pain_point_raw": "", "tier_sections_raw": "Nano", "target_gender_raw": "", "target_age_raw": "", "platform_raw": ""}]
    out, dq = normalize_requirement_rows(req, {"c1": {"campaign_display_name": "X", "brand_id": "b1"}})
    assert out[0]["fit_readiness"] == "insufficient_source_requirement"
    assert any(x["dq_code"] == "SOURCE_REQUIREMENT_MISSING" for x in dq)


def test_build_audience_profiles_excludes_shifted_values():
    rows = [
        {"influencer_id": "i1", "canonical_handle": "a", "audience_gender_raw": "ผู้หญิง", "audience_age_raw": "25-34"},
        {"influencer_id": "i1", "canonical_handle": "a", "audience_gender_raw": "25-34", "audience_age_raw": "ผู้หญิง"},
    ]
    profiles, dq = build_audience_profiles(rows)
    assert profiles[0]["audience_gender_female_count"] == 1
    assert profiles[0]["audience_age_observation_count"] == 1
    assert len(dq) == 2


def test_age_overlap_score_is_explainable():
    assert age_overlap_score(25, 40, "25-34") == 100.0
    assert age_overlap_score(25, 30, "18-24") == 0.0


def test_gender_fit_status():
    assert gender_fit_status("female_only", "female") == "match"
    assert gender_fit_status("female_only", "male") == "mismatch"
    assert gender_fit_status("all", "male") == "broad_target"
