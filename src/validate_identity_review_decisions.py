from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path


ALLOWED_DECISIONS = {
    '',
    'same_identity_use_handle',
    'different_identity_keep_separate',
    'alias_confirmed',
    'insufficient_evidence',
}


@dataclass(frozen=True)
class ReviewValidationError:
    review_id: str
    code: str
    message: str


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open('r', encoding='utf-8-sig', newline='') as file_obj:
        return list(csv.DictReader(file_obj))


def validate_row(row: dict[str, str]) -> list[ReviewValidationError]:
    errors: list[ReviewValidationError] = []
    review_id = row.get('review_id', '').strip()
    decision = row.get('decision', '').strip()
    resolved_handle = row.get('resolved_handle', '').strip()
    evidence = row.get('decision_evidence', '').strip()

    if decision not in ALLOWED_DECISIONS:
        errors.append(ReviewValidationError(review_id, 'REVIEW_DECISION_INVALID', f'unsupported decision: {decision}'))
        return errors

    if not decision:
        errors.append(ReviewValidationError(review_id, 'REVIEW_UNRESOLVED', 'decision is blank'))
        return errors

    if decision in {'same_identity_use_handle', 'alias_confirmed'}:
        if not resolved_handle:
            errors.append(ReviewValidationError(review_id, 'REVIEW_RESOLVED_HANDLE_REQUIRED', 'resolved_handle is required'))
        candidates = {value for value in row.get('normalized_handle_candidates', '').split(';') if value}
        if resolved_handle and candidates and resolved_handle not in candidates:
            errors.append(
                ReviewValidationError(
                    review_id,
                    'REVIEW_RESOLVED_HANDLE_NOT_OBSERVED',
                    'resolved_handle must be one of the observed normalized candidates',
                )
            )

    if decision == 'different_identity_keep_separate' and resolved_handle:
        errors.append(
            ReviewValidationError(
                review_id,
                'REVIEW_SINGLE_HANDLE_NOT_ALLOWED',
                'different identities cannot be collapsed into one resolved_handle',
            )
        )

    if decision == 'insufficient_evidence' and resolved_handle:
        errors.append(
            ReviewValidationError(
                review_id,
                'REVIEW_HANDLE_NOT_ALLOWED_WITH_INSUFFICIENT_EVIDENCE',
                'insufficient evidence must remain unresolved',
            )
        )

    # Every explicit decision, including insufficient_evidence, must state why.
    if decision and not evidence:
        errors.append(ReviewValidationError(review_id, 'REVIEW_EVIDENCE_REQUIRED', 'decision_evidence is required'))

    return errors


def validate_rows(rows: list[dict[str, str]]) -> list[ReviewValidationError]:
    errors: list[ReviewValidationError] = []
    for row in rows:
        errors.extend(validate_row(row))
    return errors


def summarize(rows: list[dict[str, str]]) -> dict[str, int]:
    blank = sum(1 for row in rows if not row.get('decision', '').strip())
    quarantined = sum(1 for row in rows if row.get('decision', '').strip() == 'insufficient_evidence')
    promotable = sum(
        1
        for row in rows
        if row.get('decision', '').strip() in {'same_identity_use_handle', 'alias_confirmed', 'different_identity_keep_separate'}
    )
    return {
        'review_groups': len(rows),
        'blank_groups': blank,
        'quarantined_groups': quarantined,
        'promotable_groups': promotable,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description='Validate manual identity-review decisions before Golden Master promotion.')
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument(
        '--allow-quarantine',
        action='store_true',
        help='Treat explicit insufficient_evidence decisions as a valid reviewed outcome while keeping those groups quarantined.',
    )
    args = parser.parse_args()

    rows = read_csv(args.input)
    errors = validate_rows(rows)
    summary = summarize(rows)
    print(
        'review_groups={review_groups} blank_groups={blank_groups} '
        'quarantined_groups={quarantined_groups} promotable_groups={promotable_groups} '
        'validation_errors={validation_errors}'.format(
            **summary,
            validation_errors=len(errors),
        )
    )
    for error in errors:
        print(f'{error.review_id}|{error.code}|{error.message}')

    if errors or summary['blank_groups']:
        return 2
    if summary['quarantined_groups'] and not args.allow_quarantine:
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
