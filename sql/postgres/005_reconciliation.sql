-- Run after incremental UPSERT. Every query should return zero for violation_count.

SELECT 'orphan_campaign_brand' AS check_name, count(*) AS violation_count
FROM core.dim_campaign c LEFT JOIN core.dim_brand b ON b.brand_id = c.brand_id
WHERE b.brand_id IS NULL;

SELECT 'orphan_campaign_influencer_campaign' AS check_name, count(*) AS violation_count
FROM core.fact_campaign_influencer f LEFT JOIN core.dim_campaign c ON c.campaign_id = f.campaign_id
WHERE c.campaign_id IS NULL;

SELECT 'orphan_campaign_influencer_influencer' AS check_name, count(*) AS violation_count
FROM core.fact_campaign_influencer f LEFT JOIN core.dim_influencer i ON i.influencer_id = f.influencer_id
WHERE i.influencer_id IS NULL;

SELECT 'duplicate_campaign_influencer_business_key' AS check_name,
       count(*) AS violation_count
FROM (
    SELECT campaign_id, influencer_id
    FROM core.fact_campaign_influencer
    GROUP BY campaign_id, influencer_id
    HAVING count(*) > 1
) d;

SELECT 'orphan_deliverable_campaign' AS check_name, count(*) AS violation_count
FROM core.fact_campaign_deliverable f LEFT JOIN core.dim_campaign c ON c.campaign_id = f.campaign_id
WHERE c.campaign_id IS NULL;

SELECT 'orphan_deliverable_influencer' AS check_name, count(*) AS violation_count
FROM core.fact_campaign_deliverable f LEFT JOIN core.dim_influencer i ON i.influencer_id = f.influencer_id
WHERE i.influencer_id IS NULL;

SELECT 'orphan_influencer_performance_deliverable' AS check_name, count(*) AS violation_count
FROM core.fact_influencer_performance p
LEFT JOIN core.fact_campaign_deliverable d ON d.deliverable_id = p.deliverable_id
WHERE p.deliverable_id IS NOT NULL AND d.deliverable_id IS NULL;

SELECT 'row_count_dim_influencer' AS check_name, count(*) AS actual_rows FROM core.dim_influencer;
SELECT 'row_count_dim_brand' AS check_name, count(*) AS actual_rows FROM core.dim_brand;
SELECT 'row_count_dim_campaign' AS check_name, count(*) AS actual_rows FROM core.dim_campaign;
SELECT 'row_count_fact_campaign_influencer' AS check_name, count(*) AS actual_rows FROM core.fact_campaign_influencer;
SELECT 'row_count_fact_campaign_deliverable' AS check_name, count(*) AS actual_rows FROM core.fact_campaign_deliverable;
SELECT 'row_count_fact_influencer_performance' AS check_name, count(*) AS actual_rows FROM core.fact_influencer_performance;
SELECT 'row_count_fact_campaign_performance' AS check_name, count(*) AS actual_rows FROM core.fact_campaign_performance;
