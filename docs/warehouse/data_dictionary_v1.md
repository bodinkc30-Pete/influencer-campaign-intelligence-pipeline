# PostgreSQL Data Dictionary v1

## Purpose

This document describes the **as-built public portfolio warehouse contract** for the Influencer Campaign Intelligence Pipeline.

It covers table/view grain, keys, PostgreSQL data types, source-to-target promotion, operational metadata, mart outputs, and the main data-quality/idempotency implications.

This is a **portfolio / production-like engineering lab**, not a claim of production ownership.

---

## 1. Warehouse Schemas

| Schema | Role | Behavior |
|---|---|---|
| `stg` | Text-first landing for governed load-ready CSVs | 9 `UNLOGGED` tables; values arrive as text before typed promotion |
| `core` | Governed typed business model | 9 business tables with PK/FK/CHECK/UNIQUE constraints and indexes |
| `ops` | Operational control plane | 3 tables for run state, incremental state, and DQ results |
| `mart` | Analytical read layer | 2 views built from governed `core` tables |

```text
9 stg tables
9 core business tables
3 ops tables
2 mart views
```

---

## 2. Source-to-Target Promotion

### 2.1 Staging-to-Core Mapping

| Staging table | Governed target |
|---|---|
| `stg.dim_influencer` | `core.dim_influencer` |
| `stg.influencer_identity_alias` | `core.influencer_identity_alias` |
| `stg.dim_brand` | `core.dim_brand` |
| `stg.dim_campaign` | `core.dim_campaign` |
| `stg.campaign_requirement` | `core.campaign_requirement` |
| `stg.fact_campaign_influencer` | `core.fact_campaign_influencer` |
| `stg.fact_campaign_deliverable` | `core.fact_campaign_deliverable` |
| `stg.fact_influencer_performance` | `core.fact_influencer_performance` |
| `stg.fact_campaign_performance` | `core.fact_campaign_performance` |

All staging tables are `UNLOGGED` and text-first. Typed conversion occurs during governed UPSERT into `core`.

### 2.2 Safe Type Conversion Helpers

| Helper | Target type | Behavior |
|---|---|---|
| `core.try_numeric(text)` | `numeric` | blank/NULL → NULL; invalid numeric text → NULL |
| `core.try_integer(text)` | `integer` | blank/NULL → NULL; invalid/out-of-range integer → NULL |
| `core.try_boolean(text)` | `boolean` | accepts `true/t/1/yes` and `false/f/0/no`; otherwise NULL |
| `core.try_iso_date(text)` | `date` | accepts only `YYYY-MM-DD`; malformed/invalid dates → NULL |

Current `004_incremental_upserts.sql` uses:

```text
try_integer   = 16 calls
try_numeric   = 39 calls
try_boolean   = 4 calls
try_iso_date  = 4 calls
ON CONFLICT   = 9 statements
```

### 2.3 Idempotent Promotion

Important conflict targets:

- `core.dim_influencer` → `influencer_id`
- `core.influencer_identity_alias` → `(source_row_hash, alias_type, alias_value)`
- `core.dim_brand` → `brand_id`
- `core.dim_campaign` → `campaign_id`
- `core.campaign_requirement` → `campaign_id`
- `core.fact_campaign_influencer` → `(campaign_id, influencer_id)`
- `core.fact_campaign_deliverable` → `deliverable_id`
- `core.fact_influencer_performance` → `performance_id`
- `core.fact_campaign_performance` → `campaign_performance_id`

This supports deterministic reruns without append-only duplication.

---

# 3. Core Business Model

## 3.1 `core.dim_influencer`

**Grain:** one Golden Master influencer
**Primary key:** `influencer_id`
**Additional uniqueness:** unique index on `(platform, lower(canonical_handle))`

