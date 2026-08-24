from __future__ import annotations

import argparse
import csv
import re
from collections import defaultdict
from pathlib import Path

from src.candidate_adapter import _extract_handle
from src.xlsx_probe import probe_workbook, read_sheet_rows


def classify_strong_identity_cell(value: object | None) -> tuple[str, str] | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    lower = text.casefold()
    if 'tiktok.com/@' in lower:
        handle = _extract_handle(text)
        return ('tiktok_profile_url', handle) if handle else None
    if re.search(r'\(@[A-Za-z0-9._]+\)', text):
        handle = _extract_handle(text)
        return ('parenthesized_profile_handle', handle) if handle else None
    if re.search(r'(?<![A-Za-z0-9._])@[A-Za-z0-9._]+', text):
        handle = _extract_handle(text)
        return ('explicit_at_handle', handle) if handle else None
    return None


def _column_letters(index: int) -> str:
    index += 1
    letters: list[str] = []
    while index:
        index, remainder = divmod(index - 1, 26)
        letters.append(chr(ord('A') + remainder))
    return ''.join(reversed(letters))


def scan(input_dir: Path, target_handles: set[str]) -> list[dict[str, object]]:
    targets = {item.casefold() for item in target_handles if item}
    rows_out: list[dict[str, object]] = []
    for path in sorted(input_dir.glob('*.xlsx'), key=lambda p: p.name.casefold()):
        for sheet in probe_workbook(path, max_rows=1, max_cols=1):
            rows = read_sheet_rows(path, sheet.sheet_name, max_cols=100)
            for row_number, row in enumerate(rows, start=1):
                for column_index, value in enumerate(row):
                    evidence = classify_strong_identity_cell(value)
                    if evidence is None:
                        continue
                    evidence_type, handle = evidence
                    if handle not in targets:
                        continue
                    rows_out.append(
                        {
                            'matched_handle': handle,
                            'source_filename': path.name,
                            'source_sheet_name': sheet.sheet_name,
                            'source_row_number': row_number,
                            'source_cell': f'{_column_letters(column_index)}{row_number}',
                            'evidence_type': evidence_type,
                        }
                    )
    return rows_out


def write_csv(rows: list[dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        'matched_handle',
        'source_filename',
        'source_sheet_name',
        'source_row_number',
        'source_cell',
        'evidence_type',
    ]
    with path.open('w', encoding='utf-8-sig', newline='') as file_obj:
        writer = csv.DictWriter(file_obj, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def read_review_handles(path: Path) -> set[str]:
    with path.open('r', encoding='utf-8-sig', newline='') as file_obj:
        rows = list(csv.DictReader(file_obj))
    handles: set[str] = set()
    for row in rows:
        handles.update(item.strip().casefold() for item in row.get('normalized_handle_candidates', '').split(';') if item.strip())
    return handles


def main() -> int:
    parser = argparse.ArgumentParser(description='Scan all workbook sheets for strong TikTok identity evidence for review handles.')
    parser.add_argument('--input-dir', required=True, type=Path)
    parser.add_argument('--review-input', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    handles = read_review_handles(args.review_input)
    rows = scan(args.input_dir, handles)
    write_csv(rows, args.output)
    by_type: dict[str, int] = defaultdict(int)
    for row in rows:
        by_type[str(row['evidence_type'])] += 1
    print(f"target_handles={len(handles)} evidence_rows={len(rows)} " + ' '.join(f'{k}={v}' for k,v in sorted(by_type.items())))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
