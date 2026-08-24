from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
import csv
import hashlib
import os
import re
import shutil
import subprocess
import tempfile


PIPELINE_NAME = "postgresql_warehouse_v1"
LOAD_ORDER = (
    "dim_influencer",
    "influencer_identity_alias",
    "dim_brand",
    "dim_campaign",
    "campaign_requirement",
    "fact_campaign_influencer",
    "fact_campaign_deliverable",
    "fact_influencer_performance",
    "fact_campaign_performance",
)

PRIMARY_KEYS = {
    "dim_influencer": ("influencer_id",),
    "influencer_identity_alias": ("source_row_hash", "alias_type", "alias_value"),
    "dim_brand": ("brand_id",),
    "dim_campaign": ("campaign_id",),
    "campaign_requirement": ("campaign_id",),
    "fact_campaign_influencer": ("campaign_influencer_id",),
    "fact_campaign_deliverable": ("deliverable_id",),
    "fact_influencer_performance": ("performance_id",),
    "fact_campaign_performance": ("campaign_performance_id",),
}


@dataclass(frozen=True)
class PsqlResult:
    returncode: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class WarehouseConnection:
    host: str
    port: int
    user: str
    database: str
    password: str | None = None


@dataclass
class WarehouseRunResult:
    status: str
    run_id: str
    batch_fingerprint: str
    file_count: int
    source_rows: int
    skipped: bool = False
    steps: list[dict[str, object]] = field(default_factory=list)
    error: str | None = None


def find_psql(explicit: str | None = None) -> str:
    if explicit:
        candidate = Path(explicit)
        if candidate.exists():
            return str(candidate)
        raise FileNotFoundError(f"psql was not found at explicit path: {explicit}")

    found = shutil.which("psql")
    if found:
        return found

    if os.name == "nt":
        root = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "PostgreSQL"
        candidates: list[tuple[tuple[int, ...], Path]] = []
        if root.exists():
            for child in root.iterdir():
                psql = child / "bin" / "psql.exe"
                if not psql.exists():
                    continue
                parts = tuple(int(x) for x in re.findall(r"\d+", child.name)) or (0,)
                candidates.append((parts, psql))
        if candidates:
            candidates.sort(reverse=True)
            return str(candidates[0][1])

    raise FileNotFoundError(
        "psql was not found. Install PostgreSQL client tools, add psql to PATH, "
        "or pass --psql-path."
    )


def sql_literal(value: str | None) -> str:
    if value is None:
        return "NULL"
    return "'" + value.replace("'", "''") + "'"


def quote_psql_literal(path: Path) -> str:
    text = str(path.resolve()).replace("\\", "/").replace("'", "''")
    return f"'{text}'"


def validate_load_dir(load_dir: Path) -> None:
    missing = [str(load_dir / f"{table}.csv") for table in LOAD_ORDER if not (load_dir / f"{table}.csv").is_file()]
    if missing:
        raise FileNotFoundError("Missing load-ready CSV files: " + ", ".join(missing))


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_batch_manifest(load_dir: Path) -> list[str]:
    validate_load_dir(load_dir)
    return [f"{table}.csv|{file_sha256(load_dir / f'{table}.csv')}" for table in LOAD_ORDER]


def compute_batch_fingerprint(load_dir: Path) -> str:
    manifest_text = "\n".join(build_batch_manifest(load_dir))
    return hashlib.sha256(manifest_text.encode("utf-8")).hexdigest()


def count_csv_rows(path: Path) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        try:
            next(reader)
        except StopIteration:
            return 0
        return sum(1 for _ in reader)


def source_row_counts(load_dir: Path) -> dict[str, int]:
    validate_load_dir(load_dir)
    return {table: count_csv_rows(load_dir / f"{table}.csv") for table in LOAD_ORDER}


