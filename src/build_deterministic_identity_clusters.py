from __future__ import annotations

import argparse
import csv
import hashlib
from collections import defaultdict
from pathlib import Path


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open('r', encoding='utf-8-sig', newline='') as file_obj:
        return list(csv.DictReader(file_obj))


def cluster_id(platform: str, handle: str) -> str:
    digest = hashlib.sha256(f'{platform.casefold()}|{handle.casefold()}'.encode('utf-8')).hexdigest()[:16]
    return f'icl_{digest}'


def build_clusters(rows: list[dict[str, str]], platform: str = 'tiktok') -> list[dict[str, object]]:
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        handle = row.get('canonical_handle_candidate', '').strip().casefold()
        if not handle:
            raise ValueError('accepted observation is missing canonical_handle_candidate')
        groups[handle].append(row)

    output: list[dict[str, object]] = []
    for handle, group in sorted(groups.items()):
        workbooks = sorted({row.get('source_filename', '') for row in group})
        sheets = sorted({f"{row.get('source_filename','')}::{row.get('source_sheet_name','')}" for row in group})
        source_rows = sorted(
            {
                f"{row.get('source_filename','')} | {row.get('source_sheet_name','')} | row {row.get('source_row_number','')}"
                for row in group
            }
        )
        dq_statuses = sorted({row.get('dq_status', '') for row in group if row.get('dq_status', '')})
        output.append(
            {
                'identity_cluster_id': cluster_id(platform, handle),
                'platform': platform,
                'canonical_handle_candidate': handle,
                'observation_count': len(group),
                'workbook_count': len(workbooks),
                'sheet_count': len(sheets),
                'source_workbooks': ' || '.join(workbooks),
                'source_occurrences': ' || '.join(source_rows),
                'source_dq_statuses': ';'.join(dq_statuses),
                'promotion_status': 'eligible_for_reviewed_master_promotion',
            }
        )
    return output


def reconcile(rows: list[dict[str, str]], clusters: list[dict[str, object]]) -> dict[str, int]:
    observation_count = len(rows)
    clustered_observations = sum(int(row['observation_count']) for row in clusters)
    unique_handles = len({row.get('canonical_handle_candidate', '').strip().casefold() for row in rows if row.get('canonical_handle_candidate', '').strip()})
    cross_workbook_clusters = sum(1 for row in clusters if int(row['workbook_count']) > 1)
    return {
        'input_observations': observation_count,
        'clustered_observations': clustered_observations,
        'identity_clusters': len(clusters),
        'unique_handles': unique_handles,
        'cross_workbook_clusters': cross_workbook_clusters,
    }


def write_csv(rows: list[dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError('identity cluster output is empty')
    with path.open('w', encoding='utf-8-sig', newline='') as file_obj:
        writer = csv.DictWriter(file_obj, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description='Build deterministic exact-handle identity clusters from accepted observations.')
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    rows = read_csv(args.input)
    clusters = build_clusters(rows)
    stats = reconcile(rows, clusters)
    if stats['input_observations'] != stats['clustered_observations'] or stats['identity_clusters'] != stats['unique_handles']:
        raise SystemExit(f'reconciliation failed: {stats}')
    write_csv(clusters, args.output)
    print(' '.join(f'{key}={value}' for key, value in stats.items()))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
