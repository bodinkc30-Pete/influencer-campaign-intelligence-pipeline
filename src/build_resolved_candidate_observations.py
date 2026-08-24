from __future__ import annotations

import argparse
import csv
from pathlib import Path

from src.promote_golden_master import split_reviewed_quarantine


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file_obj:
        return list(csv.DictReader(file_obj))


def write_csv(rows: list[dict[str, object]], path: Path) -> None:
    if not rows:
        raise ValueError(f"cannot write empty output: {path}")
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as file_obj:
        writer = csv.DictWriter(file_obj, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def alias_hash_map(alias_rows: list[dict[str, str]]) -> dict[str, str]:
    result: dict[str, str] = {}
    for row in alias_rows:
        source_hash = row.get("source_row_hash", "").strip()
        influencer_id = row.get("influencer_id", "").strip()
        if not source_hash or not influencer_id:
            continue
        existing = result.get(source_hash)
        if existing and existing != influencer_id:
            raise ValueError(f"source row hash maps to multiple influencers: {source_hash}")
        result[source_hash] = influencer_id
    return result


def build_resolved_rows(
    accepted: list[dict[str, str]],
    quarantine: list[dict[str, str]],
    decisions: list[dict[str, str]],
    aliases: list[dict[str, str]],
) -> tuple[list[dict[str, object]], list[dict[str, str]], dict[str, int]]:
    reviewed_promoted, remaining, _ = split_reviewed_quarantine(quarantine, decisions)
    resolved: list[dict[str, object]] = [dict(row) for row in accepted] + [dict(row) for row in reviewed_promoted]
    hash_to_influencer = alias_hash_map(aliases)
    missing: list[str] = []
    for row in resolved:
        source_hash = str(row.get("source_row_hash", "")).strip()
        influencer_id = hash_to_influencer.get(source_hash)
        if not influencer_id:
            missing.append(source_hash)
            continue
        row["influencer_id"] = influencer_id
        row.setdefault("identity_review_id", "")
        row.setdefault("identity_review_decision", "")
    if missing:
        raise ValueError(f"resolved observations missing Golden Master alias mapping: {len(missing)}")
    source_hashes = [str(row.get("source_row_hash", "")) for row in resolved]
    if len(source_hashes) != len(set(source_hashes)):
        raise ValueError("duplicate source_row_hash in resolved candidate observations")
    stats = {
        "accepted_observations": len(accepted),
        "review_promoted_observations": len(reviewed_promoted),
        "resolved_observations": len(resolved),
        "remaining_quarantine_observations": len(remaining),
    }
    return resolved, remaining, stats


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Golden-Master-linked candidate observations after governed identity review.")
    parser.add_argument("--accepted", required=True, type=Path)
    parser.add_argument("--quarantine", required=True, type=Path)
    parser.add_argument("--decisions", required=True, type=Path)
    parser.add_argument("--aliases", required=True, type=Path)
    parser.add_argument("--resolved-output", required=True, type=Path)
    parser.add_argument("--remaining-quarantine-output", required=True, type=Path)
    args = parser.parse_args()

    resolved, remaining, stats = build_resolved_rows(
        read_csv(args.accepted),
        read_csv(args.quarantine),
        read_csv(args.decisions),
        read_csv(args.aliases),
    )
    write_csv(resolved, args.resolved_output)
    write_csv(remaining, args.remaining_quarantine_output)
    print(" ".join(f"{key}={value}" for key, value in stats.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
