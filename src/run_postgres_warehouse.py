from __future__ import annotations

import argparse
from getpass import getpass
import json
import os
from pathlib import Path

try:
    from .postgres_warehouse_runtime import WarehouseConnection, execute_warehouse
except ImportError:
    from postgres_warehouse_runtime import WarehouseConnection, execute_warehouse


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Execute PostgreSQL Warehouse v1 with batch fingerprint, ops ledger, DQ gate, and same-batch skip."
    )
    p.add_argument("--host", default="localhost")
    p.add_argument("--port", type=int, default=5432)
    p.add_argument("--user", default="postgres")
    p.add_argument("--database", default="influencer_dw")
    p.add_argument("--load-dir", type=Path, required=True, help="Private load-ready CSV directory")
    p.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument("--psql-path", default=None)
    p.add_argument("--evidence-json", type=Path, default=None)
    p.add_argument(
        "--password-env",
        default="PGPASSWORD",
        help="Environment variable containing the PostgreSQL password. If absent, prompt securely.",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    password = os.environ.get(args.password_env)
    if password is None:
        password = getpass(f"PostgreSQL password for {args.user}@{args.host}:{args.port}: ")

    connection = WarehouseConnection(
        host=args.host,
        port=args.port,
        user=args.user,
        database=args.database,
        password=password,
    )
    result = execute_warehouse(
        connection=connection,
        load_dir=args.load_dir,
        project_root=args.project_root,
        psql_path=args.psql_path,
    )
    payload = {
        "status": result.status,
        "run_id": result.run_id,
        "batch_fingerprint": result.batch_fingerprint,
        "file_count": result.file_count,
        "source_rows": result.source_rows,
        "skipped": result.skipped,
        "error": result.error,
        "steps": result.steps,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if args.evidence_json:
        args.evidence_json.parent.mkdir(parents=True, exist_ok=True)
        args.evidence_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if result.status in {"SUCCESS", "SKIPPED"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
