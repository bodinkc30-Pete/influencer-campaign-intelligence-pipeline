from src.validate_identity_review_decisions import summarize, validate_row


def base_row() -> dict[str, str]:
    return {
        'review_id': 'review_1',
        'decision': '',
        'resolved_handle': '',
        'decision_evidence': '',
        'normalized_handle_candidates': 'creator_a;creator_b',
    }


def codes(row: dict[str, str]) -> set[str]:
    return {error.code for error in validate_row(row)}


def test_blank_decision_is_unresolved():
    assert 'REVIEW_UNRESOLVED' in codes(base_row())


def test_merge_decision_requires_observed_handle_and_evidence():
    row = base_row()
    row.update({'decision': 'same_identity_use_handle', 'resolved_handle': 'creator_a'})
    assert 'REVIEW_EVIDENCE_REQUIRED' in codes(row)

    row['decision_evidence'] = 'verified profile URL'
    assert not codes(row)


def test_unobserved_resolved_handle_is_rejected():
    row = base_row()
    row.update(
        {
            'decision': 'alias_confirmed',
            'resolved_handle': 'creator_c',
            'decision_evidence': 'manual check',
        }
    )
    assert 'REVIEW_RESOLVED_HANDLE_NOT_OBSERVED' in codes(row)


def test_different_identity_cannot_have_single_resolved_handle():
    row = base_row()
    row.update(
        {
            'decision': 'different_identity_keep_separate',
            'resolved_handle': 'creator_a',
            'decision_evidence': 'profiles differ',
        }
    )
    assert 'REVIEW_SINGLE_HANDLE_NOT_ALLOWED' in codes(row)


def test_insufficient_evidence_stays_unresolved_without_handle_but_requires_reason():
    row = base_row()
    row.update({'decision': 'insufficient_evidence'})
    assert 'REVIEW_EVIDENCE_REQUIRED' in codes(row)
    row['decision_evidence'] = 'no authoritative profile evidence'
    assert not codes(row)


def test_summary_separates_blank_quarantine_and_promotable():
    rows = [
        {**base_row(), 'decision': ''},
        {**base_row(), 'decision': 'insufficient_evidence', 'decision_evidence': 'not enough evidence'},
        {
            **base_row(),
            'decision': 'same_identity_use_handle',
            'resolved_handle': 'creator_a',
            'decision_evidence': 'profile URL',
        },
    ]
    assert summarize(rows) == {
        'review_groups': 3,
        'blank_groups': 1,
        'quarantined_groups': 1,
        'promotable_groups': 1,
    }
