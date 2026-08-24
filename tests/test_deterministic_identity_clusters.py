from src.build_deterministic_identity_clusters import build_clusters, reconcile


def row(handle: str, workbook: str, row_number: str = '1') -> dict[str, str]:
    return {
        'canonical_handle_candidate': handle,
        'source_filename': workbook,
        'source_sheet_name': 'Influencer',
        'source_row_number': row_number,
        'dq_status': 'PASS',
    }


def test_exact_handle_observations_collapse_to_one_cluster():
    rows = [row('CreatorA', 'a.xlsx'), row('creatora', 'b.xlsx', '2')]
    clusters = build_clusters(rows)
    assert len(clusters) == 1
    assert clusters[0]['canonical_handle_candidate'] == 'creatora'
    assert clusters[0]['observation_count'] == 2
    assert clusters[0]['workbook_count'] == 2


def test_cluster_reconciliation_matches_input():
    rows = [row('a', 'one.xlsx'), row('b', 'one.xlsx'), row('a', 'two.xlsx')]
    stats = reconcile(rows, build_clusters(rows))
    assert stats['input_observations'] == 3
    assert stats['clustered_observations'] == 3
    assert stats['identity_clusters'] == 2
    assert stats['unique_handles'] == 2
    assert stats['cross_workbook_clusters'] == 1
