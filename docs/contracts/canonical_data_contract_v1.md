# Canonical Data Contract v1

## Contract principles
1. Preserve raw value and canonical value separately.
2. Every canonical record must retain source file/sheet lineage.
3. Identity matching begins with deterministic evidence.
4. Ambiguous identities must not auto-merge.
5. Performance metrics with different definitions/scopes must not be silently combined.
6. PII must remain outside analytical master/history tables.

## Core entities

### source_file_registry
Grain: one discovered workbook version.

Required fields:
- file_id
- source_id
- source_filename
- file_hash_sha256
- file_size_bytes
- discovered_at
- parser_version
- ingestion_status

Key rule:
- `file_hash_sha256` identifies an identical delivered file and supports idempotency.

### source_sheet_registry
Grain: one sheet in one workbook version.

Required fields:
- sheet_id
- file_id
- raw_sheet_name
- sheet_type
- schema_fingerprint
- source_row_count
- classification_status

### influencer_identity_observation
Grain: one identity observation from one source row.

Required fields:
- identity_observation_id
- file_id
- sheet_id
- source_row_number
- platform
- raw_display_name
- raw_handle
- raw_profile_url
- normalized_handle
- identity_parse_status

### dim_influencer
Grain: one Golden Influencer per resolved platform identity.

Required fields:
- influencer_id
- platform
- canonical_handle
- canonical_display_name
- status
- first_seen_at
- last_seen_at

Candidate uniqueness:
- `(platform, canonical_handle)` when canonical handle is known.

### influencer_identity_alias
Grain: one known alias/representation linked to one Golden Influencer.

Required fields:
- alias_id
- influencer_id
- alias_value
- alias_type
- match_method
- confidence_class
- evidence_reference
- valid_from
- valid_to

### dim_brand
Grain: one canonical brand.

### dim_campaign
Grain: one campaign/business period.

Candidate business key:
- brand + controlled campaign code/name + period + platform

### campaign_requirement
Grain: one version of campaign requirements.

### fact_campaign_influencer
Grain: one Influencer × Campaign relationship.

### fact_campaign_deliverable
Grain: one content/live/operational deliverable for an Influencer × Campaign.

This is intentionally separate from `fact_campaign_influencer` because a creator can have multiple posts/live sessions in the same campaign.

### fact_influencer_performance
Grain: one performance measurement snapshot.

Required dimensional context:
- campaign_id
- influencer_id
- deliverable_id when applicable
- measurement_date
- performance_scope
- metric_definition_version
- source_report

Allowed initial performance scopes:
- content
- live
- ads
- affiliate
- campaign_summary

### dq_result
Grain: one executed DQ rule against an entity/run/batch.

### incident_log
Grain: one reliability/testing incident or controlled failure experiment.

## Entity resolution order

```text
Normalize
→ Exact platform + canonical handle
→ Deterministic rules
→ Known alias mapping
→ Conflict detection
→ Manual review
```

Fuzzy/probabilistic matching is not part of v1 automatic merging.