def build_copy_script(load_dir: Path) -> str:
    lines = [
        "\\set ON_ERROR_STOP on",
        "BEGIN;",
        "TRUNCATE TABLE",
        "    stg.fact_campaign_performance,",
        "    stg.fact_influencer_performance,",
        "    stg.fact_campaign_deliverable,",
        "    stg.fact_campaign_influencer,",
        "    stg.campaign_requirement,",
        "    stg.dim_campaign,",
        "    stg.dim_brand,",
        "    stg.influencer_identity_alias,",
        "    stg.dim_influencer;",
        "",
    ]
    for table in LOAD_ORDER:
        csv_path = load_dir / f"{table}.csv"
        lines.append(
            f"\\copy stg.{table} FROM {quote_psql_literal(csv_path)} "
            "WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');"
        )
    lines.extend(["COMMIT;", ""])
    return "\n".join(lines)


def _connection_args(connection: WarehouseConnection) -> list[str]:
    return [
        "-h", connection.host,
        "-p", str(connection.port),
        "-U", connection.user,
        "-d", connection.database,
    ]


def run_psql(
    psql_path: str,
    connection: WarehouseConnection,
    *,
    sql_file: Path | None = None,
    sql_text: str | None = None,
    tuples_only: bool = False,
) -> PsqlResult:
    if (sql_file is None) == (sql_text is None):
        raise ValueError("Provide exactly one of sql_file or sql_text")

    cmd = [psql_path, *_connection_args(connection), "-v", "ON_ERROR_STOP=1", "-X"]
    if tuples_only:
        cmd.extend(["-A", "-t", "-F", "\t"])

    temp_path: Path | None = None
    if sql_text is not None:
        fd, temp_name = tempfile.mkstemp(prefix="warehouse_psql_", suffix=".sql")
        os.close(fd)
        temp_path = Path(temp_name)
        temp_path.write_text(sql_text, encoding="utf-8")
        cmd.extend(["-f", str(temp_path)])
    else:
        cmd.extend(["-f", str(sql_file)])

    env = os.environ.copy()
    if connection.password is not None:
        env["PGPASSWORD"] = connection.password

    try:
        proc = subprocess.run(cmd, text=True, capture_output=True, check=False, env=env)
        return PsqlResult(proc.returncode, proc.stdout, proc.stderr)
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink()


def _single_value(result: PsqlResult) -> str:
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "psql query failed")
    values = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return values[-1] if values else ""


def _record_step(result: WarehouseRunResult, name: str, psql_result: PsqlResult) -> None:
    result.steps.append({
        "step": name,
        "returncode": psql_result.returncode,
        "stdout": psql_result.stdout,
        "stderr": psql_result.stderr,
    })


def _execute_step(
    result: WarehouseRunResult,
    name: str,
    psql_path: str,
    connection: WarehouseConnection,
    *,
    sql_file: Path | None = None,
    sql_text: str | None = None,
    tuples_only: bool = False,
) -> PsqlResult:
    psql_result = run_psql(
        psql_path,
        connection,
        sql_file=sql_file,
        sql_text=sql_text,
        tuples_only=tuples_only,
    )
    _record_step(result, name, psql_result)
    if psql_result.returncode != 0:
        raise RuntimeError(
            f"{name} failed: " + (psql_result.stderr.strip() or psql_result.stdout.strip() or "unknown psql error")
        )
    return psql_result


def _transition_sql(run_id: str, from_stage: str, to_stage: str) -> str:
    return f"""
DO $$
DECLARE affected integer;
BEGIN
    UPDATE ops.pipeline_run
    SET stage = {sql_literal(to_stage)}
    WHERE run_id = {sql_literal(run_id)}
      AND status = 'RUNNING'
      AND stage = {sql_literal(from_stage)};
    GET DIAGNOSTICS affected = ROW_COUNT;
    IF affected <> 1 THEN
        RAISE EXCEPTION 'invalid pipeline state transition: % -> % for run %',
            {sql_literal(from_stage)}, {sql_literal(to_stage)}, {sql_literal(run_id)};
    END IF;
END $$;
"""


def _mark_failed(
    psql_path: str,
    connection: WarehouseConnection,
    *,
    run_id: str,
    stage: str,
    error: str,
) -> PsqlResult:
    message = error[:1800]
    sql = f"""
UPDATE ops.pipeline_run
SET status = 'FAILED',
    stage = {sql_literal(stage)},
    finished_at = now(),
    error_code = 'WAREHOUSE_RUNTIME_ERROR',
    error_message = {sql_literal(message)}
WHERE run_id = {sql_literal(run_id)}
  AND status = 'RUNNING';
"""
    return run_psql(psql_path, connection, sql_text=sql)


