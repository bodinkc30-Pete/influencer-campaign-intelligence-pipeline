from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

from generate_postgres_integration_fixture import write_fixture


CORE_TABLES = [
    "dim_influencer",
    "influencer_identity_alias",
    "dim_brand",
    "dim_campaign",
    "campaign_requirement",
    "fact_campaign_influencer",
    "fact_campaign_deliverable",
    "fact_influencer_performance",
    "fact_campaign_performance",
]


def run_command(
    command: list[str],
    *,
    env: dict[str, str],
    capture: bool = True,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        env=env,
        text=True,
        capture_output=capture,
        check=False,
    )

    if result.returncode != 0:
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)

    return result


def psql_query(
    *,
    psql: str,
    host: str,
    port: str,
    user: str,
    database: str,
    sql: str,
    env: dict[str, str],
) -> str:
    result = run_command(
        [
            psql,
            "-h",
            host,
            "-p",
            port,
            "-U",
            user,
            "-d",
            database,
            "-X",
            "-v",
            "ON_ERROR_STOP=1",
            "-At",
            "-c",
            sql,
        ],
        env=env,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"psql query failed for database={database}"
        )

    return result.stdout.strip()


def core_counts(
    *,
    psql: str,
    host: str,
    port: str,
    user: str,
    database: str,
    env: dict[str, str],
) -> dict[str, int]:
    counts: dict[str, int] = {}

    for table in CORE_TABLES:
        raw = psql_query(
            psql=psql,
            host=host,
            port=port,
            user=user,
            database=database,
            sql=f"SELECT count(*) FROM core.{table};",
            env=env,
        )
        counts[table] = int(raw)

    return counts


