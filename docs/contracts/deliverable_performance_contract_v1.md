# Deliverable & Performance Contract v1

## Grain separation

The source workbooks contain metrics at different grains. v1 deliberately keeps them separate:

- `fact_campaign_deliverable_v1`: one canonical influencer content deliverable.
- `fact_influencer_performance_v1`: one source-reported performance snapshot tied to a Golden Master influencer.
- `fact_campaign_performance_v1`: campaign-level Live / Ads / Monthly performance where an influencer identity is absent or not the business grain.

`Live viewers` are not `video views`. `GMV`, `sales_amount`, and `revenue` remain separate metrics unless the source explicitly defines them as equivalent.

## Promotion gates

Influencer-scoped records are promoted only when both are true:

1. Campaign mapping is deterministic/configured.
2. Identity resolves by exact canonical handle or exact known alias.

Unresolved records go to quarantine. Fuzzy auto-resolution is disabled.

## PII boundary

Shipping addresses, phone numbers, and other PII columns are excluded. Draft/internal operational links are not required in the canonical public-facing contract. Real source-derived output remains private.

## Source mapping

Private mappings may use explicit sheet periods, section labels, or evidence-backed report windows. Ambiguous sources remain deferred rather than guessed.
