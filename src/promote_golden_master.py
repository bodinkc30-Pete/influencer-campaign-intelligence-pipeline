from __future__ import annotations

import argparse
import csv
import hashlib
from collections import defaultdict
from pathlib import Path

from src.build_deterministic_identity_clusters import cluster_id
from src.build_identity_review_queue import make_review_id, review_key
from src.validate_identity_review_decisions import validate_rows


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open('r', encoding='utf-8-sig', newline='') as file_obj:
        return list(csv.DictReader(file_obj))


def write_csv(rows: list[dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError(f'cannot write empty output: {path}')
    with path.open('w', encoding='utf-8-sig', newline='') as file_obj:
        writer = csv.DictWriter(file_obj, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def influencer_id_from_seed(seed: str) -> str:
    digest = hashlib.sha256(f'golden-master-v1|{seed}'.encode('utf-8')).hexdigest()[:16]
    return f'inf_{digest}'


def observation_location(row: dict[str, str]) -> str:
    return f"{row.get('source_filename','')} | {row.get('source_sheet_name','')} | row {row.get('source_row_number','')}"


def review_id_for_quarantine_row(row: dict[str, str]) -> str:
    review_type, identity_key = review_key(row)
    return make_review_id(review_type, identity_key)


def decision_map(decisions: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    errors = validate_rows(decisions)
    if errors:
        joined = '; '.join(f'{error.review_id}:{error.code}' for error in errors)
        raise ValueError(f'invalid review decisions: {joined}')
    if any(not row.get('decision', '').strip() for row in decisions):
        raise ValueError('blank review decision is not allowed for promotion')
    return {row['review_id'].strip(): row for row in decisions}


def split_reviewed_quarantine(
    quarantine: list[dict[str, str]], decisions: list[dict[str, str]]
) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, object]]]:
    decisions_by_id = decision_map(decisions)
    promoted: list[dict[str, str]] = []
    remaining: list[dict[str, str]] = []
    audit_groups: dict[str, dict[str, object]] = {}

    for row in quarantine:
        review_id = review_id_for_quarantine_row(row)
        decision = decisions_by_id.get(review_id)
        if decision is None:
            raise ValueError(f'quarantine row has no review decision: {review_id}')

        action = decision['decision'].strip()
        if action in {'same_identity_use_handle', 'alias_confirmed'}:
            resolved_handle = decision['resolved_handle'].strip().casefold()
            promoted_row = dict(row)
            promoted_row['canonical_handle_candidate'] = resolved_handle
            promoted_row['dq_status'] = 'REVIEWED_PASS'
            promoted_row['dq_codes'] = 'DQ_IDENTITY_REVIEW_RESOLVED'
            promoted_row['identity_review_id'] = review_id
            promoted_row['identity_review_decision'] = action
            promoted.append(promoted_row)
            group_action = 'promote_to_resolved_handle'
        elif action == 'insufficient_evidence':
            remaining_row = dict(row)
            remaining_row['identity_review_id'] = review_id
            remaining_row['identity_review_decision'] = action
            remaining.append(remaining_row)
            resolved_handle = ''
            group_action = 'remain_quarantined'
        elif action == 'different_identity_keep_separate':
            raise ValueError(
                f'{review_id}: different_identity_keep_separate requires row-splitting logic and is not supported in Golden Master v1'
            )
        else:
            raise ValueError(f'{review_id}: unsupported review decision {action}')

        state = audit_groups.setdefault(
            review_id,
            {
                'review_id': review_id,
                'decision': action,
                'resolved_handle': resolved_handle,
                'decision_evidence': decision.get('decision_evidence', ''),
                'reviewer': decision.get('reviewer', ''),
                'reviewed_at': decision.get('reviewed_at', ''),
                'evidence_type': decision.get('evidence_type', ''),
                'evidence_strength': decision.get('evidence_strength', ''),
                'group_action': group_action,
                'observation_count': 0,
                'source_occurrences': [],
            },
        )
        state['observation_count'] = int(state['observation_count']) + 1
        state['source_occurrences'].append(observation_location(row))

    audit: list[dict[str, object]] = []
    for review_id in sorted(audit_groups):
        state = audit_groups[review_id]
        audit.append(
            {
                **{key: value for key, value in state.items() if key != 'source_occurrences'},
                'source_occurrences': ' || '.join(sorted(set(state['source_occurrences']))),
            }
        )
    return promoted, remaining, audit


def master_seed_for_handle(handle: str, accepted_handles: set[str], review_ids_by_handle: dict[str, set[str]]) -> tuple[str, str]:
    if handle in accepted_handles:
        return cluster_id('tiktok', handle), 'deterministic_exact_handle_cluster'
    review_ids = sorted(review_ids_by_handle.get(handle, set()))
    if not review_ids:
        raise ValueError(f'new reviewed handle has no review provenance: {handle}')
    return review_ids[0], 'reviewed_direct_identity_evidence'


def build_master(
    accepted: list[dict[str, str]],
    reviewed_promoted: list[dict[str, str]],
) -> tuple[list[dict[str, object]], list[dict[str, object]], dict[str, int]]:
    all_rows = [dict(row) for row in accepted] + [dict(row) for row in reviewed_promoted]
    accepted_handles = {
        row['canonical_handle_candidate'].strip().casefold()
        for row in accepted
        if row.get('canonical_handle_candidate', '').strip()
    }
    review_ids_by_handle: dict[str, set[str]] = defaultdict(set)
    for row in reviewed_promoted:
        handle = row['canonical_handle_candidate'].strip().casefold()
        review_ids_by_handle[handle].add(row.get('identity_review_id', ''))

    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in all_rows:
        handle = row.get('canonical_handle_candidate', '').strip().casefold()
        if not handle:
            raise ValueError('promoted observation is missing canonical_handle_candidate')
        groups[handle].append(row)

    master: list[dict[str, object]] = []
    aliases: list[dict[str, object]] = []
    alias_keys: set[tuple[str, str, str, str]] = set()

    for handle, group in sorted(groups.items()):
        seed, resolution_method = master_seed_for_handle(handle, accepted_handles, review_ids_by_handle)
        influencer_id = influencer_id_from_seed(seed)
        workbooks = sorted({row.get('source_filename', '') for row in group})
        sheets = sorted({f"{row.get('source_filename','')}::{row.get('source_sheet_name','')}" for row in group})
        occurrences = sorted({observation_location(row) for row in group})
        reviewed_count = sum(1 for row in group if row.get('identity_review_id', '').strip())
        master.append(
            {
                'influencer_id': influencer_id,
                'platform': 'tiktok',
                'canonical_handle': handle,
                'master_status': 'active',
                'identity_resolution_method': resolution_method,
                'identity_confidence': 'deterministic_exact' if reviewed_count == 0 else 'reviewed_evidence',
                'observation_count': len(group),
                'reviewed_observation_count': reviewed_count,
                'workbook_count': len(workbooks),
                'sheet_count': len(sheets),
                'source_workbooks': ' || '.join(workbooks),
                'source_occurrences': ' || '.join(occurrences),
                'survivor_seed': seed,
                'golden_master_version': 'v1',
                'pii_boundary_status': 'analytics_safe_identity_only',
            }
        )

        for row in group:
            review_id = row.get('identity_review_id', '').strip()
            match_method = 'reviewed_identity_resolution' if review_id else 'exact_canonical_handle'
            alias_candidates = [
                ('raw_primary', row.get('identity_primary_raw', '').strip()),
                ('raw_secondary', row.get('identity_secondary_raw', '').strip()),
            ]
            for normalized in filter(None, row.get('normalized_handle_candidates', '').split(';')):
                alias_candidates.append(('normalized_handle', normalized.strip().casefold()))

            for alias_type, alias_value in alias_candidates:
                if not alias_value:
                    continue
                key = (influencer_id, alias_type, alias_value.casefold(), observation_location(row))
                if key in alias_keys:
                    continue
                alias_keys.add(key)
                aliases.append(
                    {
                        'influencer_id': influencer_id,
                        'platform': 'tiktok',
                        'canonical_handle': handle,
                        'alias_type': alias_type,
                        'alias_value': alias_value,
                        'match_method': match_method,
                        'review_id': review_id,
                        'source_filename': row.get('source_filename', ''),
                        'source_sheet_name': row.get('source_sheet_name', ''),
                        'source_row_number': row.get('source_row_number', ''),
                        'source_row_hash': row.get('source_row_hash', ''),
                    }
                )

    stats = {
        'accepted_observations': len(accepted),
        'review_promoted_observations': len(reviewed_promoted),
        'golden_observations': len(all_rows),
        'golden_master_records': len(master),
        'alias_records': len(aliases),
        'cross_workbook_master_records': sum(1 for row in master if int(row['workbook_count']) > 1),
        'reviewed_master_records': sum(1 for row in master if int(row['reviewed_observation_count']) > 0),
    }
    if sum(int(row['observation_count']) for row in master) != len(all_rows):
        raise ValueError(f'golden master reconciliation failed: {stats}')
    if len({row['canonical_handle'] for row in master}) != len(master):
        raise ValueError('duplicate canonical_handle in Golden Master')
    if len({row['influencer_id'] for row in master}) != len(master):
        raise ValueError('duplicate influencer_id in Golden Master')
    return master, aliases, stats


def main() -> int:
    parser = argparse.ArgumentParser(description='Promote reviewed deterministic identity observations into Golden Influencer Master v1.')
    parser.add_argument('--accepted', required=True, type=Path)
    parser.add_argument('--quarantine', required=True, type=Path)
    parser.add_argument('--decisions', required=True, type=Path)
    parser.add_argument('--master-output', required=True, type=Path)
    parser.add_argument('--alias-output', required=True, type=Path)
    parser.add_argument('--remaining-quarantine-output', required=True, type=Path)
    parser.add_argument('--promotion-audit-output', required=True, type=Path)
    args = parser.parse_args()

    accepted = read_csv(args.accepted)
    quarantine = read_csv(args.quarantine)
    decisions = read_csv(args.decisions)
    reviewed_promoted, remaining, promotion_audit = split_reviewed_quarantine(quarantine, decisions)
    master, aliases, stats = build_master(accepted, reviewed_promoted)

    if len(reviewed_promoted) + len(remaining) != len(quarantine):
        raise SystemExit('review reconciliation failed: reviewed_promoted + remaining != quarantine input')

    write_csv(master, args.master_output)
    write_csv(aliases, args.alias_output)
    write_csv(remaining, args.remaining_quarantine_output)
    write_csv(promotion_audit, args.promotion_audit_output)

    summary = {
        **stats,
        'review_input_observations': len(quarantine),
        'remaining_quarantine_observations': len(remaining),
        'review_groups': len(decisions),
        'promoted_review_groups': sum(1 for row in decisions if row['decision'].strip() != 'insufficient_evidence'),
        'quarantined_review_groups': sum(1 for row in decisions if row['decision'].strip() == 'insufficient_evidence'),
    }
    print(' '.join(f'{key}={value}' for key, value in summary.items()))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
