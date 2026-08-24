# Campaign Requirement Normalization Contract v1

## Purpose

Convert explicit campaign brief fields into governed, explainable dimensions that can later support campaign-fit features without silently inventing missing requirements.

## Inputs

- Campaign Registry v1
- Campaign Requirement v1 raw fields
- Campaign × Influencer observation history for audience snapshots

## Outputs

- normalized campaign requirement rows;
- controlled rule-derived campaign-theme/persona/content-style tags;
- normalized target gender and age ranges;
- historical influencer audience-profile observations;
- historical campaign-requirement exposure per influencer;
- DQ issues, reconciliation and limitations.

## Non-negotiable rules

1. Tier-only or missing briefs are **not inherited** from another month/brand campaign.
2. Taxonomy mapping is deterministic keyword/rule mapping; fuzzy semantic mapping is disabled.
3. Rule-derived theme/persona/style tags are not represented as an enterprise-approved taxonomy.
4. Historical persona-requirement exposure is not treated as an intrinsic creator trait.
5. Audience gender/age values that appear swapped across columns are excluded and retained as DQ evidence.
6. Historical audience snapshots are not treated as timeless attributes.
7. Matching v2 must preserve these semantics in its explanations.