| Column | Type | Constraint / nullability | Meaning |
|---|---|---|---|
| `influencer_id` | `text` | PK | Stable Golden Master influencer identifier |
| `platform` | `text` | NOT NULL | Governed platform |
| `canonical_handle` | `text` | NOT NULL | Canonical influencer handle |
| `master_status` | `text` | NOT NULL | Golden Master governance status |
| `identity_resolution_method` | `text` | NOT NULL | Identity-resolution method |
| `identity_confidence` | `text` | NOT NULL | Confidence label |
| `observation_count` | `integer` | NOT NULL, `>= 0` | Governed observations represented |
| `reviewed_observation_count` | `integer` | NOT NULL, `>= 0` | Reviewed observations |
| `workbook_count` | `integer` | NOT NULL, `>= 0` | Source workbooks represented |
| `sheet_count` | `integer` | NOT NULL, `>= 0` | Source sheets represented |
| `source_workbooks` | `text` | nullable | Serialized source-workbook lineage |
| `source_occurrences` | `text` | nullable | Serialized source-occurrence evidence |
| `survivor_seed` | `text` | nullable | Deterministic survivor evidence |
| `golden_master_version` | `text` | NOT NULL | Golden Master contract/version |
| `pii_boundary_status` | `text` | NOT NULL | Recorded PII-boundary state |
| `loaded_at` | `timestamptz` | NOT NULL, default `now()` | Warehouse load timestamp |

## 3.2 `core.influencer_identity_alias`

**Grain:** one source alias/provenance record
**Primary key:** `alias_id`
**Foreign key:** `influencer_id → core.dim_influencer.influencer_id`
**Business uniqueness:** `(source_row_hash, alias_type, alias_value)`

| Column | Type | Constraint / nullability | Meaning |
|---|---|---|---|
| `alias_id` | `bigint` | identity PK | Warehouse surrogate alias ID |
| `influencer_id` | `text` | FK, NOT NULL | Golden Master influencer |
| `platform` | `text` | NOT NULL | Alias platform |
| `canonical_handle` | `text` | NOT NULL | Canonical handle |
| `alias_type` | `text` | NOT NULL | Alias category |
| `alias_value` | `text` | NOT NULL | Observed alias |
| `match_method` | `text` | NOT NULL | Method linking alias to master |
| `review_id` | `text` | nullable | Manual-review reference if applicable |
| `source_filename` | `text` | NOT NULL | Source file lineage |
| `source_sheet_name` | `text` | NOT NULL | Source sheet lineage |
| `source_row_number` | `integer` | nullable | Source row lineage |
| `source_row_hash` | `text` | NOT NULL | Deterministic source-row fingerprint |
| `loaded_at` | `timestamptz` | NOT NULL, default `now()` | Warehouse load timestamp |

## 3.3 `core.dim_brand`

**Grain:** one governed brand
**Primary key:** `brand_id`

| Column | Type | Constraint / nullability | Meaning |
|---|---|---|---|
| `brand_id` | `text` | PK | Governed brand ID |
| `brand_name` | `text` | NOT NULL | Canonical brand name |
| `brand_mapping_method` | `text` | NOT NULL | Brand mapping method |
| `brand_mapping_confidence` | `text` | NOT NULL, `high/medium/low` | Mapping confidence |
| `business_verification_status` | `text` | NOT NULL | Verification/governance state |
| `loaded_at` | `timestamptz` | NOT NULL, default `now()` | Warehouse load timestamp |

## 3.4 `core.dim_campaign`

**Grain:** one governed technical campaign/source instance
**Primary key:** `campaign_id`
**Foreign key:** `brand_id → core.dim_brand.brand_id`

| Column | Type | Constraint / nullability | Meaning |
|---|---|---|---|
| `campaign_id` | `text` | PK | Campaign/source-instance ID |
| `brand_id` | `text` | FK, NOT NULL | Parent brand |
| `campaign_name` | `text` | NOT NULL | Governed campaign name |
| `campaign_period_label` | `text` | nullable | Campaign period label |
| `platform` | `text` | nullable | Campaign platform |
| `source_filename` | `text` | NOT NULL | Source file lineage |
| `candidate_sheet_name` | `text` | NOT NULL | Candidate sheet lineage |
| `period_resolution_method` | `text` | nullable | Period-resolution method |
| `period_confidence` | `text` | nullable | Period-resolution confidence |
| `campaign_name_status` | `text` | NOT NULL | Campaign-name governance state |
| `campaign_registry_version` | `text` | NOT NULL | Campaign registry version |
| `loaded_at` | `timestamptz` | NOT NULL, default `now()` | Warehouse load timestamp |

