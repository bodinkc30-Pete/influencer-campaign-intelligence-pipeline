-- Run inside a transaction after COPYing load-ready CSVs into stg.* tables.
BEGIN;

INSERT INTO core.dim_influencer (
    influencer_id, platform, canonical_handle, master_status, identity_resolution_method,
    identity_confidence, observation_count, reviewed_observation_count, workbook_count,
    sheet_count, source_workbooks, source_occurrences, survivor_seed, golden_master_version,
    pii_boundary_status, loaded_at
)
SELECT
    influencer_id, platform, canonical_handle, master_status, identity_resolution_method,
    identity_confidence, core.try_integer(observation_count), core.try_integer(reviewed_observation_count),
    core.try_integer(workbook_count), core.try_integer(sheet_count), source_workbooks,
    source_occurrences, survivor_seed, golden_master_version, pii_boundary_status, now()
FROM stg.dim_influencer
ON CONFLICT (influencer_id) DO UPDATE SET
    platform = EXCLUDED.platform,
    canonical_handle = EXCLUDED.canonical_handle,
    master_status = EXCLUDED.master_status,
    identity_resolution_method = EXCLUDED.identity_resolution_method,
    identity_confidence = EXCLUDED.identity_confidence,
    observation_count = EXCLUDED.observation_count,
    reviewed_observation_count = EXCLUDED.reviewed_observation_count,
    workbook_count = EXCLUDED.workbook_count,
    sheet_count = EXCLUDED.sheet_count,
    source_workbooks = EXCLUDED.source_workbooks,
    source_occurrences = EXCLUDED.source_occurrences,
    survivor_seed = EXCLUDED.survivor_seed,
    golden_master_version = EXCLUDED.golden_master_version,
    pii_boundary_status = EXCLUDED.pii_boundary_status;

INSERT INTO core.influencer_identity_alias (
    influencer_id, platform, canonical_handle, alias_type, alias_value, match_method, review_id,
    source_filename, source_sheet_name, source_row_number, source_row_hash, loaded_at
)
SELECT influencer_id, platform, canonical_handle, alias_type, alias_value, match_method, NULLIF(review_id,''),
       source_filename, source_sheet_name, core.try_integer(source_row_number), source_row_hash, now()
FROM stg.influencer_identity_alias
ON CONFLICT (source_row_hash, alias_type, alias_value) DO UPDATE SET
    influencer_id = EXCLUDED.influencer_id,
    platform = EXCLUDED.platform,
    canonical_handle = EXCLUDED.canonical_handle,
    match_method = EXCLUDED.match_method,
    review_id = EXCLUDED.review_id,
    source_filename = EXCLUDED.source_filename,
    source_sheet_name = EXCLUDED.source_sheet_name,
    source_row_number = EXCLUDED.source_row_number;

INSERT INTO core.dim_brand (
    brand_id, brand_name, brand_mapping_method, brand_mapping_confidence,
    business_verification_status, loaded_at
)
SELECT brand_id, canonical_brand_name, brand_mapping_method, brand_mapping_confidence,
       business_verification_status, now()
FROM stg.dim_brand
ON CONFLICT (brand_id) DO UPDATE SET
    brand_name = EXCLUDED.brand_name,
    brand_mapping_method = EXCLUDED.brand_mapping_method,
    brand_mapping_confidence = EXCLUDED.brand_mapping_confidence,
    business_verification_status = EXCLUDED.business_verification_status;

INSERT INTO core.dim_campaign (
    campaign_id, brand_id, campaign_name, campaign_period_label, platform, source_filename,
    candidate_sheet_name, period_resolution_method, period_confidence, campaign_name_status,
    campaign_registry_version, loaded_at
)
SELECT campaign_id, brand_id, campaign_display_name, NULLIF(campaign_period_label,''), NULLIF(platform,''),
       source_filename, candidate_sheet_name, NULLIF(period_resolution_method,''), NULLIF(period_confidence,''),
       campaign_name_status, campaign_registry_version, now()
FROM stg.dim_campaign
ON CONFLICT (campaign_id) DO UPDATE SET
    brand_id = EXCLUDED.brand_id,
    campaign_name = EXCLUDED.campaign_name,
    campaign_period_label = EXCLUDED.campaign_period_label,
    platform = EXCLUDED.platform,
    source_filename = EXCLUDED.source_filename,
    candidate_sheet_name = EXCLUDED.candidate_sheet_name,
    period_resolution_method = EXCLUDED.period_resolution_method,
    period_confidence = EXCLUDED.period_confidence,
    campaign_name_status = EXCLUDED.campaign_name_status,
    campaign_registry_version = EXCLUDED.campaign_registry_version;

