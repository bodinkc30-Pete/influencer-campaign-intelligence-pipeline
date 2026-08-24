from src.build_resolved_candidate_observations import alias_hash_map


def test_alias_hash_map_reconciles_many_aliases_to_one_observation():
    rows = [
        {"source_row_hash": "h1", "influencer_id": "inf_1"},
        {"source_row_hash": "h1", "influencer_id": "inf_1"},
    ]
    assert alias_hash_map(rows) == {"h1": "inf_1"}


def test_alias_hash_map_rejects_one_source_row_mapped_to_two_influencers():
    rows = [
        {"source_row_hash": "h1", "influencer_id": "inf_1"},
        {"source_row_hash": "h1", "influencer_id": "inf_2"},
    ]
    try:
        alias_hash_map(rows)
    except ValueError as exc:
        assert "multiple influencers" in str(exc)
    else:
        raise AssertionError("expected ValueError")
