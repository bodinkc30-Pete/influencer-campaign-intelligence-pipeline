from src.build_campaign_history import (
    build_history,
    build_registries,
    extract_requirement_rows,
    select_primary_budget,
)


def test_build_registries_one_campaign_per_source_sheet():
    mapping = [
        {
            "source_filename": "a.xlsx",
            "source_sheet_name": "Influencer Month 1",
            "canonical_brand_name": "Brand A",
            "campaign_period_label": "month_1",
        },
        {
            "source_filename": "a.xlsx",
            "source_sheet_name": "Influencer Month 2",
            "canonical_brand_name": "Brand A",
            "campaign_period_label": "month_2",
        },
    ]
    brands, campaigns, source_map = build_registries(mapping)
    assert len(brands) == 1
    assert len(campaigns) == 2
    assert len(source_map) == 2
    assert campaigns[0]["campaign_id"] != campaigns[1]["campaign_id"]


def test_requirement_extraction_does_not_inherit_and_prefers_influencer_budget():
    rows = [
        ["งบประมาณรวม 20,000 บาท"],
        ["Influencer TIKTOK (งบประมาณรวม 7,500 บาท)"],
        ["Persona Influencer", None, "self care"],
        ["Gender", "หญิง"],
        ["Influencer", "Follower", "BUDGET"],
    ]
    fields, budgets = extract_requirement_rows(rows, stop_before_row=5)
    assert fields["persona_raw"] == "self care"
    assert fields["target_gender_raw"] == "หญิง"
    amount, scope, _ = select_primary_budget(budgets)
    assert amount == 7500.0
    assert scope == "influencer_tiktok"


def test_history_preserves_duplicate_conflict_as_warning():
    campaign_map = [
        {
            "source_filename": "a.xlsx",
            "source_sheet_name": "Influencer",
            "canonical_brand_name": "Brand A",
        }
    ]
    _, _, source_map = build_registries(campaign_map)
    observations = [
        {
            "source_filename": "a.xlsx", "source_sheet_name": "Influencer", "source_row_number": "10",
            "source_row_hash": "h1", "influencer_id": "inf_1", "canonical_handle_candidate": "creator",
            "section_context_raw": "Nano", "follower_normalized": "1000", "engagement_normalized": "0.1",
            "fee_amount_normalized": "1500", "fee_model": "fixed", "fee_unit": "campaign",
            "historical_sales_normalized": "100", "audience_gender_raw": "female", "audience_age_raw": "25-34",
            "selected_raw": "True", "confirmed_raw": "", "pet_type_raw": "", "pii_present": "False",
            "dq_status": "PASS", "dq_codes": "", "identity_review_id": "", "identity_review_decision": "",
        },
        {
            "source_filename": "a.xlsx", "source_sheet_name": "Influencer", "source_row_number": "11",
            "source_row_hash": "h2", "influencer_id": "inf_1", "canonical_handle_candidate": "creator",
            "section_context_raw": "Nano", "follower_normalized": "1000", "engagement_normalized": "0.1",
            "fee_amount_normalized": "2500", "fee_model": "fixed", "fee_unit": "campaign",
            "historical_sales_normalized": "100", "audience_gender_raw": "female", "audience_age_raw": "25-34",
            "selected_raw": "False", "confirmed_raw": "", "pet_type_raw": "", "pii_present": "False",
            "dq_status": "PASS", "dq_codes": "", "identity_review_id": "", "identity_review_decision": "",
        },
    ]
    history, facts, stats = build_history(observations, source_map, {"inf_1"})
    assert len(history) == 2
    assert len(facts) == 1
    assert facts[0]["selected_status"] == "conflict"
    assert facts[0]["fee_status"] == "conflict"
    assert facts[0]["campaign_history_dq_status"] == "WARN"
    assert stats["duplicate_campaign_influencer_pairs"] == 1


def test_history_rejects_unmapped_observation_without_silent_guess():
    _, _, source_map = build_registries([
        {"source_filename": "a.xlsx", "source_sheet_name": "Influencer", "canonical_brand_name": "Brand A"}
    ])
    observation = {
        "source_filename": "other.xlsx", "source_sheet_name": "Influencer", "source_row_number": "2",
        "source_row_hash": "h", "influencer_id": "inf_1", "canonical_handle_candidate": "creator",
        "section_context_raw": "", "follower_normalized": "", "engagement_normalized": "",
        "fee_amount_normalized": "", "fee_model": "", "fee_unit": "", "historical_sales_normalized": "",
        "audience_gender_raw": "", "audience_age_raw": "", "selected_raw": "", "confirmed_raw": "",
        "pet_type_raw": "", "pii_present": "False", "dq_status": "PASS", "dq_codes": "",
        "identity_review_id": "", "identity_review_decision": "",
    }
    history, facts, stats = build_history([observation], source_map, {"inf_1"})
    assert history == []
    assert facts == []
    assert stats["unmapped_campaign_observations"] == 1


def test_bare_budget_header_does_not_borrow_number_from_adjacent_header():
    rows = [
        ["Influencer", "Follower", "BUDGET", "ยอดขายย้อนหลัง 30 วัน"],
        ["creator", 1000, 1500, 200],
    ]
    _, budgets = extract_requirement_rows(rows, stop_before_row=2)
    assert budgets == []


def test_campaign_summary_keeps_conflicts_visible():
    from src.build_campaign_history import build_campaign_summary
    campaigns = [{
        "campaign_id": "cmp_1", "brand_id": "brd_1", "campaign_display_name": "Brand | M1",
        "campaign_period_label": "M1", "candidate_sheet_name": "Influencer"
    }]
    requirements = [{
        "campaign_id": "cmp_1", "primary_candidate_budget_amount": 10000,
        "primary_budget_scope": "candidate_pool_unspecified", "requirement_status": "explicit_source_fields"
    }]
    facts = [
        {"campaign_id": "cmp_1", "observation_count": 1, "selected_status": "selected", "confirmed_status": "unknown", "campaign_history_dq_status": "PASS"},
        {"campaign_id": "cmp_1", "observation_count": 2, "selected_status": "conflict", "confirmed_status": "conflict", "campaign_history_dq_status": "WARN"},
    ]
    result = build_campaign_summary(campaigns, requirements, facts)
    assert result[0]["candidate_influencer_count"] == 2
    assert result[0]["source_observation_count"] == 3
    assert result[0]["selected_count"] == 1
    assert result[0]["selection_conflict_count"] == 1
    assert result[0]["dq_warn_pair_count"] == 1
