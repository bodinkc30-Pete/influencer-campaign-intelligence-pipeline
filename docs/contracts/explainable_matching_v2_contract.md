# Explainable Matching v2 Contract

## Purpose

Matching v2 combines governed campaign requirements with historical evidence while preventing target-campaign leakage during retrospective replay.

## Target campaigns

Only campaigns with `fit_readiness=ready_for_rule_based_fit` may be scored. Campaigns with missing briefs remain excluded until their source requirements are governed.

## Leakage guard

For each target campaign, the engine excludes that campaign from all historical inputs **before aggregation**:

- Campaign × Influencer history
- Deliverable history
- Influencer performance
- Audience evidence
- Historical requirement-experience tags

Target selection/confirmation/outcome fields are not scoring features. A leakage audit is emitted for every run.

## Fit semantics

- `audience_gender_fit`: rule-based evidence compatibility using non-target audience observations.
- `audience_age_fit`: overlap between target age range and the non-target dominant observed audience age band.
- `theme_experience_fit`: coverage of target theme tags by prior campaign requirement exposure.
- `persona_experience_fit`: prior campaign requirement exposure only; **not an intrinsic creator persona claim**.
- `content_style_experience_fit`: prior campaign content-style requirement exposure.

## Historical evidence components

- campaign experience
- cross-brand experience
- historical selection rate
- content-view percentile
- explicit individual-budget headroom when the source budget scope supports it
- post-status reliability
- data confidence

## Budget guardrail

A hard fee eligibility rule is applied only when the target source budget scope is explicitly listed as an individual-influencer scope (currently `influencer_tiktok`). `campaign_total` and `candidate_pool_unspecified` are not converted into a per-person cap.

## Dynamic weight activation

If a target campaign lacks an approved dimension, that dimension is disabled for the run and remaining active weights are renormalized. Candidate-level missing evidence uses the configured neutral missing score and reduces data confidence rather than silently inventing evidence.

## Not included in v2

- ML/statistical ranking
- automatic weight calibration
- fuzzy identity resolution
- automatic requirement inheritance
- governed recency scoring
- counterfactual campaign-success claims