INSERT INTO core.campaign_requirement (
    campaign_id, primary_candidate_budget_amount, primary_budget_scope, primary_budget_source_raw,
    budget_currency, tier_sections_raw, persona_raw, target_content_raw, content_style_raw,
    target_gender_raw, target_age_raw, pain_point_raw, platform_raw, requirement_status,
    requirement_inheritance_applied, requirement_source_rows, requirement_version, loaded_at
)
SELECT campaign_id, core.try_numeric(primary_candidate_budget_amount), NULLIF(primary_budget_scope,''),
       primary_budget_source_raw, NULLIF(budget_currency,''), tier_sections_raw, persona_raw,
       target_content_raw, content_style_raw, target_gender_raw, target_age_raw, pain_point_raw,
       platform_raw, requirement_status, coalesce(core.try_boolean(requirement_inheritance_applied), false),
       requirement_source_rows, requirement_version, now()
FROM stg.campaign_requirement
ON CONFLICT (campaign_id) DO UPDATE SET
    primary_candidate_budget_amount = EXCLUDED.primary_candidate_budget_amount,
    primary_budget_scope = EXCLUDED.primary_budget_scope,
    primary_budget_source_raw = EXCLUDED.primary_budget_source_raw,
    budget_currency = EXCLUDED.budget_currency,
    tier_sections_raw = EXCLUDED.tier_sections_raw,
    persona_raw = EXCLUDED.persona_raw,
    target_content_raw = EXCLUDED.target_content_raw,
    content_style_raw = EXCLUDED.content_style_raw,
    target_gender_raw = EXCLUDED.target_gender_raw,
    target_age_raw = EXCLUDED.target_age_raw,
    pain_point_raw = EXCLUDED.pain_point_raw,
    platform_raw = EXCLUDED.platform_raw,
    requirement_status = EXCLUDED.requirement_status,
    requirement_inheritance_applied = EXCLUDED.requirement_inheritance_applied,
    requirement_source_rows = EXCLUDED.requirement_source_rows,
    requirement_version = EXCLUDED.requirement_version;

INSERT INTO core.fact_campaign_influencer (
    campaign_influencer_id, campaign_id, influencer_id, canonical_handle, observation_count,
    selected_status, selected_known_observations, selected_true_observations, selected_false_observations,
    confirmed_status, confirmed_known_observations, confirmed_true_observations, confirmed_false_observations,
    fee_status, fee_min, fee_max, fee_models, follower_snapshot_min, follower_snapshot_max,
    engagement_snapshot_min, engagement_snapshot_max, historical_sales_snapshot_min,
    historical_sales_snapshot_max, tier_sections_raw, source_occurrences,
    campaign_history_dq_status, campaign_history_dq_codes, history_version, loaded_at
)
SELECT
    campaign_influencer_id, campaign_id, influencer_id, canonical_handle, core.try_integer(observation_count),
    selected_status, coalesce(core.try_integer(selected_known_observations),0),
    coalesce(core.try_integer(selected_true_observations),0), coalesce(core.try_integer(selected_false_observations),0),
    confirmed_status, coalesce(core.try_integer(confirmed_known_observations),0),
    coalesce(core.try_integer(confirmed_true_observations),0), coalesce(core.try_integer(confirmed_false_observations),0),
    fee_status, core.try_numeric(fee_min), core.try_numeric(fee_max), fee_models,
    core.try_numeric(follower_snapshot_min), core.try_numeric(follower_snapshot_max),
    core.try_numeric(engagement_snapshot_min), core.try_numeric(engagement_snapshot_max),
    core.try_numeric(historical_sales_snapshot_min), core.try_numeric(historical_sales_snapshot_max),
    tier_sections_raw, source_occurrences, campaign_history_dq_status, campaign_history_dq_codes,
    history_version, now()
FROM stg.fact_campaign_influencer
ON CONFLICT (campaign_id, influencer_id) DO UPDATE SET
    campaign_influencer_id = EXCLUDED.campaign_influencer_id,
    canonical_handle = EXCLUDED.canonical_handle,
    observation_count = EXCLUDED.observation_count,
    selected_status = EXCLUDED.selected_status,
    selected_known_observations = EXCLUDED.selected_known_observations,
    selected_true_observations = EXCLUDED.selected_true_observations,
    selected_false_observations = EXCLUDED.selected_false_observations,
    confirmed_status = EXCLUDED.confirmed_status,
    confirmed_known_observations = EXCLUDED.confirmed_known_observations,
    confirmed_true_observations = EXCLUDED.confirmed_true_observations,
    confirmed_false_observations = EXCLUDED.confirmed_false_observations,
    fee_status = EXCLUDED.fee_status,
    fee_min = EXCLUDED.fee_min,
    fee_max = EXCLUDED.fee_max,
    fee_models = EXCLUDED.fee_models,
    follower_snapshot_min = EXCLUDED.follower_snapshot_min,
    follower_snapshot_max = EXCLUDED.follower_snapshot_max,
    engagement_snapshot_min = EXCLUDED.engagement_snapshot_min,
    engagement_snapshot_max = EXCLUDED.engagement_snapshot_max,
    historical_sales_snapshot_min = EXCLUDED.historical_sales_snapshot_min,
    historical_sales_snapshot_max = EXCLUDED.historical_sales_snapshot_max,
    tier_sections_raw = EXCLUDED.tier_sections_raw,
    source_occurrences = EXCLUDED.source_occurrences,
    campaign_history_dq_status = EXCLUDED.campaign_history_dq_status,
    campaign_history_dq_codes = EXCLUDED.campaign_history_dq_codes,
    history_version = EXCLUDED.history_version;

