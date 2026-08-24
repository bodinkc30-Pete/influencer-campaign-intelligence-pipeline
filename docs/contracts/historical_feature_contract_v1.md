# Historical Feature Contract v1

## Grain

One row per governed `influencer_id` from Golden Influencer Master v1.

## Purpose

Create reusable historical evidence for explainable matching without collapsing incompatible metrics into one number.

## Rules

- Keep campaign reuse, selection history, fee evidence, deliverable history and influencer/content performance as separate feature families.
- `views` never includes campaign-level live viewers.
- `GMV`, `sales_amount` and `revenue` remain distinct concepts.
- Fee features use only exact, consistent numeric campaign fee observations; conflicting/range/unknown fees are excluded from the single-value fee summary.
- Selection/confirmation conflicts and unknown states are excluded from known-status rate denominators.
- Campaign-history DQ warnings are retained as confidence evidence rather than silently overwritten.
- No fuzzy identity resolution is allowed in the feature layer.
- Recency is intentionally not scored in v1 because campaign-period chronology is not consistently normalized across all sources.
- Persona/category/audience-fit scores are intentionally not created in v1 until controlled taxonomies and mappings are governed.

## Feature families

1. Identity/source coverage
2. Campaign reuse and brand diversity
3. Selection/confirmation history
4. Fee observations
5. Follower/engagement source snapshots
6. Deliverable completion evidence
7. Influencer/content view and interaction evidence
8. GMV/sales/orders observations
9. DQ/confidence evidence

## Matching boundary

Historical Feature v1 is evidence input only. It is not a recommendation score by itself. Eligibility rules and weighted ranking must live in a separate configurable matching layer.
