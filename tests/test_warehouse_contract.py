from pathlib import Path

from src.warehouse_contract import (
    TABLE_CONTRACTS,
    add_parsed_date,
    duplicate_primary_keys,
    foreign_key_violations,
    is_iso_date_text,
    simulate_idempotent_upsert,
)


def synthetic_tables():
    return {
        "dim_influencer": [{
            "influencer_id": "inf_demo_1", "platform": "tiktok", "canonical_handle": "demo.creator",
            "master_status": "active", "identity_resolution_method": "deterministic_exact_handle_cluster",
            "identity_confidence": "deterministic_exact", "observation_count": "1",
            "reviewed_observation_count": "0", "workbook_count": "1", "sheet_count": "1",
            "golden_master_version": "v1", "pii_boundary_status": "public_safe",
        }],
        "influencer_identity_alias": [{
            "influencer_id": "inf_demo_1", "platform": "tiktok", "canonical_handle": "demo.creator",
            "alias_type": "raw_primary", "alias_value": "@demo.creator", "match_method": "exact",
            "source_filename": "synthetic.xlsx", "source_sheet_name": "Candidates", "source_row_number": "2",
            "source_row_hash": "hash_demo_1",
        }],
        "dim_brand": [{
            "brand_id": "brd_demo_1", "canonical_brand_name": "Demo Brand",
            "brand_mapping_method": "synthetic", "brand_mapping_confidence": "high",
            "business_verification_status": "synthetic",
        }],
        "dim_campaign": [{
            "campaign_id": "cmp_demo_1", "brand_id": "brd_demo_1", "campaign_display_name": "Demo Campaign",
            "source_filename": "synthetic.xlsx", "candidate_sheet_name": "Candidates", "campaign_period_label": "2026-08",
            "period_resolution_method": "synthetic", "period_confidence": "high", "platform": "tiktok",
            "campaign_name_status": "synthetic", "campaign_registry_version": "v1",
        }],
        "campaign_requirement": [{
            "campaign_id": "cmp_demo_1", "primary_candidate_budget_amount": "2500", "primary_budget_scope": "influencer_tiktok",
            "budget_currency": "THB", "tier_sections_raw": "", "persona_raw": "", "target_content_raw": "",
            "content_style_raw": "", "target_gender_raw": "", "target_age_raw": "", "pain_point_raw": "",
            "platform_raw": "TikTok", "requirement_status": "synthetic", "requirement_inheritance_applied": "false",
            "requirement_version": "v1",
        }],
        "fact_campaign_influencer": [{
            "campaign_influencer_id": "cinf_demo_1", "campaign_id": "cmp_demo_1", "influencer_id": "inf_demo_1",
            "canonical_handle": "demo.creator", "observation_count": "1", "selected_status": "selected",
            "confirmed_status": "confirmed", "fee_status": "consistent", "campaign_history_dq_status": "PASS",
            "history_version": "v1",
        }],
        "fact_campaign_deliverable": [{
            "deliverable_id": "dlv_demo_1", "campaign_id": "cmp_demo_1", "influencer_id": "inf_demo_1",
            "canonical_handle": "demo.creator", "deliverable_type": "content_post", "platform": "tiktok",
            "source_filename": "synthetic.xlsx", "source_sheet_name": "Content", "source_row_number": "2",
            "deliverable_version": "v1", "deliverable_dq_status": "PASS",
        }],
        "fact_influencer_performance": [{
            "performance_id": "ipf_demo_1", "campaign_id": "cmp_demo_1", "influencer_id": "inf_demo_1",
            "deliverable_id": "dlv_demo_1", "measurement_scope": "content_or_report_snapshot",
            "metric_definition_version": "v1", "source_filename": "synthetic.xlsx", "source_sheet_name": "Content",
            "source_row_number": "2",
        }],
        "fact_campaign_performance": [{
            "campaign_performance_id": "cpf_demo_1", "campaign_id": "cmp_demo_1", "performance_scope": "live_session",
            "metric_definition_version": "v1", "source_filename": "synthetic.xlsx", "source_sheet_name": "Live",
            "source_row_number": "2",
        }],
    }


def test_table_contracts_cover_warehouse_mvp():
    assert set(TABLE_CONTRACTS) == {
        "dim_influencer", "influencer_identity_alias", "dim_brand", "dim_campaign",
        "campaign_requirement", "fact_campaign_influencer", "fact_campaign_deliverable",
        "fact_influencer_performance", "fact_campaign_performance",
    }


def test_synthetic_fk_graph_has_no_orphans():
    assert foreign_key_violations(synthetic_tables()) == []


def test_foreign_key_violation_is_detected():
    tables = synthetic_tables()
    tables["fact_campaign_influencer"][0]["influencer_id"] = "inf_missing"
    violations = foreign_key_violations(tables)
    assert any(v["parent_table"] == "dim_influencer" for v in violations)


def test_duplicate_business_primary_key_is_detected():
    rows = synthetic_tables()["dim_campaign"]
    duplicate_rows = rows + [dict(rows[0])]
    assert duplicate_primary_keys("dim_campaign", duplicate_rows)


def test_idempotent_upsert_simulation_does_not_grow_on_rerun():
    rows = synthetic_tables()["fact_campaign_influencer"]
    first, second, changed = simulate_idempotent_upsert(rows, ("campaign_influencer_id",))
    assert first == second == 1
    assert changed == 0


def test_iso_date_parser_preserves_raw_non_iso_text():
    parsed = add_parsed_date({"event_date": "27 เม. ย"}, "event_date", "event_date")
    assert parsed["event_date"] == ""
    assert parsed["event_date_raw"] == "27 เม. ย"
    assert is_iso_date_text("2026-04-27") is True
    assert is_iso_date_text("27 เม. ย") is False


def test_postgres_ddl_contains_core_and_ops_tables():
    sql_dir = Path(__file__).parents[1] / "sql" / "postgres"
    ddl = (sql_dir / "003_core_tables.sql").read_text(encoding="utf-8")
    for table in [
        "core.dim_influencer", "core.dim_brand", "core.dim_campaign",
        "core.fact_campaign_influencer", "core.fact_campaign_deliverable",
        "core.fact_influencer_performance", "core.fact_campaign_performance",
        "ops.pipeline_run", "ops.incremental_state", "ops.data_quality_result",
    ]:
        assert table in ddl


def test_incremental_sql_uses_transaction_and_on_conflict():
    sql_dir = Path(__file__).parents[1] / "sql" / "postgres"
    sql = (sql_dir / "004_incremental_upserts.sql").read_text(encoding="utf-8")
    assert "BEGIN;" in sql
    assert "COMMIT;" in sql
    assert sql.count("ON CONFLICT") >= 9
    assert "ON CONFLICT (campaign_id, influencer_id)" in sql


def test_psql_copy_script_uses_private_load_dir_without_repo_data():
    from src.postgres_warehouse_runtime import LOAD_ORDER, build_copy_script
    script = build_copy_script(Path("private/load_ready"))
    assert script.count("\\copy stg.") == len(LOAD_ORDER)
    assert "TRUNCATE TABLE" in script
    assert "private/load_ready" in script.replace("\\", "/")


def test_mart_views_preaggregate_to_avoid_join_fanout():
    sql_dir = Path(__file__).parents[1] / "sql" / "postgres"
    sql = (sql_dir / "006_mart_views.sql").read_text(encoding="utf-8")
    assert "campaign_agg AS" in sql
    assert "deliverable_agg AS" in sql
    assert "performance_agg AS" in sql
    assert "GROUP BY influencer_id" in sql
