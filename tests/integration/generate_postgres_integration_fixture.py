from __future__ import annotations

import argparse
import csv
from pathlib import Path


TABLES: dict[str, tuple[list[str], dict[str, str]]] = {
    "dim_influencer": (
        [
            "influencer_id",
            "platform",
            "canonical_handle",
            "master_status",
            "identity_resolution_method",
            "identity_confidence",
            "observation_count",
            "reviewed_observation_count",
            "workbook_count",
            "sheet_count",
            "source_workbooks",
            "source_occurrences",
            "survivor_seed",
            "golden_master_version",
            "pii_boundary_status",
        ],
        {
            "influencer_id": "inf_ci_1",
            "platform": "tiktok",
            "canonical_handle": "ci.creator",
            "master_status": "active",
            "identity_resolution_method": "synthetic_ci",
            "identity_confidence": "high",
            "observation_count": "1",
            "reviewed_observation_count": "0",
            "workbook_count": "1",
            "sheet_count": "1",
            "source_workbooks": "synthetic_ci.xlsx",
            "source_occurrences": "synthetic_ci:1",
            "survivor_seed": "ci_seed_1",
            "golden_master_version": "v1",
            "pii_boundary_status": "public_safe",
        },
    ),
    "influencer_identity_alias": (
        [
            "influencer_id",
            "platform",
            "canonical_handle",
            "alias_type",
            "alias_value",
            "match_method",
            "review_id",
            "source_filename",
            "source_sheet_name",
            "source_row_number",
            "source_row_hash",
        ],
        {
            "influencer_id": "inf_ci_1",
            "platform": "tiktok",
            "canonical_handle": "ci.creator",
            "alias_type": "raw_primary",
            "alias_value": "@ci.creator",
            "match_method": "exact",
            "review_id": "",
            "source_filename": "synthetic_ci.xlsx",
            "source_sheet_name": "Candidates",
            "source_row_number": "2",
            "source_row_hash": "hash_ci_1",
        },
    ),
    "dim_brand": (
        [
            "brand_id",
            "canonical_brand_name",
            "brand_mapping_method",
            "brand_mapping_confidence",
            "business_verification_status",
        ],
        {
            "brand_id": "brd_ci_1",
            "canonical_brand_name": "Synthetic CI Brand",
            "brand_mapping_method": "synthetic_ci",
            "brand_mapping_confidence": "high",
            "business_verification_status": "synthetic",
        },
    ),
    "dim_campaign": (
        [
            "campaign_id",
            "brand_id",
            "campaign_display_name",
            "source_filename",
            "candidate_sheet_name",
            "campaign_period_label",
            "period_resolution_method",
            "period_confidence",
            "platform",
            "campaign_name_status",
            "campaign_registry_version",
        ],
        {
            "campaign_id": "cmp_ci_1",
            "brand_id": "brd_ci_1",
            "campaign_display_name": "Synthetic CI Campaign",
            "source_filename": "synthetic_ci.xlsx",
            "candidate_sheet_name": "Candidates",
            "campaign_period_label": "2026-08",
            "period_resolution_method": "synthetic_ci",
            "period_confidence": "high",
            "platform": "tiktok",
            "campaign_name_status": "synthetic",
            "campaign_registry_version": "v1",
        },
    ),
    "campaign_requirement": (
        [
            "campaign_id",
            "primary_candidate_budget_amount",
            "primary_budget_scope",
            "primary_budget_source_raw",
            "budget_currency",
            "tier_sections_raw",
            "persona_raw",
            "target_content_raw",
            "content_style_raw",
            "target_gender_raw",
            "target_age_raw",
            "pain_point_raw",
            "platform_raw",
            "requirement_status",
            "requirement_inheritance_applied",
            "requirement_source_rows",
            "requirement_version",
        ],
        {
            "campaign_id": "cmp_ci_1",
            "primary_candidate_budget_amount": "2500.00",
            "primary_budget_scope": "influencer_tiktok",
            "primary_budget_source_raw": "synthetic_ci",
            "budget_currency": "THB",
            "tier_sections_raw": "demo_tier",
            "persona_raw": "synthetic_persona",
            "target_content_raw": "synthetic_content",
            "content_style_raw": "demo",
            "target_gender_raw": "",
            "target_age_raw": "",
            "pain_point_raw": "",
            "platform_raw": "TikTok",
            "requirement_status": "synthetic",
            "requirement_inheritance_applied": "false",
            "requirement_source_rows": "synthetic_ci:1",
            "requirement_version": "v1",
        },
    ),
    "fact_campaign_influencer": (
        [
            "campaign_influencer_id",
            "campaign_id",
            "influencer_id",
            "canonical_handle",
            "observation_count",
            "selected_status",
            "selected_known_observations",
            "selected_true_observations",
            "selected_false_observations",
            "confirmed_status",
            "confirmed_known_observations",
            "confirmed_true_observations",
            "confirmed_false_observations",
            "fee_status",
            "fee_min",
            "fee_max",
            "fee_models",
            "follower_snapshot_min",
            "follower_snapshot_max",
            "engagement_snapshot_min",
            "engagement_snapshot_max",
            "historical_sales_snapshot_min",
            "historical_sales_snapshot_max",
            "tier_sections_raw",
            "source_occurrences",
            "campaign_history_dq_status",
            "campaign_history_dq_codes",
            "history_version",
        ],
        {
            "campaign_influencer_id": "cinf_ci_1",
            "campaign_id": "cmp_ci_1",
            "influencer_id": "inf_ci_1",
            "canonical_handle": "ci.creator",
            "observation_count": "1",
            "selected_status": "selected",
            "selected_known_observations": "1",
            "selected_true_observations": "1",
            "selected_false_observations": "0",
            "confirmed_status": "confirmed",
            "confirmed_known_observations": "1",
            "confirmed_true_observations": "1",
            "confirmed_false_observations": "0",
            "fee_status": "consistent",
            "fee_min": "2500.00",
            "fee_max": "2500.00",
            "fee_models": "flat_fee",
            "follower_snapshot_min": "10000",
            "follower_snapshot_max": "10000",
            "engagement_snapshot_min": "0.05000000",
            "engagement_snapshot_max": "0.05000000",
            "historical_sales_snapshot_min": "5000.00",
            "historical_sales_snapshot_max": "5000.00",
            "tier_sections_raw": "demo_tier",
            "source_occurrences": "synthetic_ci:1",
            "campaign_history_dq_status": "PASS",
            "campaign_history_dq_codes": "",
            "history_version": "v1",
        },
    ),
    "fact_campaign_deliverable": (
        [
            "deliverable_id",
            "campaign_id",
            "influencer_id",
            "canonical_handle",
            "deliverable_type",
            "platform",
            "product_raw",
            "confirmed_raw",
            "posted_raw",
            "scheduled_date",
            "posted_date",
            "post_url",
            "gencode_present",
            "ad_status_raw",
            "identity_resolution_method",
            "campaign_mapping_method",
            "campaign_mapping_confidence",
            "source_filename",
            "source_sheet_name",
            "source_row_number",
            "source_section",
            "deliverable_version",
            "observation_count",
            "source_occurrences",
            "deliverable_dq_status",
            "deliverable_dq_codes",
            "scheduled_date_raw",
            "posted_date_raw",
        ],
        {
            "deliverable_id": "dlv_ci_1",
            "campaign_id": "cmp_ci_1",
            "influencer_id": "inf_ci_1",
            "canonical_handle": "ci.creator",
            "deliverable_type": "content_post",
            "platform": "tiktok",
            "product_raw": "synthetic_product",
            "confirmed_raw": "true",
            "posted_raw": "true",
            "scheduled_date": "2026-08-01",
            "posted_date": "2026-08-02",
            "post_url": "https://example.com/synthetic-ci-post",
            "gencode_present": "false",
            "ad_status_raw": "none",
            "identity_resolution_method": "synthetic_ci",
            "campaign_mapping_method": "synthetic_ci",
            "campaign_mapping_confidence": "high",
            "source_filename": "synthetic_ci.xlsx",
            "source_sheet_name": "Content",
            "source_row_number": "2",
            "source_section": "synthetic",
            "deliverable_version": "v1",
            "observation_count": "1",
            "source_occurrences": "synthetic_ci:1",
            "deliverable_dq_status": "PASS",
            "deliverable_dq_codes": "",
            "scheduled_date_raw": "2026-08-01",
            "posted_date_raw": "2026-08-02",
        },
    ),
    "fact_influencer_performance": (
        [
            "performance_id",
            "campaign_id",
            "influencer_id",
            "deliverable_id",
            "canonical_handle",
            "measurement_scope",
            "measurement_date",
            "views",
            "likes",
            "comments",
            "saves",
            "shares",
            "gmv",
            "sales_amount",
            "orders",
            "traffic",
            "impressions",
            "clicks",
            "cost",
            "revenue",
            "roi",
            "roas",
            "metric_definition_version",
            "source_filename",
            "source_sheet_name",
            "source_row_number",
            "measurement_date_raw",
        ],
        {
            "performance_id": "ipf_ci_1",
            "campaign_id": "cmp_ci_1",
            "influencer_id": "inf_ci_1",
            "deliverable_id": "dlv_ci_1",
            "canonical_handle": "ci.creator",
            "measurement_scope": "content_or_report_snapshot",
            "measurement_date": "2026-08-03",
            "views": "1000",
            "likes": "100",
            "comments": "10",
            "saves": "5",
            "shares": "4",
            "gmv": "5000.00",
            "sales_amount": "5000.00",
            "orders": "20",
            "traffic": "300",
            "impressions": "1200",
            "clicks": "100",
            "cost": "2500.00",
            "revenue": "5000.00",
            "roi": "1.00000000",
            "roas": "2.00000000",
            "metric_definition_version": "v1",
            "source_filename": "synthetic_ci.xlsx",
            "source_sheet_name": "Content",
            "source_row_number": "2",
            "measurement_date_raw": "2026-08-03",
        },
    ),
    "fact_campaign_performance": (
        [
            "campaign_performance_id",
            "campaign_id",
            "performance_scope",
            "event_date",
            "platform_raw",
            "sales_amount",
            "orders",
            "traffic",
            "viewers",
            "likes",
            "comments",
            "shares",
            "gmv",
            "revenue",
            "cost",
            "roi",
            "roas",
            "impressions",
            "clicks",
            "ctr",
            "campaign_mapping_method",
            "campaign_mapping_confidence",
            "metric_definition_version",
            "source_filename",
            "source_sheet_name",
            "source_row_number",
            "source_section",
            "event_date_raw",
        ],
        {
            "campaign_performance_id": "cpf_ci_1",
            "campaign_id": "cmp_ci_1",
            "performance_scope": "live_session",
            "event_date": "2026-08-03",
            "platform_raw": "TikTok",
            "sales_amount": "5000.00",
            "orders": "20",
            "traffic": "300",
            "viewers": "250",
            "likes": "100",
            "comments": "10",
            "shares": "4",
            "gmv": "5000.00",
            "revenue": "5000.00",
            "cost": "2500.00",
            "roi": "1.00000000",
            "roas": "2.00000000",
            "impressions": "1200",
            "clicks": "100",
            "ctr": "0.08333333",
            "campaign_mapping_method": "synthetic_ci",
            "campaign_mapping_confidence": "high",
            "metric_definition_version": "v1",
            "source_filename": "synthetic_ci.xlsx",
            "source_sheet_name": "Live",
            "source_row_number": "2",
            "source_section": "synthetic",
            "event_date_raw": "2026-08-03",
        },
    ),
}


def validate_fixture() -> None:
    if len(TABLES) != 9:
        raise ValueError(f"Expected 9 warehouse tables, found {len(TABLES)}")

    for table_name, (columns, row) in TABLES.items():
        missing = [column for column in columns if column not in row]
        extra = [column for column in row if column not in columns]

        if missing or extra:
            raise ValueError(
                f"{table_name}: missing={missing}; extra={extra}"
            )


def write_fixture(output_dir: Path) -> None:
    validate_fixture()
    output_dir.mkdir(parents=True, exist_ok=True)

    for table_name, (columns, row) in TABLES.items():
        path = output_dir / f"{table_name}.csv"

        with path.open(
            "w",
            encoding="utf-8",
            newline="",
        ) as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=columns,
                extrasaction="raise",
            )
            writer.writeheader()
            writer.writerow(row)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate public-safe synthetic load-ready CSVs "
            "for PostgreSQL warehouse integration testing."
        )
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    write_fixture(args.output_dir)

    print(f"OUTPUT_DIR={args.output_dir.resolve()}")
    print(f"TABLE_COUNT={len(TABLES)}")

    for table_name in TABLES:
        print(f"CREATED={table_name}.csv")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