## 3.5 `core.campaign_requirement`

**Grain:** one governed requirement row per campaign
**Primary key / foreign key:** `campaign_id → core.dim_campaign.campaign_id`

| Column | Type | Constraint / nullability | Meaning |
|---|---|---|---|
| `campaign_id` | `text` | PK, FK | Campaign |
| `primary_candidate_budget_amount` | `numeric(18,2)` | nullable | Primary candidate budget amount |
| `primary_budget_scope` | `text` | nullable | Budget scope |
| `primary_budget_source_raw` | `text` | nullable | Raw budget source evidence |
| `budget_currency` | `text` | nullable | Currency |
| `tier_sections_raw` | `text` | nullable | Raw tier requirement |
| `persona_raw` | `text` | nullable | Raw persona requirement |
| `target_content_raw` | `text` | nullable | Raw target-content requirement |
| `content_style_raw` | `text` | nullable | Raw style requirement |
| `target_gender_raw` | `text` | nullable | Raw gender requirement |
| `target_age_raw` | `text` | nullable | Raw age requirement |
| `pain_point_raw` | `text` | nullable | Raw pain-point evidence |
| `platform_raw` | `text` | nullable | Raw platform requirement |
| `requirement_status` | `text` | NOT NULL | Requirement readiness/governance state |
| `requirement_inheritance_applied` | `boolean` | NOT NULL, default `false` | Whether explicit inheritance was applied |
| `requirement_source_rows` | `text` | nullable | Source-row evidence |
| `requirement_version` | `text` | NOT NULL | Requirement contract/version |
| `loaded_at` | `timestamptz` | NOT NULL, default `now()` | Warehouse load timestamp |

## 3.6 `core.fact_campaign_influencer`

**Grain:** one campaign × influencer
**Primary key:** `campaign_influencer_id`
**Foreign keys:** campaign and influencer
**Business uniqueness:** `(campaign_id, influencer_id)`

| Column | Type | Constraint / nullability | Meaning |
|---|---|---|---|
| `campaign_influencer_id` | `text` | PK | Deterministic relationship ID |
| `campaign_id` | `text` | FK, NOT NULL | Campaign |
| `influencer_id` | `text` | FK, NOT NULL | Golden Master influencer |
| `canonical_handle` | `text` | NOT NULL | Canonical handle |
| `observation_count` | `integer` | NOT NULL, `>= 1` | Source observations represented |
| `selected_status` | `text` | `selected/not_selected/unknown/conflict` | Governed selection state |
| `selected_known_observations` | `integer` | NOT NULL, `>= 0` | Known selection observations |
| `selected_true_observations` | `integer` | NOT NULL, `>= 0` | Selected observations |
| `selected_false_observations` | `integer` | NOT NULL, `>= 0` | Not-selected observations |
| `confirmed_status` | `text` | `confirmed/not_confirmed/unknown/conflict` | Governed confirmation state |
| `confirmed_known_observations` | `integer` | NOT NULL, `>= 0` | Known confirmation observations |
| `confirmed_true_observations` | `integer` | NOT NULL, `>= 0` | Confirmed observations |
| `confirmed_false_observations` | `integer` | NOT NULL, `>= 0` | Not-confirmed observations |
| `fee_status` | `text` | `consistent/missing/conflict` | Fee evidence state |
| `fee_min` | `numeric(18,2)` | nullable | Minimum governed fee |
| `fee_max` | `numeric(18,2)` | nullable | Maximum governed fee |
| `fee_models` | `text` | nullable | Fee-model evidence |
| `follower_snapshot_min` | `numeric(18,2)` | nullable | Minimum follower snapshot |
| `follower_snapshot_max` | `numeric(18,2)` | nullable | Maximum follower snapshot |
| `engagement_snapshot_min` | `numeric(18,8)` | nullable | Minimum engagement snapshot |
| `engagement_snapshot_max` | `numeric(18,8)` | nullable | Maximum engagement snapshot |
| `historical_sales_snapshot_min` | `numeric(18,2)` | nullable | Minimum historical-sales snapshot |
| `historical_sales_snapshot_max` | `numeric(18,2)` | nullable | Maximum historical-sales snapshot |
| `tier_sections_raw` | `text` | nullable | Tier evidence |
| `source_occurrences` | `text` | nullable | Serialized lineage |
| `campaign_history_dq_status` | `text` | `PASS/WARN` | Campaign-history DQ state |
| `campaign_history_dq_codes` | `text` | nullable | DQ code evidence |
| `history_version` | `text` | NOT NULL | Campaign-history contract/version |
| `loaded_at` | `timestamptz` | NOT NULL, default `now()` | Warehouse load timestamp |

