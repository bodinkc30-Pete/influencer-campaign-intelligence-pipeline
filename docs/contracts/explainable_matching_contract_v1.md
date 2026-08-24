# Explainable Matching Contract v1

## Status

Historical-evidence baseline. This is **not** yet full campaign-fit ranking.

## Grain

One score row per `scenario_id × influencer_id`.

## Processing order

```text
Historical Feature Layer v1
→ Eligibility Rules
→ Component Scores
→ Configurable Weighted Total
→ Deterministic Rank
→ Explainable Reasons / Cautions
→ Human Review
```

## Eligibility v1

Required rules are configured rather than hardcoded in business logic:

- platform must match the scenario;
- historical campaign count must meet the configured minimum;
- when `require_fee_history=true`, exact consistent historical fee evidence must exist;
- median observed fee must not exceed the configured fee cap;
- campaign-history DQ warnings can optionally be configured as a rejection rule.

Ineligible candidates receive no rank.

## Score components

1. `historical_experience` — governed campaign reuse, capped by configuration.
2. `cross_brand_experience` — governed brand diversity, capped by configuration.
3. `selection_history` — historical selected rate over known outcomes only.
4. `view_performance` — percentile rank of content `views_median` among eligible candidates with views evidence.
5. `budget_headroom` — distance below the configured fee cap. This is **not ROI** and is not called cost efficiency.
6. `operational_reliability` — governed posted-rate evidence where available.
7. `data_confidence` — explicit evidence-coverage and DQ score.

All weights live in configuration and must sum to 1.0.

## Missing evidence

Missing score components receive the configured neutral score rather than being treated as zero performance. Data confidence is lower when evidence is missing, and output includes a caution explaining the missing evidence.

## Explainability

Each eligible output includes:

- component scores;
- total score;
- deterministic rank;
- positive evidence reasons;
- cautions / missing-evidence notes;
- scenario and config version.

## Determinism

Same input + same config must return the same eligibility, total score and rank. Ties use deterministic secondary ordering.

## Guardrails

Matching v1 does **not** use:

- machine learning;
- fuzzy entity resolution;
- campaign-level Live viewers as content views;
- merged GMV/sales/revenue concepts;
- category fit before a governed taxonomy exists;
- persona/audience fit before controlled mappings exist;
- recency until chronology is governed.

A demo scenario may be synthetic for portfolio testing. It must not be represented as a historical source campaign requirement.