def _same_batch_sql(batch_fingerprint: str) -> str:
    return f"""
SELECT CASE WHEN EXISTS (
    SELECT 1
    FROM ops.incremental_state s
    JOIN ops.pipeline_run p ON p.run_id = s.last_successful_run_id
    WHERE s.pipeline_name = {sql_literal(PIPELINE_NAME)}
      AND s.batch_fingerprint = {sql_literal(batch_fingerprint)}
      AND p.status = 'SUCCESS'
) THEN 1 ELSE 0 END;
"""


def _skip_sql(run_id: str, batch_fingerprint: str, source_rows: int) -> str:
    return f"""
INSERT INTO ops.pipeline_run (
    run_id, pipeline_name, batch_fingerprint, started_at, finished_at,
    status, stage, rows_attempted, rows_loaded, rows_rejected, retry_count
)
VALUES (
    {sql_literal(run_id)}, {sql_literal(PIPELINE_NAME)}, {sql_literal(batch_fingerprint)},
    now(), now(), 'SKIPPED', 'SAME_BATCH_GATE', {source_rows}, 0, 0, 0
);
"""


def _start_run_sql(run_id: str, batch_fingerprint: str, source_rows: int) -> str:
    return f"""
INSERT INTO ops.pipeline_run (
    run_id, pipeline_name, batch_fingerprint, started_at, status, stage,
    rows_attempted, rows_loaded, rows_rejected, retry_count
)
VALUES (
    {sql_literal(run_id)}, {sql_literal(PIPELINE_NAME)}, {sql_literal(batch_fingerprint)},
    now(), 'RUNNING', 'PRE_LOAD', {source_rows}, 0, 0, 0
);
"""


def _staging_reconciliation_sql(expected: dict[str, int]) -> str:
    selects = [
        f"SELECT {sql_literal(table)} AS table_name, COUNT(*)::bigint AS actual_rows, {count}::bigint AS expected_rows FROM stg.{table}"
        for table, count in expected.items()
    ]
    union = "\nUNION ALL\n".join(selects)
    return f"""
WITH counts AS (
{union}
)
SELECT COUNT(*)
FROM counts
WHERE actual_rows <> expected_rows;
"""