INSERT INTO core.fact_campaign_deliverable (
    deliverable_id, campaign_id, influencer_id, canonical_handle, deliverable_type, platform,
    product_raw, confirmed, posted, scheduled_date, scheduled_date_raw, posted_date, posted_date_raw,
    post_url, gencode_present, ad_status_raw, identity_resolution_method, campaign_mapping_method,
    campaign_mapping_confidence, source_filename, source_sheet_name, source_row_number, source_section,
    deliverable_version, observation_count, source_occurrences, deliverable_dq_status,
    deliverable_dq_codes, loaded_at
)
SELECT deliverable_id, campaign_id, influencer_id, canonical_handle, deliverable_type, NULLIF(platform,''),
       product_raw, core.try_boolean(confirmed_raw), core.try_boolean(posted_raw),
       core.try_iso_date(scheduled_date), coalesce(NULLIF(scheduled_date_raw,''), scheduled_date),
       core.try_iso_date(posted_date), coalesce(NULLIF(posted_date_raw,''), posted_date),
       NULLIF(post_url,''), core.try_boolean(gencode_present), ad_status_raw, identity_resolution_method,
       campaign_mapping_method, campaign_mapping_confidence, source_filename, source_sheet_name,
       core.try_integer(source_row_number), source_section, deliverable_version,
       coalesce(core.try_integer(observation_count),1), source_occurrences, deliverable_dq_status,
       deliverable_dq_codes, now()
FROM stg.fact_campaign_deliverable
ON CONFLICT (deliverable_id) DO UPDATE SET
    campaign_id = EXCLUDED.campaign_id,
    influencer_id = EXCLUDED.influencer_id,
    canonical_handle = EXCLUDED.canonical_handle,
    deliverable_type = EXCLUDED.deliverable_type,
    platform = EXCLUDED.platform,
    product_raw = EXCLUDED.product_raw,
    confirmed = EXCLUDED.confirmed,
    posted = EXCLUDED.posted,
    scheduled_date = EXCLUDED.scheduled_date,
    scheduled_date_raw = EXCLUDED.scheduled_date_raw,
    posted_date = EXCLUDED.posted_date,
    posted_date_raw = EXCLUDED.posted_date_raw,
    post_url = EXCLUDED.post_url,
    gencode_present = EXCLUDED.gencode_present,
    ad_status_raw = EXCLUDED.ad_status_raw,
    identity_resolution_method = EXCLUDED.identity_resolution_method,
    campaign_mapping_method = EXCLUDED.campaign_mapping_method,
    campaign_mapping_confidence = EXCLUDED.campaign_mapping_confidence,
    source_filename = EXCLUDED.source_filename,
    source_sheet_name = EXCLUDED.source_sheet_name,
    source_row_number = EXCLUDED.source_row_number,
    source_section = EXCLUDED.source_section,
    deliverable_version = EXCLUDED.deliverable_version,
    observation_count = EXCLUDED.observation_count,
    source_occurrences = EXCLUDED.source_occurrences,
    deliverable_dq_status = EXCLUDED.deliverable_dq_status,
    deliverable_dq_codes = EXCLUDED.deliverable_dq_codes;

INSERT INTO core.fact_influencer_performance (
    performance_id, campaign_id, influencer_id, deliverable_id, canonical_handle, measurement_scope,
    measurement_date, measurement_date_raw, views, likes, comments, saves, shares, gmv,
    sales_amount, orders, traffic, impressions, clicks, cost, revenue, roi, roas,
    metric_definition_version, source_filename, source_sheet_name, source_row_number, loaded_at
)
SELECT performance_id, campaign_id, influencer_id, NULLIF(deliverable_id,''), canonical_handle,
       measurement_scope, core.try_iso_date(measurement_date),
       coalesce(NULLIF(measurement_date_raw,''), measurement_date),
       core.try_numeric(views), core.try_numeric(likes), core.try_numeric(comments),
       core.try_numeric(saves), core.try_numeric(shares), core.try_numeric(gmv),
       core.try_numeric(sales_amount), core.try_numeric(orders), core.try_numeric(traffic),
       core.try_numeric(impressions), core.try_numeric(clicks), core.try_numeric(cost),
       core.try_numeric(revenue), core.try_numeric(roi), core.try_numeric(roas),
       metric_definition_version, source_filename, source_sheet_name,
       core.try_integer(source_row_number), now()