def run_warehouse(
    *,
    project_root: Path,
    python_executable: str,
    psql: str,
    host: str,
    port: str,
    user: str,
    database: str,
    load_dir: Path,
    evidence_json: Path,
    env: dict[str, str],
) -> dict:
    result = run_command(
        [
            python_executable,
            "-m",
            "src.run_postgres_warehouse",
            "--host",
            host,
            "--port",
            port,
            "--user",
            user,
            "--database",
            database,
            "--load-dir",
            str(load_dir),
            "--project-root",
            str(project_root),
            "--psql-path",
            psql,
            "--evidence-json",
            str(evidence_json),
            "--password-env",
            "PGPASSWORD",
        ],
        env=env,
    )

    if result.returncode != 0:
        raise RuntimeError(
            "Warehouse runner failed with "
            f"exit code {result.returncode}"
        )

    if not evidence_json.is_file():
        raise RuntimeError(
            f"Evidence file not created: {evidence_json}"
        )

    return json.loads(
        evidence_json.read_text(
            encoding="utf-8-sig",
        )
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run real PostgreSQL warehouse integration test "
            "using public-safe synthetic data."
        )
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("PGHOST", "localhost"),
    )
    parser.add_argument(
        "--port",
        default=os.environ.get("PGPORT", "5432"),
    )
    parser.add_argument(
        "--user",
        default=os.environ.get("PGUSER", "postgres"),
    )
    parser.add_argument(
        "--admin-database",
        default="postgres",
    )
    parser.add_argument(
        "--psql-path",
        default="psql",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not os.environ.get("PGPASSWORD"):
        raise RuntimeError(
            "PGPASSWORD must be set for integration testing."
        )

    project_root = Path(__file__).resolve().parents[2]

    database = (
        "influencer_ci_"
        + uuid.uuid4().hex[:12]
    )

    child_env = os.environ.copy()

    print(f"INTEGRATION_DATABASE={database}")
    print("PUBLIC_SAFE_FIXTURE=True")

    created = False

    try:
        exists_before = psql_query(
            psql=args.psql_path,
            host=args.host,
            port=str(args.port),
            user=args.user,
            database=args.admin_database,
            sql=(
                "SELECT count(*) "
                "FROM pg_database "
                f"WHERE datname = '{database}';"
            ),
            env=child_env,
        )

        if exists_before != "0":
            raise RuntimeError(
                "Integration database unexpectedly exists."
            )

        create_result = run_command(
            [
                args.psql_path,
                "-h",
                args.host,
                "-p",
                str(args.port),
                "-U",
                args.user,
                "-d",
                args.admin_database,
                "-X",
                "-v",
                "ON_ERROR_STOP=1",
                "-c",
                f'CREATE DATABASE "{database}";',
            ],
            env=child_env,
        )

        if create_result.returncode != 0:
            raise RuntimeError(
                "Unable to create integration database."
            )

        created = True
        print("DATABASE_CREATED=True")

        with tempfile.TemporaryDirectory(
            prefix="influencer-pg-ci-"
        ) as temp_dir:
            temp_root = Path(temp_dir)
            load_dir = temp_root / "load"
            write_fixture(load_dir)

            csv_files = sorted(load_dir.glob("*.csv"))

            if len(csv_files) != 9:
                raise RuntimeError(
                    f"Expected 9 fixture CSVs, found {len(csv_files)}"
                )

            print("FIXTURE_CSV_COUNT=9")

            first_evidence_path = (
                temp_root / "first_run.json"
            )

            first = run_warehouse(
                project_root=project_root,
                python_executable=sys.executable,
                psql=args.psql_path,
                host=args.host,
                port=str(args.port),
                user=args.user,
                database=database,
                load_dir=load_dir,
                evidence_json=first_evidence_path,
                env=child_env,
            )

            print(
                f"FIRST_STATUS={first.get('status')}"
            )
            print(
                f"FIRST_SKIPPED={first.get('skipped')}"
            )
            print(
                "FIRST_SOURCE_ROWS="
                f"{first.get('source_rows')}"
            )

            if first.get("status") != "SUCCESS":
                raise AssertionError(
                    "First warehouse load was not SUCCESS."
                )

            if first.get("skipped") is not False:
                raise AssertionError(
                    "First warehouse load was unexpectedly skipped."
                )

            if first.get("file_count") != 9:
                raise AssertionError(
                    "First warehouse load file_count != 9."
                )

            if first.get("source_rows") != 9:
                raise AssertionError(
                    "First warehouse load source_rows != 9."
                )

            counts_before = core_counts(
                psql=args.psql_path,
                host=args.host,
                port=str(args.port),
                user=args.user,
                database=database,
                env=child_env,
            )

            print(
                "CORE_COUNTS_BEFORE="
                + json.dumps(
                    counts_before,
                    sort_keys=True,
                )
            )

            if any(
                count != 1
                for count in counts_before.values()
            ):
                raise AssertionError(
                    "Expected exactly one row in each core table."
                )

            second_evidence_path = (
                temp_root / "second_run.json"
            )

            second = run_warehouse(
                project_root=project_root,
                python_executable=sys.executable,
                psql=args.psql_path,
                host=args.host,
                port=str(args.port),
                user=args.user,
                database=database,
                load_dir=load_dir,
                evidence_json=second_evidence_path,
                env=child_env,
            )

            print(
                f"SECOND_STATUS={second.get('status')}"
            )
            print(
                f"SECOND_SKIPPED={second.get('skipped')}"
            )

            if second.get("status") != "SKIPPED":
                raise AssertionError(
                    "Second warehouse run was not SKIPPED."
                )

            if second.get("skipped") is not True:
                raise AssertionError(
                    "Second warehouse run skipped flag != True."
                )

            fingerprint_match = (
                second.get("batch_fingerprint")
                == first.get("batch_fingerprint")
            )

            print(
                f"FINGERPRINT_MATCH={fingerprint_match}"
            )

            if not fingerprint_match:
                raise AssertionError(
                    "Same fixture produced different fingerprints."
                )

            counts_after = core_counts(
                psql=args.psql_path,
                host=args.host,
                port=str(args.port),
                user=args.user,
                database=database,
                env=child_env,
            )

            print(
                "CORE_COUNTS_AFTER="
                + json.dumps(
                    counts_after,
                    sort_keys=True,
                )
            )

            row_counts_unchanged = (
                counts_before == counts_after
            )

            print(
                "ROW_COUNTS_UNCHANGED="
                f"{row_counts_unchanged}"
            )

            if not row_counts_unchanged:
                raise AssertionError(
                    "Core row counts changed after same-batch rerun."
                )

        print("POSTGRES_INTEGRATION_STATUS=PASS")
        return 0

    finally:
        if created:
            terminate_sql = (
                "SELECT pg_terminate_backend(pid) "
                "FROM pg_stat_activity "
                f"WHERE datname = '{database}' "
                "AND pid <> pg_backend_pid();"
            )

            psql_query(
                psql=args.psql_path,
                host=args.host,
                port=str(args.port),
                user=args.user,
                database=args.admin_database,
                sql=terminate_sql,
                env=child_env,
            )

            drop_result = run_command(
                [
                    args.psql_path,
                    "-h",
                    args.host,
                    "-p",
                    str(args.port),
                    "-U",
                    args.user,
                    "-d",
                    args.admin_database,
                    "-X",
                    "-v",
                    "ON_ERROR_STOP=1",
                    "-c",
                    f'DROP DATABASE IF EXISTS "{database}";',
                ],
                env=child_env,
            )

            print(
                "DATABASE_DROPPED="
                f"{drop_result.returncode == 0}"
            )


if __name__ == "__main__":
    raise SystemExit(main())