## 3.7 `core.fact_campaign_deliverable`

**Grain:** one canonical deliverable
**Primary key:** `deliverable_id`
**Foreign keys:** campaign and influencer

| Column | Type | Constraint / nullability | Meaning |
|---|---|---|---|
| `deliverable_id` | `text` | PK | Canonical deliverable ID |
| `campaign_id` | `text` | FK, NOT NULL | Campaign |
| `influencer_id` | `text` | FK, NOT NULL | Golden Master influencer |
| `canonical_handle` | `text` | NOT NULL | Canonical handle |
| `deliverable_type` | `text` | NOT NULL | Deliverable type |
| `platform` | `text` | nullable | Deliverable platform |
| `product_raw` | `text` | nullable | Raw product evidence |
| `confirmed` | `boolean` | nullable | Parsed confirmation state |
| `posted` | `boolean` | nullable | Parsed posted state |
| `scheduled_date` | `date` | nullable | Parsed scheduled date |
| `scheduled_date_raw` | `text` | nullable | Original scheduled-date text |
| `posted_date` | `date` | nullable | Parsed posted date |
| `posted_date_raw` | `text` | nullable | Original posted-date text |
| `post_url` | `text` | nullable | Content URL |
| `gencode_present` | `boolean` | nullable | Gencode-present flag |
| `ad_status_raw` | `text` | nullable | Raw ad status |
| `identity_resolution_method` | `text` | nullable | Identity mapping evidence |
| `campaign_mapping_method` | `text` | nullable | Campaign mapping method |
| `campaign_mapping_confidence` | `text` | nullable | Campaign mapping confidence |
| `source_filename` | `text` | NOT NULL | Source file lineage |
| `source_sheet_name` | `text` | NOT NULL | Source sheet lineage |
| `source_row_number` | `integer` | nullable | Source row lineage |
| `source_section` | `text` | nullable | Source section lineage |
| `deliverable_version` | `text` | NOT NULL | Deliverable contract/version |
| `observation_count` | `integer` | NOT NULL, default `1`, `>= 1` | Observations represented |
| `source_occurrences` | `text` | nullable | Serialized lineage |
| `deliverable_dq_status` | `text` | `PASS/WARN` | Deliverable DQ state |
| `deliverable_dq_codes` | `text` | nullable | DQ code evidence |
| `loaded_at` | `timestamptz` | NOT NULL, default `now()` | Warehouse load timestamp |

## 3.8 `core.fact_influencer_performance`

**Grain:** one governed influencer-performance observation
**Primary key:** `performance_id`
**Foreign keys:** campaign, influencer, and optional deliverable

