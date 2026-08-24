from src.historical_features import build_historical_features, known_bool, parse_float


def fixture_features():
    masters = [
        {"influencer_id": "inf_1", "platform": "tiktok", "canonical_handle": "creator.one", "identity_confidence": "deterministic_exact", "workbook_count": "2"},
        {"influencer_id": "inf_2", "platform": "tiktok", "canonical_handle": "creator.two", "identity_confidence": "reviewed_evidence", "workbook_count": "1"},
    ]
    registry = [
        {"campaign_id": "cmp_1", "brand_id": "brd_a"},
        {"campaign_id": "cmp_2", "brand_id": "brd_b"},
    ]
    campaign_facts = [
        {"campaign_id": "cmp_1", "influencer_id": "inf_1", "selected_status": "selected", "confirmed_status": "confirmed", "campaign_history_dq_status": "PASS", "fee_status": "consistent", "fee_min": "1500", "fee_max": "1500", "follower_snapshot_min": "10000", "follower_snapshot_max": "10000", "engagement_snapshot_min": "0.10", "engagement_snapshot_max": "0.10"},
        {"campaign_id": "cmp_2", "influencer_id": "inf_1", "selected_status": "not_selected", "confirmed_status": "unknown", "campaign_history_dq_status": "WARN", "fee_status": "consistent", "fee_min": "2500", "fee_max": "2500", "follower_snapshot_min": "12000", "follower_snapshot_max": "12000", "engagement_snapshot_min": "0.12", "engagement_snapshot_max": "0.12"},
    ]
    deliverables = [
        {"influencer_id": "inf_1", "posted_raw": "True"},
        {"influencer_id": "inf_1", "posted_raw": "False"},
    ]
    performance = [
        {"influencer_id": "inf_1", "campaign_id": "cmp_1", "views": "1000", "likes": "50", "comments": "10", "saves": "5", "shares": "5", "gmv": "5000", "sales_amount": "", "orders": "10"},
        {"influencer_id": "inf_1", "campaign_id": "cmp_2", "views": "3000", "likes": "120", "comments": "20", "saves": "10", "shares": "10", "gmv": "9000", "sales_amount": "7000", "orders": "20"},
    ]
    return build_historical_features(masters, campaign_facts, registry, deliverables, performance)


def test_number_and_bool_guards():
    assert parse_float("1,500") == 1500
    assert parse_float("#DIV/0!") is None
    assert known_bool("True") is True
    assert known_bool("") is None


def test_one_row_per_master_and_zero_history_preserved():
    rows = fixture_features()
    assert len(rows) == 2
    no_history = next(r for r in rows if r["influencer_id"] == "inf_2")
    assert no_history["campaign_count"] == 0
    assert no_history["has_performance_history"] is False


def test_campaign_reuse_and_fee_features():
    row = next(r for r in fixture_features() if r["influencer_id"] == "inf_1")
    assert row["campaign_count"] == 2
    assert row["brand_count"] == 2
    assert row["selected_rate"] == 0.5
    assert row["fee_observed_median"] == 2000
    assert row["campaign_history_dq_warn_count"] == 1


def test_deliverable_and_performance_features_do_not_mix_live_metrics():
    row = next(r for r in fixture_features() if r["influencer_id"] == "inf_1")
    assert row["deliverable_count"] == 2
    assert row["posted_rate"] == 0.5
    assert row["views_total"] == 4000
    assert row["views_median"] == 2000
    assert row["gmv_observed_median"] == 7000
    expected = (70 + 160) / 4000
    assert abs(row["weighted_content_engagement_rate"] - expected) < 1e-12
