from src.build_identity_review_queue import build_queue


def test_repeated_conflict_is_one_review_group():
    rows = [
        {
            "dq_codes": "DQ_IDENTITY_CONFLICT",
            "normalized_handle_candidates": "a;b",
            "identity_primary_raw": "a",
            "identity_secondary_raw": "Name (@b) | TikTok",
            "source_filename": "one.xlsx",
            "source_sheet_name": "Influencer",
            "source_row_number": "10",
        },
        {
            "dq_codes": "DQ_IDENTITY_CONFLICT",
            "normalized_handle_candidates": "b;a",
            "identity_primary_raw": "a",
            "identity_secondary_raw": "Name (@b) | TikTok",
            "source_filename": "two.xlsx",
            "source_sheet_name": "Influencer",
            "source_row_number": "20",
        },
    ]
    queue = build_queue(rows)
    assert len(queue) == 1
    assert queue[0]["occurrence_count"] == 2
    assert queue[0]["decision"] == ""
