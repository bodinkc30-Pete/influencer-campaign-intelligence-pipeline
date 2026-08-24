from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from src.candidate_adapter import _extract_handle


@dataclass(frozen=True)
class CorroborationHit:
    handle: str
    source_filename: str
    source_sheet_name: str
    source_row_number: str


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open('r', encoding='utf-8-sig', newline='') as file_obj:
        return list(csv.DictReader(file_obj))


def write_csv(rows: list[dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError('corroboration output is empty')
    with path.open('w', encoding='utf-8-sig', newline='') as file_obj:
        writer = csv.DictWriter(file_obj, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _accepted_exact_hits(accepted_rows: list[dict[str, str]]) -> dict[str, list[CorroborationHit]]:
    by_handle: dict[str, list[CorroborationHit]] = defaultdict(list)
    for row in accepted_rows:
        handle = row.get('canonical_handle_candidate', '').strip().casefold()
        if not handle:
            continue
        by_handle[handle].append(
            CorroborationHit(
                handle=handle,
                source_filename=row.get('source_filename', ''),
                source_sheet_name=row.get('source_sheet_name', ''),
                source_row_number=row.get('source_row_number', ''),
            )
        )
    return by_handle


def _secondary_handle(row: dict[str, str]) -> str:
    return _extract_handle(row.get('identity_secondary_raw', '')) or ''


def _primary_handle(row: dict[str, str]) -> str:
    return _extract_handle(row.get('identity_primary_raw', '')) or ''


def corroborate(review_rows: list[dict[str, str]], accepted_rows: list[dict[str, str]]) -> list[dict[str, object]]:
    accepted_by_handle = _accepted_exact_hits(accepted_rows)
    output: list[dict[str, object]] = []

    for row in review_rows:
        candidates = [item.strip().casefold() for item in row.get('normalized_handle_candidates', '').split(';') if item.strip()]
        counts: dict[str, int] = {}
        workbooks: dict[str, set[str]] = {}
        hit_descriptions: dict[str, list[str]] = {}

        for candidate in candidates:
            hits = accepted_by_handle.get(candidate, [])
            counts[candidate] = len(hits)
            workbooks[candidate] = {hit.source_filename for hit in hits}
            hit_descriptions[candidate] = [
                f'{hit.source_filename} | {hit.source_sheet_name} | row {hit.source_row_number}' for hit in hits
            ]

        supported = [candidate for candidate in candidates if counts.get(candidate, 0) > 0]
        primary = _primary_handle(row)
        secondary = _secondary_handle(row)

        if not candidates:
            status = 'no_candidate_handle'
            supported_handle = ''
            evidence_consistency = 'not_applicable'
            recommendation = 'manual_review_required'
        elif not supported:
            status = 'no_independent_exact_corroboration'
            supported_handle = ''
            evidence_consistency = 'no_independent_support'
            recommendation = 'manual_review_required'
        elif len(supported) > 1:
            status = 'multiple_candidates_corroborated'
            supported_handle = ''
            evidence_consistency = 'conflicting_independent_support'
            recommendation = 'manual_review_required'
        else:
            supported_handle = supported[0]
            status = 'single_candidate_corroborated'
            if secondary and supported_handle == secondary:
                evidence_consistency = 'supports_secondary_profile_handle'
                recommendation = 'human_can_confirm_supported_handle'
            elif primary and supported_handle == primary and secondary and primary != secondary:
                evidence_consistency = 'supports_primary_but_conflicts_with_secondary_profile_handle'
                recommendation = 'manual_review_required'
            elif primary and supported_handle == primary:
                evidence_consistency = 'supports_primary_handle'
                recommendation = 'human_can_confirm_supported_handle'
            else:
                evidence_consistency = 'supports_observed_candidate'
                recommendation = 'human_can_confirm_supported_handle'

        summary_parts: list[str] = []
        source_parts: list[str] = []
        for candidate in candidates:
            summary_parts.append(
                f'{candidate}:accepted_hits={counts.get(candidate, 0)},workbooks={len(workbooks.get(candidate, set()))}'
            )
            if hit_descriptions.get(candidate):
                source_parts.append(f"{candidate} => " + ' || '.join(hit_descriptions[candidate]))

        enriched = dict(row)
        enriched.update(
            {
                'primary_parsed_handle': primary,
                'secondary_parsed_handle': secondary,
                'corroboration_status': status,
                'corroborated_handle': supported_handle,
                'corroboration_summary': ' ; '.join(summary_parts),
                'corroboration_sources': ' ; '.join(source_parts),
                'evidence_consistency': evidence_consistency,
                'machine_recommendation': recommendation,
                'auto_resolution_allowed': 'no',
            }
        )
        output.append(enriched)

    return output


def main() -> int:
    parser = argparse.ArgumentParser(description='Add independent exact-handle corroboration to identity review evidence.')
    parser.add_argument('--review-input', required=True, type=Path)
    parser.add_argument('--accepted-input', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()

    rows = corroborate(read_csv(args.review_input), read_csv(args.accepted_input))
    write_csv(rows, args.output)
    status_counts: dict[str, int] = defaultdict(int)
    for row in rows:
        status_counts[str(row['corroboration_status'])] += 1
    print(f"review_groups={len(rows)} " + ' '.join(f'{key}={value}' for key, value in sorted(status_counts.items())))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
