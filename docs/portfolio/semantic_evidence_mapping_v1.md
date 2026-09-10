# Semantic Evidence Mapping v1

## Purpose

This post-completion portfolio extension maps business meaning to the already-implemented Influencer Campaign Intelligence Pipeline.

The core project remains **COMPLETED** and feature-frozen. This document does not introduce a new platform, database, matching algorithm, or ML layer.

Traceability target:

```text
Business concept
→ governed entity / feature
→ implementation
→ source/provenance evidence
→ public-safe explanation
```

## Evidence sources used

- `docs/contracts/canonical_data_contract_v1.md`
- `docs/contracts/historical_feature_contract_v1.md`
- `docs/contracts/explainable_matching_v2_contract.md`
- `docs/contracts/human_review_feedback_contract_v1.md`
- `docs/contracts/deliverable_performance_contract_v1.md`
- `docs/warehouse/data_dictionary_v1.md`
- `src/historical_features.py`
- `src/matching_v2.py`
- `config/matching_v2_config.example.json`

## Entity traceability

| Business concept | Governed implementation | Grain / key | Provenance / control |
|---|---|---|---|
| Canonical Influencer | `core.dim_influencer` | one Golden Master influencer; `influencer_id` | canonical handle, resolution method/confidence, source occurrences, PII boundary status |
| Identity Alias | `core.influencer_identity_alias` | one source alias/provenance record | source file/sheet/row/hash, match method, optional review ID |
| Brand | `core.dim_brand` | one governed brand; `brand_id` | mapping method/confidence and business-verification status |
| Campaign | `core.dim_campaign` | one governed technical campaign/source instance | source filename, candidate sheet, period-resolution evidence |
| Campaign Requirement | `core.campaign_requirement` | one governed requirement row per campaign | raw requirement fields, source rows, version, inheritance flag |
| Campaign Participation | `core.fact_campaign_influencer` | one campaign × influencer | selected/confirmed/fee evidence, source occurrences, DQ status/codes |
| Deliverable | `core.fact_campaign_deliverable` | one canonical deliverable | campaign/influencer FKs, source row lineage, DQ state |
| Influencer Performance Observation | `core.fact_influencer_performance` | one governed influencer-performance observation | measurement scope/date, metric-definition version, source row lineage |
| Campaign Performance Observation | `core.fact_campaign_performance` | one governed campaign-level observation | scope, event date, metric-definition version, source row lineage |
| Human Review Decision | feedback contract | one shortlisted influencer in one matching scenario | reviewer, reviewed timestamp, decision and written reason are required for a completed decision |

## Identity semantic chain

```text
Source identity observation
→ normalize handle / URL representation
→ exact or deterministic identity evidence
→ alias/provenance linkage
→ manual review when ambiguous
→ Golden Master `influencer_id`
```

Automatic fuzzy merging is outside the implemented v1/v2 identity contract.

## Historical feature semantics

The implemented `FEATURE_CONTRACT` in `src/historical_features.py` is the primary semantic source for reusable historical features.

| Feature | Business meaning | Primary source family | Important guardrail |
|---|---|---|---|
| `campaign_count` | distinct observed campaign source-instances | Campaign History | source-instance count, not verified business-success count |
| `brand_count` | distinct brands represented in campaign history | Campaign History | brand registry remains governed evidence |
| `selected_rate` | selected campaigns / campaigns with known selected state | Campaign History | unknown/conflict excluded from denominator |
| `fee_observed_median` | median exact consistent fee observation | Campaign History | conflicting/range/unknown fee is not forced to one value |
| `follower_observed_median` | median follower snapshot | Campaign History | not a governed latest follower count |
| `engagement_observed_median` | median source engagement snapshot | Campaign History | source definitions may differ |
| `deliverable_count` | canonical resolved deliverables | Deliverable History | unresolved identities are not promoted |
| `posted_rate` | posted / known post-status deliverables | Deliverable History | unknown states excluded |
| `views_median` | median source-reported content views | Influencer Performance | never mixed with campaign-level live viewers |
| `weighted_content_engagement_rate` | known interactions / views | Influencer Performance | content/influencer records only |
| `gmv_observed_median` | median field explicitly mapped as GMV | Influencer Performance | GMV remains distinct from sales and revenue |
| `sales_observed_median` | median mapped sales amount | Influencer Performance | not assumed equivalent to GMV/revenue |
| `campaign_history_dq_warn_count` | history facts carrying DQ warnings | Campaign History DQ | confidence evidence, not automatic rejection |
| `identity_confidence` | confidence from deterministic/reviewed identity evidence | Golden Master | no fuzzy auto-merge |

## Matching context-to-reason mapping

Matching v2 uses only campaigns with `fit_readiness=ready_for_rule_based_fit` and excludes the target campaign before historical aggregation.

| Matching component | Approved meaning / transformation | Explanation behavior |
|---|---|---|
| `audience_gender_fit` | compatibility between target gender requirement and non-target observed audience evidence | emits audience-gender fit score when dimension is active |
| `audience_age_fit` | overlap between target age range and non-target dominant audience age band | emits audience-age fit score when dimension is active |
| `theme_experience_fit` | coverage of target theme tags by prior campaign requirement exposure | positive/caution reason based on historical tag coverage |
| `persona_experience_fit` | prior campaign requirement exposure, not intrinsic creator persona | positive/caution reason based on prior requirement tags |
| `content_style_experience_fit` | prior content-style requirement exposure | positive/caution reason based on prior requirement tags |
| `historical_experience` | bounded score from non-target campaign count | uses configured campaign-count cap |
| `cross_brand_experience` | bounded score from non-target brand count | uses configured brand-count cap |
| `selection_history` | non-target historical selection rate | neutral missing score when no known evidence |
| `view_performance` | percentile of non-target median content views | neutral missing score when no view evidence |
| `budget_headroom` | remaining headroom against explicit individual budget scope | disabled when budget scope is not governed as individual |
| `operational_reliability` | non-target known post-status rate | neutral missing score when no post evidence |
| `data_confidence` | evidence-coverage score plus identity/DQ evidence | DQ warnings lower confidence rather than inventing values |

Weights are externalized in `config/matching_v2_config.example.json`, must sum to 1.0, and unsupported dimensions are dynamically disabled and renormalized.

## Business-context lineage

```text
Source workbook / sheet / row
→ source identity or campaign observation
→ alias + source-row hash / occurrence evidence
→ canonical `influencer_id`
→ campaign / deliverable / performance history
→ historical feature
→ target-excluded matching component
→ weighted candidate score + reasons/cautions
→ human review decision
```

The warehouse preserves lineage fields where applicable, including `source_filename`, `source_sheet_name`, `source_row_number`, `source_section`, `source_occurrences`, and `source_row_hash`.

## Semantic safety boundaries

- `views` does not include campaign-level `viewers`.
- `GMV`, `sales_amount`, and `revenue` are not interchangeable.
- ROI/ROAS fields existing in source performance tables do not authorize unsupported Creator ROI claims.
- Missing evidence follows explicit null/neutral/disabled-dimension policy; it is not invented.
- Ambiguous identity evidence must remain under review rather than silently becoming canonical.
- Public evidence must use synthetic, anonymized, masked, or aggregated examples only.
- Matching remains deterministic/rule-based weighted decision support; human review remains final.

## Extension status

This map is documentation evidence only. It does not alter core IDs, warehouse schema, historical feature calculations, or matching behavior.
