from src.enrich_identity_review_evidence import classify_evidence, enrich


def test_explicit_profile_url_is_high_strength_but_not_auto_resolution():
    row = {
        'review_type': 'identity_conflict',
        'identity_secondary_raw': 'https://www.tiktok.com/@creator_two',
        'occurrence_count': '1',
    }
    evidence_type, strength, _ = classify_evidence(row)
    assert evidence_type == 'explicit_tiktok_profile_url_conflict'
    assert strength == 'high'
    enriched = enrich([row])[0]
    assert enriched['auto_resolution_allowed'] == 'no'


def test_embedded_profile_handle_is_medium_strength():
    row = {
        'review_type': 'identity_conflict',
        'identity_secondary_raw': 'Display Name (@creator_two) | TikTok',
        'occurrence_count': '2',
    }
    evidence_type, strength, _ = classify_evidence(row)
    assert evidence_type == 'embedded_tiktok_profile_handle_conflict'
    assert strength == 'medium'
    assert enrich([row])[0]['cross_occurrence_evidence'] == 'yes'


def test_plain_text_conflict_is_low_strength():
    evidence_type, strength, _ = classify_evidence(
        {
            'review_type': 'identity_conflict',
            'identity_secondary_raw': 'creator_typo',
        }
    )
    assert evidence_type == 'plain_text_handle_conflict'
    assert strength == 'low'


def test_unparsable_display_is_low_strength():
    evidence_type, strength, _ = classify_evidence(
        {
            'review_type': 'identity_unparsable',
            'identity_secondary_raw': '',
        }
    )
    assert evidence_type == 'display_only_unparsable'
    assert strength == 'low'
