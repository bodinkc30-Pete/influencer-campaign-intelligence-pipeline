BEGIN;

CREATE OR REPLACE VIEW mart.v_influencer_campaign_summary AS
WITH campaign_agg AS (
    SELECT
        f.influencer_id,
        count(DISTINCT f.campaign_id) AS campaign_count,
        count(DISTINCT c.brand_id) AS brand_count,
        count(*) FILTER (WHERE f.selected_status = 'selected') AS selected_campaign_count,
        count(*) FILTER (WHERE f.confirmed_status = 'confirmed') AS confirmed_campaign_count,
        min(f.fee_min) AS fee_observed_min,
        max(f.fee_max) AS fee_observed_max
    FROM core.fact_campaign_influencer f
    JOIN core.dim_campaign c ON c.campaign_id = f.campaign_id
    GROUP BY f.influencer_id
),
deliverable_agg AS (
    SELECT
        influencer_id,
        count(*) AS deliverable_count,
        count(*) FILTER (WHERE posted IS TRUE) AS posted_deliverable_count
    FROM core.fact_campaign_deliverable
    GROUP BY influencer_id
),
performance_agg AS (
    SELECT
        influencer_id,
        sum(views) AS views_total,
        avg(views) FILTER (WHERE views IS NOT NULL) AS views_average,
        max(views) AS views_max,
        sum(gmv) AS influencer_gmv_total,
        sum(sales_amount) AS influencer_sales_total
    FROM core.fact_influencer_performance
    GROUP BY influencer_id
)
SELECT
    i.influencer_id,
    i.platform,
    i.canonical_handle,
    coalesce(ca.campaign_count, 0) AS campaign_count,
    coalesce(ca.brand_count, 0) AS brand_count,
    coalesce(ca.selected_campaign_count, 0) AS selected_campaign_count,
    coalesce(ca.confirmed_campaign_count, 0) AS confirmed_campaign_count,
    ca.fee_observed_min,
    ca.fee_observed_max,
    coalesce(da.deliverable_count, 0) AS deliverable_count,
    coalesce(da.posted_deliverable_count, 0) AS posted_deliverable_count,
    pa.views_total,
    pa.views_average,
    pa.views_max,
    pa.influencer_gmv_total,
    pa.influencer_sales_total
FROM core.dim_influencer i
LEFT JOIN campaign_agg ca ON ca.influencer_id = i.influencer_id
LEFT JOIN deliverable_agg da ON da.influencer_id = i.influencer_id
LEFT JOIN performance_agg pa ON pa.influencer_id = i.influencer_id;

CREATE OR REPLACE VIEW mart.v_campaign_quality_summary AS
WITH candidate_agg AS (
    SELECT
        campaign_id,
        count(*) AS candidate_count,
        count(*) FILTER (WHERE campaign_history_dq_status = 'WARN') AS campaign_history_warn_rows
    FROM core.fact_campaign_influencer
    GROUP BY campaign_id
),
deliverable_agg AS (
    SELECT
        campaign_id,
        count(*) AS deliverable_count,
        count(*) FILTER (WHERE deliverable_dq_status = 'WARN') AS deliverable_warn_rows
    FROM core.fact_campaign_deliverable
    GROUP BY campaign_id
),
influencer_perf_agg AS (
    SELECT campaign_id, count(*) AS influencer_performance_rows
    FROM core.fact_influencer_performance
    GROUP BY campaign_id
),
campaign_perf_agg AS (
    SELECT campaign_id, count(*) AS campaign_performance_rows
    FROM core.fact_campaign_performance
    GROUP BY campaign_id
)
SELECT
    c.campaign_id,
    c.brand_id,
    c.campaign_name,
    coalesce(ca.candidate_count, 0) AS candidate_count,
    coalesce(ca.campaign_history_warn_rows, 0) AS campaign_history_warn_rows,
    coalesce(da.deliverable_count, 0) AS deliverable_count,
    coalesce(da.deliverable_warn_rows, 0) AS deliverable_warn_rows,
    coalesce(ipa.influencer_performance_rows, 0) AS influencer_performance_rows,
    coalesce(cpa.campaign_performance_rows, 0) AS campaign_performance_rows
FROM core.dim_campaign c
LEFT JOIN candidate_agg ca ON ca.campaign_id = c.campaign_id
LEFT JOIN deliverable_agg da ON da.campaign_id = c.campaign_id
LEFT JOIN influencer_perf_agg ipa ON ipa.campaign_id = c.campaign_id
LEFT JOIN campaign_perf_agg cpa ON cpa.campaign_id = c.campaign_id;

COMMIT;
