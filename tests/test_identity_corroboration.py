from src.corroborate_identity_review import corroborate


def accepted(handle: str, workbook: str = 'other.xlsx') -> dict[str, str]:
    return {
        'canonical_handle_candidate': handle,
        'source_filename': workbook,
        'source_sheet_name': 'Influencer',
        'source_row_number': '10',
    }


def review(primary: str, secondary: str, candidates: str) -> dict[str, str]:
    return {
        'review_id': 'review_1',
        'review_type': 'identity_conflict',
        'identity_primary_raw': primary,
        'identity_secondary_raw': secondary,
        'normalized_handle_candidates': candidates,
        'auto_resolution_allowed': 'no',
    }


def test_independent_exact_handle_can_prepare_human_confirmation_without_auto_resolution():
    rows = corroborate(
        [review('bbymum', 'Baby (@bbymumi) | TikTok', 'bbymum;bbymumi')],
        [accepted('bbymumi')],
    )
    row = rows[0]
    assert row['corroborated_handle'] == 'bbymumi'
    assert row['evidence_consistency'] == 'supports_secondary_profile_handle'
    assert row['machine_recommendation'] == 'human_can_confirm_supported_handle'
    assert row['auto_resolution_allowed'] == 'no'


def test_support_for_primary_that_conflicts_with_embedded_profile_stays_manual():
    rows = corroborate(
        [review('youveneverseen', 'Yu (@youveneverseenn) | TikTok', 'youveneverseen;youveneverseenn')],
        [accepted('youveneverseen')],
    )
    row = rows[0]
    assert row['corroborated_handle'] == 'youveneverseen'
    assert row['evidence_consistency'] == 'supports_primary_but_conflicts_with_secondary_profile_handle'
    assert row['machine_recommendation'] == 'manual_review_required'


def test_no_independent_support_stays_manual():
    rows = corroborate(
        [review('a', 'Name (@b) | TikTok', 'a;b')],
        [],
    )
    assert rows[0]['corroboration_status'] == 'no_independent_exact_corroboration'
    assert rows[0]['corroborated_handle'] == ''


def test_unparsable_display_stays_manual():
    row = {
        'review_id': 'review_2',
        'review_type': 'identity_unparsable',
        'identity_primary_raw': 'ชื่อภาษาไทย',
        'identity_secondary_raw': '',
        'normalized_handle_candidates': '',
        'auto_resolution_allowed': 'no',
    }
    result = corroborate([row], [accepted('somebody')])[0]
    assert result['corroboration_status'] == 'no_candidate_handle'
    assert result['machine_recommendation'] == 'manual_review_required'