def _dq_sql(run_id: str, expected_source_rows: int) -> str:
    # These checks are valid for snapshot-upsert and future changed batches. They do not
    # require core row counts to equal staging because core intentionally does not hard-delete.
    return f"""
DELETE FROM ops.data_quality_result WHERE run_id = {sql_literal(run_id)};

WITH metrics AS (
    SELECT
        (
            SELECT COUNT(*) FROM (
                SELECT s.influencer_id FROM stg.dim_influencer s
                LEFT JOIN core.dim_influencer c USING (influencer_id)
                WHERE c.influencer_id IS NULL
                UNION ALL
                SELECT s.source_row_hash FROM stg.influencer_identity_alias s
                LEFT JOIN core.influencer_identity_alias c
                  ON c.source_row_hash = s.source_row_hash
                 AND c.alias_type = s.alias_type
                 AND c.alias_value = s.alias_value
                WHERE c.alias_id IS NULL
                UNION ALL
                SELECT s.brand_id FROM stg.dim_brand s
                LEFT JOIN core.dim_brand c USING (brand_id)
                WHERE c.brand_id IS NULL
                UNION ALL
                SELECT s.campaign_id FROM stg.dim_campaign s
                LEFT JOIN core.dim_campaign c USING (campaign_id)
                WHERE c.campaign_id IS NULL
                UNION ALL
                SELECT s.campaign_id FROM stg.campaign_requirement s
                LEFT JOIN core.campaign_requirement c USING (campaign_id)
                WHERE c.campaign_id IS NULL
                UNION ALL
                SELECT s.campaign_influencer_id FROM stg.fact_campaign_influencer s
                LEFT JOIN core.fact_campaign_influencer c USING (campaign_influencer_id)
                WHERE c.campaign_influencer_id IS NULL
                UNION ALL
                SELECT s.deliverable_id FROM stg.fact_campaign_deliverable s
                LEFT JOIN core.fact_campaign_deliverable c USING (deliverable_id)
                WHERE c.deliverable_id IS NULL
                UNION ALL
                SELECT s.performance_id FROM stg.fact_influencer_performance s
                LEFT JOIN core.fact_influencer_performance c USING (performance_id)
                WHERE c.performance_id IS NULL
                UNION ALL
                SELECT s.campaign_performance_id FROM stg.fact_campaign_performance s
                LEFT JOIN core.fact_campaign_performance c USING (campaign_performance_id)
                WHERE c.campaign_performance_id IS NULL
            ) missing
        ) AS missing_staging_keys,
        (
            SELECT COUNT(*) FROM (
                SELECT campaign_id, influencer_id
                FROM core.fact_campaign_influencer
                GROUP BY campaign_id, influencer_id
                HAVING COUNT(*) > 1
            ) d
        ) AS duplicate_campaign_influencer_groups,
        (
            SELECT COUNT(*)
            FROM core.fact_campaign_influencer f
            LEFT JOIN core.dim_campaign c ON c.campaign_id = f.campaign_id
            LEFT JOIN core.dim_influencer i ON i.influencer_id = f.influencer_id
            WHERE c.campaign_id IS NULL OR i.influencer_id IS NULL
        ) AS orphan_campaign_influencer,
        (
            SELECT COUNT(*)
            FROM core.fact_campaign_deliverable d
            LEFT JOIN core.dim_campaign c ON c.campaign_id = d.campaign_id
            WHERE c.campaign_id IS NULL
        ) AS orphan_deliverable_campaign,
        (
            SELECT COUNT(*)
            FROM core.fact_campaign_deliverable d
            LEFT JOIN core.dim_influencer i ON i.influencer_id = d.influencer_id
            WHERE i.influencer_id IS NULL
        ) AS orphan_deliverable_influencer,
        (
            SELECT abs(
                (SELECT COUNT(*) FROM mart.v_influencer_campaign_summary) -
                (SELECT COUNT(*) FROM core.dim_influencer)
            )
        ) AS influencer_mart_grain_mismatch,
        (
            SELECT abs(
                (SELECT COUNT(*) FROM mart.v_campaign_quality_summary) -
                (SELECT COUNT(*) FROM core.dim_campaign)
            )
        ) AS campaign_mart_grain_mismatch,
        (
            SELECT
                abs(coalesce((SELECT SUM(candidate_count) FROM mart.v_campaign_quality_summary), 0) -
                    (SELECT COUNT(*) FROM core.fact_campaign_influencer))
              + abs(coalesce((SELECT SUM(deliverable_count) FROM mart.v_campaign_quality_summary), 0) -
                    (SELECT COUNT(*) FROM core.fact_campaign_deliverable))
              + abs(coalesce((SELECT SUM(influencer_performance_rows) FROM mart.v_campaign_quality_summary), 0) -
                    (SELECT COUNT(*) FROM core.fact_influencer_performance))
              + abs(coalesce((SELECT SUM(campaign_performance_rows) FROM mart.v_campaign_quality_summary), 0) -
                    (SELECT COUNT(*) FROM core.fact_campaign_performance))
        ) AS mart_fanout_mismatch
)
INSERT INTO ops.data_quality_result (
    run_id, check_name, entity_name, severity, status,
    observed_value, threshold_value, details
)
SELECT
    {sql_literal(run_id)}, v.check_name, 'warehouse_core', 'ERROR',
    CASE WHEN v.observed_value = v.expected_value THEN 'PASS' ELSE 'FAIL' END,
    v.observed_value::text, v.expected_value::text,
    jsonb_build_object('observed', v.observed_value, 'expected', v.expected_value,
                       'source_rows_processed', {expected_source_rows})
FROM metrics m
CROSS JOIN LATERAL (
    VALUES
      ('missing_staging_keys_after_upsert', m.missing_staging_keys::bigint, 0::bigint),
      ('duplicate_campaign_influencer_groups', m.duplicate_campaign_influencer_groups::bigint, 0::bigint),
      ('orphan_campaign_influencer', m.orphan_campaign_influencer::bigint, 0::bigint),
      ('orphan_deliverable_campaign', m.orphan_deliverable_campaign::bigint, 0::bigint),
      ('orphan_deliverable_influencer', m.orphan_deliverable_influencer::bigint, 0::bigint),
      ('influencer_mart_grain_mismatch', m.influencer_mart_grain_mismatch::bigint, 0::bigint),
      ('campaign_mart_grain_mismatch', m.campaign_mart_grain_mismatch::bigint, 0::bigint),
      ('mart_fanout_mismatch', m.mart_fanout_mismatch::bigint, 0::bigint)
) v(check_name, observed_value, expected_value);
"""


