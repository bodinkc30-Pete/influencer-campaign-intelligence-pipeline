from __future__ import annotations

import argparse
import csv
from pathlib import Path

from src.historical_features import FEATURE_CONTRACT, build_historical_features


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    p = argparse.ArgumentParser(description="Build one-row-per-influencer historical feature layer from governed private history.")
    p.add_argument("--master", type=Path, required=True)
    p.add_argument("--campaign-fact", type=Path, required=True)
    p.add_argument("--campaign-registry", type=Path, required=True)
    p.add_argument("--deliverable-fact", type=Path, required=True)
    p.add_argument("--performance-fact", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--contract-output", type=Path)
    args = p.parse_args()

    features = build_historical_features(
        read_csv(args.master),
        read_csv(args.campaign_fact),
        read_csv(args.campaign_registry),
        read_csv(args.deliverable_fact),
        read_csv(args.performance_fact),
    )
    write_csv(args.output, features)

    if args.contract_output:
        contract_rows = [
            {"feature_name": a, "unit": b, "definition": c, "source_layer": d, "limitation": e, "feature_version": "v1"}
            for a, b, c, d, e in FEATURE_CONTRACT
        ]
        write_csv(args.contract_output, contract_rows)

    print(f"historical_feature_records={len(features)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
