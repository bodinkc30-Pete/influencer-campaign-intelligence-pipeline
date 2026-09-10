# Business Glossary / Metric Catalog

## Scope

This catalog documents only historical metrics/features already implemented in `src/historical_features.py` and their governed use in matching v2.

The canonical source for the feature definitions is `FEATURE_CONTRACT` in `src/historical_features.py`. Matching semantics are governed by `src/matching_v2.py`, `config/matching_v2_config.example.json`, and `docs/contracts/explainable_matching_v2_contract.md`.

## Global semantic rules

- Feature grain is one governed `influencer_id` for Historical Features v1.
- Matching v2 rebuilds target-excluded historical context for each replay target before scoring.
- Missing evidence is not invented: it remains null, uses an explicit neutral score, or disables a target dimension according to the matching contract.
- Content `views` never includes campaign-level live `viewers`.
- `GMV`, `sales_amount`, and `revenue` remain distinct concepts.
- Recency scoring is not implemented because source chronology is not governed consistently enough.
- Fuzzy identity resolution is not allowed.

## Implemented metric catalog

| Metric / feature | Business definition | Technical source | Grain | Null / evidence policy | Unit | Used by matching v2? |
|---|---|---|---|---|---|---|
| `campaign_count` | Distinct campaign source-instances observed for an influencer | Campaign History | influencer | zero when no history | count | Yes → `historical_experience` using target-excluded count |
| `brand_count` | Distinct brands represented in campaign history | Campaign History + Campaign Registry | influencer | zero when no history | count | Yes → `cross_brand_experience` using target-excluded count |
| `selected_rate` | Selected campaigns divided by campaigns with known selected status | Campaign History | influencer | null when denominator is zero; unknown/conflict excluded | ratio | Yes → `selection_history` |
| `fee_observed_median` | Median exact consistent fee observation | Campaign History | influencer | only exact consistent single-value fee evidence; conflicts/ranges excluded | THB in current feature contract | Yes → target-excluded budget eligibility/headroom when budget scope is explicitly individual |
| `follower_observed_median` | Median follower snapshot observed in campaign facts | Campaign History | influencer | null without evidence | count | No direct v2 component |
| `engagement_observed_median` | Median source engagement snapshot | Campaign History | influencer | null without evidence; source definitions may differ | source ratio | No direct v2 component |
| `deliverable_count` | Canonical identity-resolved deliverables linked to the influencer | Deliverable History | influencer | zero when none | count | No direct v2 component |
| `posted_rate` | Posted deliverables divided by deliverables with known post status | Deliverable History | influencer | null when no known post status; unknown excluded | ratio | Yes → `operational_reliability` using target-excluded evidence |
| `views_median` | Median source-reported content views | Influencer Performance | influencer | null without view evidence | count | Yes → target-excluded percentile used by `view_performance` |
| `weighted_content_engagement_rate` | Total known likes/comments/saves/shares divided by total views for eligible content rows | Influencer Performance | influencer | null unless positive views and interaction evidence exist | ratio | No direct v2 component |
| `gmv_observed_median` | Median source field explicitly mapped as GMV | Influencer Performance | influencer | null without explicit GMV evidence | source currency | No direct v2 component |
| `sales_observed_median` | Median source field mapped to `sales_amount` | Influencer Performance | influencer | null without sales evidence | source currency | No direct v2 component |
| `campaign_history_dq_warn_count` | Number of campaign×influencer facts carrying DQ warnings | Campaign History DQ | influencer | zero when no warnings | count | Yes → contributes to `data_confidence` |
| `identity_confidence` | Golden Master confidence from deterministic or reviewed evidence | Golden Master | influencer | governed categorical value | categorical | Yes → contributes to `data_confidence` |

## Matching-only derived components

These are scores, not raw business metrics.

| Component | Definition | Inputs | Missing / activation rule |
|---|---|---|---|
| `audience_gender_fit` | compatibility of governed target gender requirement with non-target audience evidence | target requirement + dominant historical audience gender | target dimension disabled if requirement unavailable; neutral when candidate evidence unavailable |
| `audience_age_fit` | overlap of target age range with non-target dominant audience age band | target age range + historical age band | same governed activation / neutral policy |
| `theme_experience_fit` | target theme-tag coverage by prior requirement exposure | target theme tags + non-target historical theme tags | dimension disabled without target tags; zero if active but no matching history |
| `persona_experience_fit` | target persona-tag coverage by prior campaign requirement exposure | target persona tags + prior requirement tags | never interpreted as intrinsic creator persona |
| `content_style_experience_fit` | target content-style tag coverage by prior campaign requirement exposure | target style tags + prior requirement tags | dimension disabled without target tags |
| `historical_experience` | bounded score from non-target campaign count | `campaign_count_ex_target` | cap comes from config |
| `cross_brand_experience` | bounded score from non-target brand count | `brand_count_ex_target` | cap comes from config |
| `selection_history` | non-target historical selection rate as 0–100 score | `selected_rate_ex_target` | neutral missing score when no known selection evidence |
| `view_performance` | percentile rank of non-target median content views | `views_median_ex_target` → percentile | neutral missing score when no view evidence |
| `budget_headroom` | percentage headroom between exact non-target median fee and explicit individual target budget cap | fee history + governed budget scope | disabled unless budget scope is explicitly individual; neutral if active but candidate fee missing |
| `operational_reliability` | non-target posted-rate evidence as 0–100 score | `posted_rate_ex_target` | neutral missing score without known post evidence |
| `data_confidence` | evidence-coverage score combining identity, history, performance, audience/tag evidence, and DQ state | target-excluded context | bounded 0–100; DQ warning removes its clean-history confidence contribution |

## Time validity

Historical Features v1 does not claim recency-aware scoring. Source dates are preserved where available, but campaign chronology is not sufficiently normalized across all sources to introduce a governed recency feature.

Matching v2 therefore uses target-excluded historical evidence without claiming that every observation is equally recent or temporally comparable.

## Privacy / public-use rules

- Never publish raw workbook rows, real phone/address/shipping fields, or private company URLs.
- Public examples use synthetic IDs, handles, campaign names, and values.
- Aggregated counts may be published only when already validated as public-safe project evidence.
- Source lineage is demonstrated structurally; real company filenames/rows remain private.

## Explicit non-metrics / non-claims

The current project does **not** define a validated universal `creator_roi`, recommendation accuracy, predictive success probability, or ML score.

Existing source fields such as ROI/ROAS in performance tables remain source-scoped observations and do not authorize a cross-source Creator ROI claim without additional validated revenue/cost semantics.