| Column | Type | Constraint / nullability | Meaning |
|---|---|---|---|
| `performance_id` | `text` | PK | Performance observation ID |
| `campaign_id` | `text` | FK, NOT NULL | Campaign |
| `influencer_id` | `text` | FK, NOT NULL | Golden Master influencer |
| `deliverable_id` | `text` | optional FK | Related deliverable |
| `canonical_handle` | `text` | nullable | Canonical handle |
| `measurement_scope` | `text` | NOT NULL | Measurement scope |
| `measurement_date` | `date` | nullable | Parsed measurement date |
| `measurement_date_raw` | `text` | nullable | Original measurement-date text |
| `views` | `numeric(20,4)` | nullable | Views |
| `likes` | `numeric(20,4)` | nullable | Likes |
| `comments` | `numeric(20,4)` | nullable | Comments |
| `saves` | `numeric(20,4)` | nullable | Saves |
| `shares` | `numeric(20,4)` | nullable | Shares |
| `gmv` | `numeric(20,4)` | nullable | GMV |
| `sales_amount` | `numeric(20,4)` | nullable | Sales amount |
| `orders` | `numeric(20,4)` | nullable | Orders |
| `traffic` | `numeric(20,4)` | nullable | Traffic |
| `impressions` | `numeric(20,4)` | nullable | Impressions |
| `clicks` | `numeric(20,4)` | nullable | Clicks |
| `cost` | `numeric(20,4)` | nullable | Cost |
| `revenue` | `numeric(20,4)` | nullable | Revenue |
| `roi` | `numeric(20,8)` | nullable | ROI |
| `roas` | `numeric(20,8)` | nullable | ROAS |
| `metric_definition_version` | `text` | NOT NULL | Metric-semantics version |
| `source_filename` | `text` | NOT NULL | Source file lineage |
| `source_sheet_name` | `text` | NOT NULL | Source sheet lineage |
| `source_row_number` | `integer` | nullable | Source row lineage |
| `loaded_at` | `timestamptz` | NOT NULL, default `now()` | Warehouse load timestamp |

GMV, sales amount, revenue, ROI, and ROAS are intentionally not treated as interchangeable.

## 3.9 `core.fact_campaign_performance`

**Grain:** one governed campaign-level performance observation
**Primary key:** `campaign_performance_id`
**Foreign key:** campaign
**Allowed scopes:** `ads_report`, `monthly_platform`, `live_session`

| Column | Type | Constraint / nullability | Meaning |
|---|---|---|---|
| `campaign_performance_id` | `text` | PK | Campaign-performance observation ID |
| `campaign_id` | `text` | FK, NOT NULL | Campaign |
| `performance_scope` | `text` | constrained | Report/performance scope |
| `event_date` | `date` | nullable | Parsed event/report date |
| `event_date_raw` | `text` | nullable | Original event-date text |
| `platform_raw` | `text` | nullable | Raw platform value |
| `sales_amount` | `numeric(20,4)` | nullable | Sales amount |
| `orders` | `numeric(20,4)` | nullable | Orders |
| `traffic` | `numeric(20,4)` | nullable | Traffic |
| `viewers` | `numeric(20,4)` | nullable | Viewers |
| `likes` | `numeric(20,4)` | nullable | Likes |
| `comments` | `numeric(20,4)` | nullable | Comments |
| `shares` | `numeric(20,4)` | nullable | Shares |
| `gmv` | `numeric(20,4)` | nullable | GMV |
| `revenue` | `numeric(20,4)` | nullable | Revenue |
| `cost` | `numeric(20,4)` | nullable | Cost |
| `roi` | `numeric(20,8)` | nullable | ROI |
| `roas` | `numeric(20,8)` | nullable | ROAS |
| `impressions` | `numeric(20,4)` | nullable | Impressions |
| `clicks` | `numeric(20,4)` | nullable | Clicks |
| `ctr` | `numeric(20,8)` | nullable | CTR |
| `campaign_mapping_method` | `text` | nullable | Campaign mapping method |
| `campaign_mapping_confidence` | `text` | nullable | Campaign mapping confidence |
| `metric_definition_version` | `text` | NOT NULL | Metric-semantics version |
| `source_filename` | `text` | NOT NULL | Source file lineage |
| `source_sheet_name` | `text` | NOT NULL | Source sheet lineage |
| `source_row_number` | `integer` | nullable | Source row lineage |
| `source_section` | `text` | nullable | Source section lineage |
| `loaded_at` | `timestamptz` | NOT NULL, default `now()` | Warehouse load timestamp |

