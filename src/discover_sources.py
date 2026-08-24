from __future__ import annotations

import argparse
import csv
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class SourceFileRecord:
    source_filename: str
    file_hash_sha256: str
    file_size_bytes: int
    discovered_at_utc: str


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        while chunk := file_obj.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def discover_xlsx(input_dir: Path) -> list[SourceFileRecord]:
    discovered_at = datetime.now(timezone.utc).isoformat()
    records: list[SourceFileRecord] = []

    for path in sorted(input_dir.glob("*.xlsx"), key=lambda p: p.name.casefold()):
        records.append(
            SourceFileRecord(
                source_filename=path.name,
                file_hash_sha256=sha256_file(path),
                file_size_bytes=path.stat().st_size,
                discovered_at_utc=discovered_at,
            )
        )

    return records


def duplicate_hash_groups(records: list[SourceFileRecord]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    for record in records:
        groups.setdefault(record.file_hash_sha256, []).append(record.source_filename)
    return {digest: names for digest, names in groups.items() if len(names) > 1}




def discovery_gate_failures(
    records: list[SourceFileRecord],
    expected_count: int | None = None,
    *,
    allow_duplicate_hashes: bool = False,
) -> list[str]:
    failures: list[str] = []
    if expected_count is not None and len(records) != expected_count:
        failures.append(f"expected {expected_count} files, discovered {len(records)}")
    if duplicate_hash_groups(records) and not allow_duplicate_hashes:
        failures.append("duplicate workbook content hashes detected")
    return failures

def write_csv(records: list[SourceFileRecord], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as file_obj:
        writer = csv.DictWriter(file_obj, fieldnames=list(asdict(records[0]).keys()))
        writer.writeheader()
        writer.writerows(asdict(record) for record in records)


def main() -> int:
    parser = argparse.ArgumentParser(description="Discover private Excel source files and compute SHA-256 hashes.")
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-count", type=int, default=None)
    parser.add_argument("--allow-duplicate-hashes", action="store_true")
    args = parser.parse_args()

    records = discover_xlsx(args.input_dir)

    if not records:
        raise SystemExit("ERROR: no .xlsx files discovered")

    write_csv(records, args.output)

    duplicate_hashes = duplicate_hash_groups(records)

    summary = {
        "status": "PASS",
        "input_dir": str(args.input_dir),
        "output": str(args.output),
        "files_discovered": len(records),
        "expected_count": args.expected_count,
        "duplicate_hash_groups": duplicate_hashes,
    }

    failures = discovery_gate_failures(
        records,
        args.expected_count,
        allow_duplicate_hashes=args.allow_duplicate_hashes,
    )

    if failures:
        summary["status"] = "FAIL"
        summary["failures"] = failures
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 2

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