def _finalize_sql(run_id: str, batch_fingerprint: str, source_rows: int, dq_count: int) -> str:
    return f"""
WITH dq AS (
    SELECT
        COUNT(*) AS check_count,
        COUNT(*) FILTER (WHERE status = 'PASS') AS pass_count,
        COUNT(*) FILTER (WHERE status <> 'PASS') AS nonpass_count
    FROM ops.data_quality_result
    WHERE run_id = {sql_literal(run_id)}
),
finalized AS (
    UPDATE ops.pipeline_run p
    SET status = 'SUCCESS',
        stage = 'COMPLETED',
        rows_loaded = {source_rows},
        rows_rejected = 0,
        finished_at = now(),
        error_code = NULL,
        error_message = NULL
    FROM dq
    WHERE p.run_id = {sql_literal(run_id)}
      AND p.pipeline_name = {sql_literal(PIPELINE_NAME)}
      AND p.batch_fingerprint = {sql_literal(batch_fingerprint)}
      AND p.status = 'RUNNING'
      AND p.stage = 'RECONCILIATION'
      AND p.rows_attempted = {source_rows}
      AND dq.check_count = {dq_count}
      AND dq.pass_count = {dq_count}
      AND dq.nonpass_count = 0
    RETURNING p.run_id, p.pipeline_name, p.batch_fingerprint
)
INSERT INTO ops.incremental_state (
    pipeline_name, last_successful_run_id, batch_fingerprint, watermark_value, updated_at
)
SELECT pipeline_name, run_id, batch_fingerprint, NULL, now()
FROM finalized
ON CONFLICT (pipeline_name)
DO UPDATE SET
    last_successful_run_id = EXCLUDED.last_successful_run_id,
    batch_fingerprint = EXCLUDED.batch_fingerprint,
    watermark_value = EXCLUDED.watermark_value,
    updated_at = now();
"""


def _verify_final_sql(run_id: str, batch_fingerprint: str) -> str:
    return f"""
SELECT CASE WHEN EXISTS (
    SELECT 1
    FROM ops.pipeline_run p
    JOIN ops.incremental_state s
      ON s.pipeline_name = p.pipeline_name
     AND s.last_successful_run_id = p.run_id
    WHERE p.run_id = {sql_literal(run_id)}
      AND p.status = 'SUCCESS'
      AND p.stage = 'COMPLETED'
      AND s.batch_fingerprint = {sql_literal(batch_fingerprint)}
) THEN 1 ELSE 0 END;
"""


def _make_run_id(batch_fingerprint: str, *, skipped: bool = False) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    prefix = "whv1_skip" if skipped else "whv1"
    return f"{prefix}_{stamp}_{batch_fingerprint[:12]}"