---

# 4. Operational Model

## 4.1 `ops.pipeline_run`

**Grain:** one pipeline execution attempt
**Primary key:** `run_id`

| Column | Type | Constraint / nullability | Meaning |
|---|---|---|---|
| `run_id` | `text` | PK | Pipeline-run ID |
| `pipeline_name` | `text` | NOT NULL | Logical pipeline |
| `batch_fingerprint` | `text` | NOT NULL | Deterministic governed-batch fingerprint |
| `started_at` | `timestamptz` | NOT NULL | Start time |
| `finished_at` | `timestamptz` | nullable | Finish time |
| `status` | `text` | `RUNNING/SUCCESS/FAILED/SKIPPED` | Run lifecycle state |
| `stage` | `text` | NOT NULL | Current/final stage |
| `rows_attempted` | `integer` | NOT NULL, `>= 0` | Rows attempted |
| `rows_loaded` | `integer` | NOT NULL, `>= 0` | Rows loaded |
| `rows_rejected` | `integer` | NOT NULL, `>= 0` | Rows rejected |
| `retry_count` | `integer` | NOT NULL, `>= 0` | Retry count |
| `error_code` | `text` | nullable | Structured error code |
| `error_message` | `text` | nullable | Error evidence |

## 4.2 `ops.incremental_state`

**Grain:** one current incremental state row per pipeline
**Primary key:** `pipeline_name`
**Foreign key:** `last_successful_run_id → ops.pipeline_run.run_id`

| Column | Type | Constraint / nullability | Meaning |
|---|---|---|---|
| `pipeline_name` | `text` | PK | Logical pipeline |
| `last_successful_run_id` | `text` | optional FK | Last successful run |
| `batch_fingerprint` | `text` | nullable | Last successful batch fingerprint |
| `watermark_value` | `text` | nullable | Optional watermark |
| `updated_at` | `timestamptz` | NOT NULL, default `now()` | State update time |

## 4.3 `ops.data_quality_result`

**Grain:** one DQ check result
**Primary key:** `dq_result_id`
**Foreign key:** `run_id → ops.pipeline_run.run_id`

| Column | Type | Constraint / nullability | Meaning |
|---|---|---|---|
| `dq_result_id` | `bigint` | identity PK | DQ result ID |
| `run_id` | `text` | optional FK | Associated run |
| `check_name` | `text` | NOT NULL | DQ check name |
| `entity_name` | `text` | NOT NULL | Entity/domain checked |
| `severity` | `text` | `INFO/WARN/ERROR/CRITICAL` | Severity |
| `status` | `text` | `PASS/FAIL/WARN` | Result state |
| `observed_value` | `text` | nullable | Observed evidence |
| `threshold_value` | `text` | nullable | Expected/threshold evidence |
| `details` | `jsonb` | nullable | Structured details |
| `checked_at` | `timestamptz` | NOT NULL, default `now()` | Check time |

---

# 5. Mart Views

## 5.1 `mart.v_influencer_campaign_summary`

**Grain:** one influencer
**Base anchor:** `core.dim_influencer`

| Output column | Meaning |
|---|---|
| `influencer_id` | Golden Master influencer |
| `platform` | Platform |
| `canonical_handle` | Canonical handle |
| `campaign_count` | Distinct campaigns |
| `brand_count` | Distinct brands |
| `selected_campaign_count` | Campaigns selected |
| `confirmed_campaign_count` | Campaigns confirmed |
| `fee_observed_min` | Minimum governed fee evidence |
| `fee_observed_max` | Maximum governed fee evidence |
| `deliverable_count` | Canonical deliverables |
| `posted_deliverable_count` | Deliverables with `posted IS TRUE` |
| `views_total` | Sum of influencer-performance views |
| `views_average` | Average non-null views |
| `views_max` | Maximum views |
| `influencer_gmv_total` | Sum of influencer-performance GMV |
| `influencer_sales_total` | Sum of influencer-performance sales amount |