FROM stg.fact_influencer_performance
ON CONFLICT (performance_id) DO UPDATE SET
    campaign_id = EXCLUDED.campaign_id,
    influencer_id = EXCLUDED.influencer_id,
    deliverable_id = EXCLUDED.deliverable_id,
    canonical_handle = EXCLUDED.canonical_handle,
    measurement_scope = EXCLUDED.measurement_scope,
    measurement_date = EXCLUDED.measurement_date,
    measurement_date_raw = EXCLUDED.measurement_date_raw,
    views = EXCLUDED.views, likes = EXCLUDED.likes, comments = EXCLUDED.comments,
    saves = EXCLUDED.saves, shares = EXCLUDED.shares, gmv = EXCLUDED.gmv,
    sales_amount = EXCLUDED.sales_amount, orders = EXCLUDED.orders, traffic = EXCLUDED.traffic,
    impressions = EXCLUDED.impressions, clicks = EXCLUDED.clicks, cost = EXCLUDED.cost,
    revenue = EXCLUDED.revenue, roi = EXCLUDED.roi, roas = EXCLUDED.roas,
    metric_definition_version = EXCLUDED.metric_definition_version,
    source_filename = EXCLUDED.source_filename,
    source_sheet_name = EXCLUDED.source_sheet_name,
    source_row_number = EXCLUDED.source_row_number;

INSERT INTO core.fact_campaign_performance (
    campaign_performance_id, campaign_id, performance_scope, event_date, event_date_raw,
    platform_raw, sales_amount, orders, traffic, viewers, likes, comments, shares, gmv,
    revenue, cost, roi, roas, impressions, clicks, ctr, campaign_mapping_method,
    campaign_mapping_confidence, metric_definition_version, source_filename, source_sheet_name,
    source_row_number, source_section, loaded_at
)
SELECT campaign_performance_id, campaign_id, performance_scope, core.try_iso_date(event_date),
       coalesce(NULLIF(event_date_raw,''), event_date), platform_raw, core.try_numeric(sales_amount),
       core.try_numeric(orders), core.try_numeric(traffic), core.try_numeric(viewers),
       core.try_numeric(likes), core.try_numeric(comments), core.try_numeric(shares),
       core.try_numeric(gmv), core.try_numeric(revenue), core.try_numeric(cost), core.try_numeric(roi),
       core.try_numeric(roas), core.try_numeric(impressions), core.try_numeric(clicks), core.try_numeric(ctr),
       campaign_mapping_method, campaign_mapping_confidence, metric_definition_version,
       source_filename, source_sheet_name, core.try_integer(source_row_number), source_section, now()
FROM stg.fact_campaign_performance
ON CONFLICT (campaign_performance_id) DO UPDATE SET
    campaign_id = EXCLUDED.campaign_id,
    performance_scope = EXCLUDED.performance_scope,
    event_date = EXCLUDED.event_date,
    event_date_raw = EXCLUDED.event_date_raw,
    platform_raw = EXCLUDED.platform_raw,
    sales_amount = EXCLUDED.sales_amount,
    orders = EXCLUDED.orders,
    traffic = EXCLUDED.traffic,
    viewers = EXCLUDED.viewers,
    likes = EXCLUDED.likes,
    comments = EXCLUDED.comments,
    shares = EXCLUDED.shares,
    gmv = EXCLUDED.gmv,
    revenue = EXCLUDED.revenue,
    cost = EXCLUDED.cost,
    roi = EXCLUDED.roi,
    roas = EXCLUDED.roas,
    impressions = EXCLUDED.impressions,
    clicks = EXCLUDED.clicks,
    ctr = EXCLUDED.ctr,
    campaign_mapping_method = EXCLUDED.campaign_mapping_method,
    campaign_mapping_confidence = EXCLUDED.campaign_mapping_confidence,
    metric_definition_version = EXCLUDED.metric_definition_version,
    source_filename = EXCLUDED.source_filename,
    source_sheet_name = EXCLUDED.source_sheet_name,
    source_row_number = EXCLUDED.source_row_number,
    source_section = EXCLUDED.source_section;

COMMIT;
