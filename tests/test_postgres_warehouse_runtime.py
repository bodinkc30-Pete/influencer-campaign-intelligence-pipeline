from pathlib import Path

from src.postgres_warehouse_runtime import (
    LOAD_ORDER,
    build_batch_manifest,
    build_copy_script,
    compute_batch_fingerprint,
    source_row_counts,
)


def _write_csvs(root: Path) -> None:
    for i, table in enumerate(LOAD_ORDER, start=1):
        path = root / f"{table}.csv"
        path.write_text("id,value\n" + "\n".join(f"{n},v{i}_{n}" for n in range(i)) + "\n", encoding="utf-8")


def test_batch_manifest_covers_exact_load_order(tmp_path: Path):
    _write_csvs(tmp_path)
    manifest = build_batch_manifest(tmp_path)
    assert len(manifest) == len(LOAD_ORDER)
    assert [line.split("|", 1)[0] for line in manifest] == [f"{x}.csv" for x in LOAD_ORDER]


def test_batch_fingerprint_is_deterministic_and_changes_with_content(tmp_path: Path):
    _write_csvs(tmp_path)
    first = compute_batch_fingerprint(tmp_path)
    second = compute_batch_fingerprint(tmp_path)
    assert first == second
    target = tmp_path / "dim_brand.csv"
    target.write_text(target.read_text(encoding="utf-8") + "extra,row\n", encoding="utf-8")
    assert compute_batch_fingerprint(tmp_path) != first


def test_source_row_counts_exclude_csv_header(tmp_path: Path):
    _write_csvs(tmp_path)
    counts = source_row_counts(tmp_path)
    assert counts["dim_influencer"] == 1
    assert counts["fact_campaign_performance"] == len(LOAD_ORDER)


def test_copy_script_is_atomic_and_covers_nine_tables(tmp_path: Path):
    _write_csvs(tmp_path)
    script = build_copy_script(tmp_path)
    assert "BEGIN;" in script
    assert "COMMIT;" in script
    assert script.index("BEGIN;") < script.index("TRUNCATE TABLE") < script.index("COMMIT;")
    assert script.count("\\copy stg.") == len(LOAD_ORDER)


def test_public_incremental_sql_preserves_loaded_at_on_conflict():
    sql = (Path(__file__).parents[1] / "sql" / "postgres" / "004_incremental_upserts.sql").read_text(encoding="utf-8")
    assert sql.count("ON CONFLICT") == 9
    assert "loaded_at = now()" not in sql


def test_iso_date_helper_uses_unambiguous_digit_class():
    sql = (Path(__file__).parents[1] / "sql" / "postgres" / "001_schemas_and_helpers.sql").read_text(encoding="utf-8")
    assert "^[0-9]{4}-[0-9]{2}-[0-9]{2}$" in sql
    assert "^\\\\d{4}" not in sql


def test_sql_migrations_have_no_utf8_bom():
    sql_dir = Path(__file__).parents[1] / "sql" / "postgres"
    for path in sorted(sql_dir.glob("*.sql")):
        assert not path.read_bytes().startswith(b"\xef\xbb\xbf"), path.name