def execute_warehouse(
    *,
    connection: WarehouseConnection,
    load_dir: Path,
    project_root: Path,
    psql_path: str | None = None,
) -> WarehouseRunResult:
    validate_load_dir(load_dir)
    psql = find_psql(psql_path)
    fingerprint = compute_batch_fingerprint(load_dir)
    counts = source_row_counts(load_dir)
    source_rows = sum(counts.values())
    result = WarehouseRunResult(
        status="RUNNING",
        run_id="",
        batch_fingerprint=fingerprint,
        file_count=len(LOAD_ORDER),
        source_rows=source_rows,
    )
    sql_dir = project_root / "sql" / "postgres"

    # Bootstrap/upgrade DDL is idempotent and must run before the ops gate so a fresh
    # database can create the ops tables required for batch-state checks.
    for name, filename in (
        ("schemas_and_helpers", "001_schemas_and_helpers.sql"),
        ("staging_tables", "002_staging_tables.sql"),
        ("core_and_ops_tables", "003_core_tables.sql"),
    ):
        _execute_step(result, name, psql, connection, sql_file=sql_dir / filename)

    same = _execute_step(
        result, "same_batch_check", psql, connection,
        sql_text=_same_batch_sql(fingerprint), tuples_only=True,
    )
    if _single_value(same) == "1":
        run_id = _make_run_id(fingerprint, skipped=True)
        result.run_id = run_id
        _execute_step(result, "record_skipped_run", psql, connection, sql_text=_skip_sql(run_id, fingerprint, source_rows))
        result.status = "SKIPPED"
        result.skipped = True
        return result

    run_id = _make_run_id(fingerprint)
    result.run_id = run_id
    current_stage = "PRE_LOAD"
    try:
        _execute_step(result, "start_run", psql, connection, sql_text=_start_run_sql(run_id, fingerprint, source_rows))

        _execute_step(result, "stage_to_staging_load", psql, connection,
                      sql_text=_transition_sql(run_id, "PRE_LOAD", "STAGING_LOAD"))
        current_stage = "STAGING_LOAD"

        _execute_step(result, "copy_to_staging", psql, connection, sql_text=build_copy_script(load_dir))
        staging_check = _execute_step(
            result, "staging_reconciliation", psql, connection,
            sql_text=_staging_reconciliation_sql(counts), tuples_only=True,
        )
        if _single_value(staging_check) != "0":
            raise RuntimeError("staging_reconciliation failed: one or more staging row counts differ from CSV source rows")

        _execute_step(result, "stage_to_core_upsert", psql, connection,
                      sql_text=_transition_sql(run_id, "STAGING_LOAD", "CORE_UPSERT"))
        current_stage = "CORE_UPSERT"
        _execute_step(result, "incremental_upserts", psql, connection, sql_file=sql_dir / "004_incremental_upserts.sql")
        _execute_step(result, "mart_views", psql, connection, sql_file=sql_dir / "006_mart_views.sql")

        _execute_step(result, "stage_to_reconciliation", psql, connection,
                      sql_text=_transition_sql(run_id, "CORE_UPSERT", "RECONCILIATION"))
        current_stage = "RECONCILIATION"
        _execute_step(result, "dq_evidence", psql, connection, sql_text=_dq_sql(run_id, source_rows))

        dq_summary = _execute_step(
            result, "dq_summary", psql, connection,
            sql_text=(
                "SELECT count(*)::text || '|' || "
                "count(*) FILTER (WHERE status='PASS')::text || '|' || "
                "count(*) FILTER (WHERE status<>'PASS')::text "
                f"FROM ops.data_quality_result WHERE run_id={sql_literal(run_id)};"
            ),
            tuples_only=True,
        )
        summary = _single_value(dq_summary).split("|")
        if summary != ["8", "8", "0"]:
            raise RuntimeError(f"data-quality gate failed: expected 8|8|0 but got {'|'.join(summary)}")

        _execute_step(result, "finalize_success", psql, connection,
                      sql_text=_finalize_sql(run_id, fingerprint, source_rows, 8))
        verify = _execute_step(
            result, "verify_success_state", psql, connection,
            sql_text=_verify_final_sql(run_id, fingerprint), tuples_only=True,
        )
        if _single_value(verify) != "1":
            raise RuntimeError("final success/incremental-state verification failed")

        result.status = "SUCCESS"
        return result
    except Exception as exc:
        result.status = "FAILED"
        result.error = str(exc)
        if result.run_id:
            failed_result = _mark_failed(
                psql, connection, run_id=result.run_id, stage=current_stage, error=str(exc)
            )
            _record_step(result, "mark_failed", failed_result)
        return result
