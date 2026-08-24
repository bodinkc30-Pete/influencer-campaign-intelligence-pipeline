BEGIN;

CREATE UNLOGGED TABLE IF NOT EXISTS stg.dim_influencer (
    influencer_id text, platform text, canonical_handle text, master_status text,
    identity_resolution_method text, identity_confidence text, observation_count text,
    reviewed_observation_count text, workbook_count text, sheet_count text,
    source_workbooks text, source_occurrences text, survivor_seed text,
    golden_master_version text, pii_boundary_status text
);

CREATE UNLOGGED TABLE IF NOT EXISTS stg.influencer_identity_alias (
    influencer_id text, platform text, canonical_handle text, alias_type text,
    alias_value text, match_method text, review_id text, source_filename text,
    source_sheet_name text, source_row_number text, source_row_hash text
);

CREATE UNLOGGED TABLE IF NOT EXISTS stg.dim_brand (
    brand_id text, canonical_brand_name text, brand_mapping_method text,
    brand_mapping_confidence text, business_verification_status text
);

CREATE UNLOGGED TABLE IF NOT EXISTS stg.dim_campaign (
    campaign_id text, brand_id text, campaign_display_name text, source_filename text,
    candidate_sheet_name text, campaign_period_label text, period_resolution_method text,
    period_confidence text, platform text, campaign_name_status text,
    campaign_registry_version text
);

CREATE UNLOGGED TABLE IF NOT EXISTS stg.campaign_requirement (
    campaign_id text, primary_candidate_budget_amount text, primary_budget_scope text,
    primary_budget_source_raw text, budget_currency text, tier_sections_raw text,
    persona_raw text, target_content_raw text, content_style_raw text, target_gender_raw text,
    target_age_raw text, pain_point_raw text, platform_raw text, requirement_status text,
    requirement_inheritance_applied text, requirement_source_rows text, requirement_version text
);

CREATE UNLOGGED TABLE IF NOT EXISTS stg.fact_campaign_influencer (
    campaign_influencer_id text, campaign_id text, influencer_id text, canonical_handle text,
    observation_count text, selected_status text, selected_known_observations text,
    selected_true_observations text, selected_false_observations text, confirmed_status text,
    confirmed_known_observations text, confirmed_true_observations text,
    confirmed_false_observations text, fee_status text, fee_min text, fee_max text,
    fee_models text, follower_snapshot_min text, follower_snapshot_max text,
    engagement_snapshot_min text, engagement_snapshot_max text, historical_sales_snapshot_min text,
    historical_sales_snapshot_max text, tier_sections_raw text, source_occurrences text,
    campaign_history_dq_status text, campaign_history_dq_codes text, history_version text
);

CREATE UNLOGGED TABLE IF NOT EXISTS stg.fact_campaign_deliverable (
    deliverable_id text, campaign_id text, influencer_id text, canonical_handle text,
    deliverable_type text, platform text, product_raw text, confirmed_raw text, posted_raw text,
    scheduled_date text, posted_date text, post_url text, gencode_present text, ad_status_raw text,
    identity_resolution_method text, campaign_mapping_method text, campaign_mapping_confidence text,
    source_filename text, source_sheet_name text, source_row_number text, source_section text,
    deliverable_version text, observation_count text, source_occurrences text,
    deliverable_dq_status text, deliverable_dq_codes text,
    scheduled_date_raw text, posted_date_raw text
);

CREATE UNLOGGED TABLE IF NOT EXISTS stg.fact_influencer_performance (
    performance_id text, campaign_id text, influencer_id text, deliverable_id text,
    canonical_handle text, measurement_scope text, measurement_date text, views text,
    likes text, comments text, saves text, shares text, gmv text, sales_amount text,
    orders text, traffic text, impressions text, clicks text, cost text, revenue text,
    roi text, roas text, metric_definition_version text, source_filename text,
    source_sheet_name text, source_row_number text, measurement_date_raw text
);

CREATE UNLOGGED TABLE IF NOT EXISTS stg.fact_campaign_performance (
    campaign_performance_id text, campaign_id text, performance_scope text, event_date text,
    platform_raw text, sales_amount text, orders text, traffic text, viewers text, likes text,
    comments text, shares text, gmv text, revenue text, cost text, roi text, roas text,
    impressions text, clicks text, ctr text, campaign_mapping_method text,
    campaign_mapping_confidence text, metric_definition_version text, source_filename text,
    source_sheet_name text, source_row_number text, source_section text, event_date_raw text
);

COMMIT;
