BEGIN;

CREATE TABLE IF NOT EXISTS core.dim_influencer (
    influencer_id text PRIMARY KEY,
    platform text NOT NULL,
    canonical_handle text NOT NULL,
    master_status text NOT NULL,
    identity_resolution_method text NOT NULL,
    identity_confidence text NOT NULL,
    observation_count integer NOT NULL CHECK (observation_count >= 0),
    reviewed_observation_count integer NOT NULL CHECK (reviewed_observation_count >= 0),
    workbook_count integer NOT NULL CHECK (workbook_count >= 0),
    sheet_count integer NOT NULL CHECK (sheet_count >= 0),
    source_workbooks text,
    source_occurrences text,
    survivor_seed text,
    golden_master_version text NOT NULL,
    pii_boundary_status text NOT NULL,
    loaded_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_dim_influencer_platform_handle
    ON core.dim_influencer (platform, lower(canonical_handle));

CREATE TABLE IF NOT EXISTS core.influencer_identity_alias (
    alias_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    influencer_id text NOT NULL REFERENCES core.dim_influencer(influencer_id),
    platform text NOT NULL,
    canonical_handle text NOT NULL,
    alias_type text NOT NULL,
    alias_value text NOT NULL,
    match_method text NOT NULL,
    review_id text,
    source_filename text NOT NULL,
    source_sheet_name text NOT NULL,
    source_row_number integer,
    source_row_hash text NOT NULL,
    loaded_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (source_row_hash, alias_type, alias_value)
);

CREATE TABLE IF NOT EXISTS core.dim_brand (
    brand_id text PRIMARY KEY,
    brand_name text NOT NULL,
    brand_mapping_method text NOT NULL,
    brand_mapping_confidence text NOT NULL CHECK (brand_mapping_confidence IN ('high','medium','low')),
    business_verification_status text NOT NULL,
    loaded_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS core.dim_campaign (
    campaign_id text PRIMARY KEY,
    brand_id text NOT NULL REFERENCES core.dim_brand(brand_id),
    campaign_name text NOT NULL,
    campaign_period_label text,
    platform text,
    source_filename text NOT NULL,
    candidate_sheet_name text NOT NULL,
    period_resolution_method text,
    period_confidence text,
    campaign_name_status text NOT NULL,
    campaign_registry_version text NOT NULL,
    loaded_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_dim_campaign_brand_id ON core.dim_campaign(brand_id);
CREATE INDEX IF NOT EXISTS ix_dim_campaign_platform ON core.dim_campaign(platform);

CREATE TABLE IF NOT EXISTS core.campaign_requirement (
    campaign_id text PRIMARY KEY REFERENCES core.dim_campaign(campaign_id),
    primary_candidate_budget_amount numeric(18,2),
    primary_budget_scope text,
    primary_budget_source_raw text,
    budget_currency text,
    tier_sections_raw text,
    persona_raw text,
    target_content_raw text,
    content_style_raw text,
    target_gender_raw text,
    target_age_raw text,
    pain_point_raw text,
    platform_raw text,
    requirement_status text NOT NULL,
    requirement_inheritance_applied boolean NOT NULL DEFAULT false,
    requirement_source_rows text,
    requirement_version text NOT NULL,
    loaded_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS core.fact_campaign_influencer (
    campaign_influencer_id text PRIMARY KEY,
    campaign_id text NOT NULL REFERENCES core.dim_campaign(campaign_id),
    influencer_id text NOT NULL REFERENCES core.dim_influencer(influencer_id),
    canonical_handle text NOT NULL,
    observation_count integer NOT NULL CHECK (observation_count >= 1),
    selected_status text NOT NULL CHECK (selected_status IN ('selected','not_selected','unknown','conflict')),
    selected_known_observations integer NOT NULL DEFAULT 0 CHECK (selected_known_observations >= 0),
    selected_true_observations integer NOT NULL DEFAULT 0 CHECK (selected_true_observations >= 0),
    selected_false_observations integer NOT NULL DEFAULT 0 CHECK (selected_false_observations >= 0),
    confirmed_status text NOT NULL CHECK (confirmed_status IN ('confirmed','not_confirmed','unknown','conflict')),
    confirmed_known_observations integer NOT NULL DEFAULT 0 CHECK (confirmed_known_observations >= 0),
    confirmed_true_observations integer NOT NULL DEFAULT 0 CHECK (confirmed_true_observations >= 0),
    confirmed_false_observations integer NOT NULL DEFAULT 0 CHECK (confirmed_false_observations >= 0),
    fee_status text NOT NULL CHECK (fee_status IN ('consistent','missing','conflict')),
    fee_min numeric(18,2),
    fee_max numeric(18,2),
    fee_models text,
    follower_snapshot_min numeric(18,2),
    follower_snapshot_max numeric(18,2),
    engagement_snapshot_min numeric(18,8),
    engagement_snapshot_max numeric(18,8),
    historical_sales_snapshot_min numeric(18,2),
    historical_sales_snapshot_max numeric(18,2),
    tier_sections_raw text,
    source_occurrences text,
    campaign_history_dq_status text NOT NULL CHECK (campaign_history_dq_status IN ('PASS','WARN')),
    campaign_history_dq_codes text,
    history_version text NOT NULL,
    loaded_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (campaign_id, influencer_id)
);

CREATE INDEX IF NOT EXISTS ix_fact_campaign_influencer_influencer ON core.fact_campaign_influencer(influencer_id);
CREATE INDEX IF NOT EXISTS ix_fact_campaign_influencer_campaign ON core.fact_campaign_influencer(campaign_id);
CREATE INDEX IF NOT EXISTS ix_fact_campaign_influencer_selected ON core.fact_campaign_influencer(selected_status);

CREATE TABLE IF NOT EXISTS core.fact_campaign_deliverable (
    deliverable_id text PRIMARY KEY,
    campaign_id text NOT NULL REFERENCES core.dim_campaign(campaign_id),
    influencer_id text NOT NULL REFERENCES core.dim_influencer(influencer_id),
    canonical_handle text NOT NULL,
    deliverable_type text NOT NULL,
    platform text,
    product_raw text,
    confirmed boolean,
    posted boolean,
    scheduled_date date,
    scheduled_date_raw text,
    posted_date date,
    posted_date_raw text,
    post_url text,
    gencode_present boolean,
    ad_status_raw text,
    identity_resolution_method text,
    campaign_mapping_method text,
    campaign_mapping_confidence text,
    source_filename text NOT NULL,
    source_sheet_name text NOT NULL,
    source_row_number integer,
    source_section text,
    deliverable_version text NOT NULL,
    observation_count integer NOT NULL DEFAULT 1 CHECK (observation_count >= 1),
    source_occurrences text,
    deliverable_dq_status text NOT NULL CHECK (deliverable_dq_status IN ('PASS','WARN')),
    deliverable_dq_codes text,
    loaded_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_fact_deliverable_campaign_influencer ON core.fact_campaign_deliverable(campaign_id, influencer_id);
CREATE INDEX IF NOT EXISTS ix_fact_deliverable_posted_date ON core.fact_campaign_deliverable(posted_date);

CREATE TABLE IF NOT EXISTS core.fact_influencer_performance (
    performance_id text PRIMARY KEY,
    campaign_id text NOT NULL REFERENCES core.dim_campaign(campaign_id),
    influencer_id text NOT NULL REFERENCES core.dim_influencer(influencer_id),
    deliverable_id text REFERENCES core.fact_campaign_deliverable(deliverable_id),
    canonical_handle text,
    measurement_scope text NOT NULL,
    measurement_date date,
    measurement_date_raw text,
    views numeric(20,4), likes numeric(20,4), comments numeric(20,4), saves numeric(20,4), shares numeric(20,4),
    gmv numeric(20,4), sales_amount numeric(20,4), orders numeric(20,4), traffic numeric(20,4),
    impressions numeric(20,4), clicks numeric(20,4), cost numeric(20,4), revenue numeric(20,4),
    roi numeric(20,8), roas numeric(20,8),
    metric_definition_version text NOT NULL,
    source_filename text NOT NULL,
    source_sheet_name text NOT NULL,
    source_row_number integer,
    loaded_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_fact_influencer_perf_campaign_influencer ON core.fact_influencer_performance(campaign_id, influencer_id);
CREATE INDEX IF NOT EXISTS ix_fact_influencer_perf_measurement_date ON core.fact_influencer_performance(measurement_date);

CREATE TABLE IF NOT EXISTS core.fact_campaign_performance (
    campaign_performance_id text PRIMARY KEY,
    campaign_id text NOT NULL REFERENCES core.dim_campaign(campaign_id),
    performance_scope text NOT NULL CHECK (performance_scope IN ('ads_report','monthly_platform','live_session')),
    event_date date,
    event_date_raw text,
    platform_raw text,
    sales_amount numeric(20,4), orders numeric(20,4), traffic numeric(20,4), viewers numeric(20,4),
    likes numeric(20,4), comments numeric(20,4), shares numeric(20,4), gmv numeric(20,4), revenue numeric(20,4),
    cost numeric(20,4), roi numeric(20,8), roas numeric(20,8), impressions numeric(20,4), clicks numeric(20,4), ctr numeric(20,8),
    campaign_mapping_method text,
    campaign_mapping_confidence text,
    metric_definition_version text NOT NULL,
    source_filename text NOT NULL,
    source_sheet_name text NOT NULL,
    source_row_number integer,
    source_section text,
    loaded_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_fact_campaign_perf_campaign_date ON core.fact_campaign_performance(campaign_id, event_date);
CREATE INDEX IF NOT EXISTS ix_fact_campaign_perf_scope ON core.fact_campaign_performance(performance_scope);

CREATE TABLE IF NOT EXISTS ops.pipeline_run (
    run_id text PRIMARY KEY,
    pipeline_name text NOT NULL,
    batch_fingerprint text NOT NULL,
    started_at timestamptz NOT NULL,
    finished_at timestamptz,
    status text NOT NULL CHECK (status IN ('RUNNING','SUCCESS','FAILED','SKIPPED')),
    stage text NOT NULL,
    rows_attempted integer NOT NULL DEFAULT 0 CHECK (rows_attempted >= 0),
    rows_loaded integer NOT NULL DEFAULT 0 CHECK (rows_loaded >= 0),
    rows_rejected integer NOT NULL DEFAULT 0 CHECK (rows_rejected >= 0),
    retry_count integer NOT NULL DEFAULT 0 CHECK (retry_count >= 0),
    error_code text,
    error_message text,
    UNIQUE (pipeline_name, batch_fingerprint, run_id)
);

CREATE INDEX IF NOT EXISTS ix_ops_pipeline_run_status ON ops.pipeline_run(pipeline_name, status, started_at DESC);

CREATE TABLE IF NOT EXISTS ops.incremental_state (
    pipeline_name text PRIMARY KEY,
    last_successful_run_id text REFERENCES ops.pipeline_run(run_id),
    batch_fingerprint text,
    watermark_value text,
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ops.data_quality_result (
    dq_result_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id text REFERENCES ops.pipeline_run(run_id),
    check_name text NOT NULL,
    entity_name text NOT NULL,
    severity text NOT NULL CHECK (severity IN ('INFO','WARN','ERROR','CRITICAL')),
    status text NOT NULL CHECK (status IN ('PASS','FAIL','WARN')),
    observed_value text,
    threshold_value text,
    details jsonb,
    checked_at timestamptz NOT NULL DEFAULT now()
);

COMMIT;