## 5.2 `mart.v_campaign_quality_summary`

**Grain:** one campaign
**Base anchor:** `core.dim_campaign`

| Output column | Meaning |
|---|---|
| `campaign_id` | Campaign |
| `brand_id` | Parent brand |
| `campaign_name` | Governed campaign name |
| `candidate_count` | Campaign × influencer rows |
| `campaign_history_warn_rows` | Campaign-history rows with DQ `WARN` |
| `deliverable_count` | Deliverables |
| `deliverable_warn_rows` | Deliverables with DQ `WARN` |
| `influencer_performance_rows` | Influencer-performance observations |
| `campaign_performance_rows` | Campaign-level performance observations |

---

# 6. Referential and Reconciliation Contract

Post-load reconciliation explicitly checks:

```text
campaign → brand orphan
campaign-influencer → campaign orphan
campaign-influencer → influencer orphan
duplicate campaign × influencer business key
deliverable → campaign orphan
deliverable → influencer orphan
influencer-performance → optional deliverable orphan
```

The reconciliation migration also reports row counts for major core tables.

For referential/duplicate checks, expected `violation_count = 0`.

---

# 7. Constraint Summary

Audited `003_core_tables.sql`:

```text
12 PRIMARY KEY declarations
13 REFERENCES declarations
26 CHECK(...) declarations
3 UNIQUE(...) declarations
```

These counts describe the current migration text and must be re-audited if DDL changes.

---

# 8. Data-Type and Semantic Rules

## Dates

Ambiguous source dates preserve both parsed and raw evidence:

```text
scheduled_date   + scheduled_date_raw
posted_date      + posted_date_raw
measurement_date + measurement_date_raw
event_date       + event_date_raw
```

Unsafe date text is not silently coerced.

## Metrics

The warehouse keeps these separate:

```text
GMV
sales_amount
revenue
ROI
ROAS
CTR
```

Their meaning is governed through metric-definition/version evidence.

## Lineage

Governed tables preserve lineage fields where applicable:

```text
source_filename
source_sheet_name
source_row_number
source_section
source_occurrences
source_row_hash
```

## DQ State

Business-table DQ fields include:

```text
campaign_history_dq_status
campaign_history_dq_codes
deliverable_dq_status
deliverable_dq_codes
```

Pipeline-level DQ evidence lives separately in `ops.data_quality_result`.

---

# 9. Load Order

```text
1. dim_influencer
2. influencer_identity_alias
3. dim_brand
4. dim_campaign
5. campaign_requirement
6. fact_campaign_influencer
7. fact_campaign_deliverable
8. fact_influencer_performance
9. fact_campaign_performance
```

---

# 10. Boundaries

This dictionary does **not** imply:

- raw company workbooks are public;
- invalid staging text is trusted;
- similar metric names are semantically interchangeable;
- fuzzy identity matches are automatically promoted;
- warehouse success alone proves data correctness;
- this portfolio lab represents production database ownership.

```text
Pipeline SUCCESS != Data Correct
```

---

# 11. Related Evidence

- `docs/architecture/architecture_v2.md`
- `docs/warehouse/postgresql_warehouse_v1.md`
- `docs/warehouse/postgresql_warehouse_erd_v1.md`
- `sql/postgres/001_schemas_and_helpers.sql`
- `sql/postgres/002_staging_tables.sql`
- `sql/postgres/003_core_tables.sql`
- `sql/postgres/004_incremental_upserts.sql`
- `sql/postgres/005_reconciliation.sql`
- `sql/postgres/006_mart_views.sql`
