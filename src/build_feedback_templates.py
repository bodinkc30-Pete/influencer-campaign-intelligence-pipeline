from __future__ import annotations

import argparse
import csv
from pathlib import Path

from src.feedback_loop import build_campaign_result_template, build_human_review_queue


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError("cannot write an empty feedback template")
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build governed human-review and feedback templates from a matching shortlist.")
    parser.add_argument("--shortlist", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--primary-review-limit", type=int, default=10)
    args = parser.parse_args()

    review_rows = build_human_review_queue(read_csv(args.shortlist), primary_review_limit=args.primary_review_limit)
    result_rows = build_campaign_result_template(review_rows)
    write_csv(args.output_dir / "human_review_queue_v1.csv", review_rows)
    write_csv(args.output_dir / "campaign_result_feedback_template_v1.csv", result_rows)


if __name__ == "__main__":
    main()
