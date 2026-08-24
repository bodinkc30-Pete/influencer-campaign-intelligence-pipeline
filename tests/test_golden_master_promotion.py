from src.promote_golden_master import (
    build_master,
    influencer_id_from_seed,
    split_reviewed_quarantine,
)


def accepted_row(handle: str, source: str = 'a.xlsx', row_number: str = '1') -> dict[str, str]:
    return {
        'source_filename': source,
        'source_sheet_name': 'Influencer',
        'source_row_number': row_number,
        'identity_primary_raw': handle,
        'identity_secondary_raw': f'@{handle}',
        'normalized_handle_candidates': handle,
        'canonical_handle_candidate': handle,
        'dq_status': 'PASS',
        'dq_codes': '',
        'source_row_hash': f'hash-{source}-{row_number}',
    }


def quarantine_row(primary: str, candidates: str, row_number: str = '2') -> dict[str, str]:
    return {
        'source_filename': 'q.xlsx',
        'source_sheet_name': 'Influencer',
        'source_row_number': row_number,
        'identity_primary_raw': primary,
        'identity_secondary_raw': '',
        'normalized_handle_candidates': candidates,
        'canonical_handle_candidate': '',
        'dq_status': 'ERROR',
        'dq_codes': 'DQ_IDENTITY_CONFLICT',
        'source_row_hash': f'qhash-{row_number}',
    }


def decision(review_id: str, candidates: str, action: str, handle: str = '') -> dict[str, str]:
    return {
        'review_id': review_id,
        'decision': action,
        'resolved_handle': handle,
        'decision_evidence': 'evidence present',
        'normalized_handle_candidates': candidates,
    }


def test_build_master_groups_exact_and_reviewed_observations():
    accepted = [accepted_row('creator_a')]
    reviewed = [
        {
            **accepted_row('creator_a', source='q.xlsx', row_number='2'),
            'identity_review_id': 'review_1',
            'identity_review_decision': 'same_identity_use_handle',
            'dq_status': 'REVIEWED_PASS',
        }
    ]
    master, aliases, stats = build_master(accepted, reviewed)
    assert len(master) == 1
    assert master[0]['canonical_handle'] == 'creator_a'
    assert master[0]['observation_count'] == 2
    assert master[0]['reviewed_observation_count'] == 1
    assert stats['golden_observations'] == 2
    assert aliases


def test_new_reviewed_handle_gets_master_without_accepted_cluster():
    reviewed = [
        {
            **accepted_row('creator_new', source='q.xlsx'),
            'identity_review_id': 'review_new',
            'identity_review_decision': 'same_identity_use_handle',
            'dq_status': 'REVIEWED_PASS',
        }
    ]
    master, _, _ = build_master([], reviewed)
    assert master[0]['identity_resolution_method'] == 'reviewed_direct_identity_evidence'
    assert master[0]['survivor_seed'] == 'review_new'
    assert master[0]['influencer_id'] == influencer_id_from_seed('review_new')


def test_insufficient_evidence_remains_quarantined():
    row = quarantine_row('creatorx', 'creatorx;creator_x')
    from src.build_identity_review_queue import make_review_id, review_key

    review_type, identity_key = review_key(row)
    review_id = make_review_id(review_type, identity_key)
    promoted, remaining, audit = split_reviewed_quarantine(
        [row],
        [decision(review_id, 'creatorx;creator_x', 'insufficient_evidence')],
    )
    assert promoted == []
    assert len(remaining) == 1
    assert audit[0]['group_action'] == 'remain_quarantined'


def test_resolved_review_is_promoted_to_observed_handle():
    row = quarantine_row('creatorx', 'creatorx;creator_x')
    from src.build_identity_review_queue import make_review_id, review_key

    review_type, identity_key = review_key(row)
    review_id = make_review_id(review_type, identity_key)
    promoted, remaining, _ = split_reviewed_quarantine(
        [row],
        [decision(review_id, 'creatorx;creator_x', 'same_identity_use_handle', 'creator_x')],
    )
    assert remaining == []
    assert promoted[0]['canonical_handle_candidate'] == 'creator_x'
    assert promoted[0]['dq_status'] == 'REVIEWED_PASS'
