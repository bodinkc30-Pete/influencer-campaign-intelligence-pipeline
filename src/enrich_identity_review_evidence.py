from __future__ import annotations

import argparse
import csv
from pathlib import Path


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open('r', encoding='utf-8-sig', newline='') as file_obj:
        return list(csv.DictReader(file_obj))


def write_csv(rows: list[dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError('identity review evidence is empty')
    with path.open('w', encoding='utf-8-sig', newline='') as file_obj:
        writer = csv.DictWriter(file_obj, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def classify_evidence(row: dict[str, str]) -> tuple[str, str, str]:
    review_type = row.get('review_type', '').strip()
    secondary = row.get('identity_secondary_raw', '').strip()
    secondary_cf = secondary.casefold()

    if review_type == 'identity_unparsable':
        return (
            'display_only_unparsable',
            'low',
            'find an explicit TikTok profile URL/@handle or other authoritative source evidence; do not infer from display name',
        )

    if 'tiktok.com/@' in secondary_cf:
        return (
            'explicit_tiktok_profile_url_conflict',
            'high',
            'verify the profile URL and whether the competing plain handle is a stale alias or source typo before resolving',
        )

    if '(@' in secondary and 'tiktok' in secondary_cf:
        return (
            'embedded_tiktok_profile_handle_conflict',
            'medium',
            'verify the embedded @handle against an explicit profile URL or independent source occurrence before resolving',
        )

    return (
        'plain_text_handle_conflict',
        'low',
        'require corroborating profile evidence; spelling similarity alone is not sufficient for automatic resolution',
    )


def enrich(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    enriched: list[dict[str, object]] = []
    for row in rows:
        evidence_type, evidence_strength, required_check = classify_evidence(row)
        occurrence_count = int(row.get('occurrence_count', '0') or 0)
        enriched.append(
            {
                **row,
                'evidence_type': evidence_type,
                'evidence_strength': evidence_strength,
                'cross_occurrence_evidence': 'yes' if occurrence_count > 1 else 'no',
                'required_manual_check': required_check,
                'auto_resolution_allowed': 'no',
            }
        )
    return enriched


def main() -> int:
    parser = argparse.ArgumentParser(description='Classify evidence strength for manual identity-review groups.')
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()

    rows = enrich(read_csv(args.input))
    write_csv(rows, args.output)

    counts: dict[str, int] = {}
    for row in rows:
        key = str(row['evidence_type'])
        counts[key] = counts.get(key, 0) + 1

    print(f'review_groups={len(rows)} evidence_types={counts} output={args.output}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
