from __future__ import annotations

import argparse
import csv
import hashlib
from collections import defaultdict
from pathlib import Path


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file_obj:
        return list(csv.DictReader(file_obj))


def write_csv(rows: list[dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError("review queue is empty")
    with path.open("w", encoding="utf-8-sig", newline="") as file_obj:
        writer = csv.DictWriter(file_obj, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def review_key(row: dict[str, str]) -> tuple[str, str]:
    codes = set(filter(None, row["dq_codes"].split(";")))
    if "DQ_IDENTITY_CONFLICT" in codes:
        candidates = sorted(filter(None, row["normalized_handle_candidates"].split(";")))
        return "identity_conflict", ";".join(candidates)
    return "identity_unparsable", row["identity_primary_raw"].strip().casefold()


def make_review_id(review_type: str, identity_key: str) -> str:
    digest = hashlib.sha256(f"{review_type}|{identity_key}".encode("utf-8")).hexdigest()[:12]
    return f"review_{digest}"


def build_queue(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    groups: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        groups[review_key(row)].append(row)

    queue: list[dict[str, object]] = []
    for (review_type, identity_key), group in sorted(groups.items()):
        first = group[0]
        occurrences = [
            f"{row['source_filename']} | {row['source_sheet_name']} | row {row['source_row_number']}"
            for row in group
        ]
        queue.append(
            {
                "review_id": make_review_id(review_type, identity_key),
                "review_type": review_type,
                "identity_primary_raw": first["identity_primary_raw"],
                "identity_secondary_raw": first["identity_secondary_raw"],
                "normalized_handle_candidates": first["normalized_handle_candidates"],
                "occurrence_count": len(group),
                "source_occurrences": " || ".join(occurrences),
                "suggested_action": "verify TikTok identity evidence manually; do not auto-merge",
                "decision": "",
                "resolved_handle": "",
                "decision_evidence": "",
                "reviewer": "",
                "reviewed_at": "",
            }
        )
    return queue


def main() -> int:
    parser = argparse.ArgumentParser(description="Build deterministic manual identity review queue from quarantined rows.")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    queue = build_queue(read_csv(args.input))
    write_csv(queue, args.output)
    print(f"review_groups={len(queue)} output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
