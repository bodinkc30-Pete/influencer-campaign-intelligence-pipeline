# Human Review & Campaign Feedback Contract v1

## Purpose

This contract closes the decision-support loop without pretending that a ranking is a business decision or that a campaign result exists before it is observed.

```text
Explainable Shortlist
→ Human Review
→ Selected / Rejected / Hold + Reason
→ Campaign Execution
→ Observed Campaign Result
→ Business Success Label using an approved objective
→ Observational Matching Evaluation
```

## Guardrails

- A machine shortlist never becomes a human decision automatically.
- `selected`, `rejected`, and `hold` decisions require reviewer, timestamp, and written reason.
- Campaign-result evidence is accepted only for selected candidates.
- Evaluation remains blocked until all human decisions are complete, selected-candidate results are complete, and a business success definition is documented.
- The evaluation is observational over selected outcomes only. Rejected candidates have no counterfactual campaign outcome, so the project must not claim model accuracy/precision for the full candidate population.
- Automatic weight calibration is disabled in v1.
- Machine learning is disabled in v1.

## Human Review grain

One row = one shortlisted influencer in one matching scenario.

Core fields:

- `scenario_id`
- `influencer_id`
- `canonical_handle`
- `rank`
- `total_score`
- `review_priority`
- `positive_reasons`
- `cautions`
- `human_decision`
- `human_decision_reason`
- `reviewer`
- `reviewed_at`

## Campaign Result grain

One row = one shortlisted influencer in one matching scenario. Result fields remain blank until that influencer is selected and a campaign result is actually observed.

Core result fields:

- `execution_status`
- `result_observed_at`
- `business_success`
- `actual_fee`
- `content_posted`
- `views`
- `likes`
- `comments`
- `saves`
- `shares`
- `gmv`
- `sales_amount`
- `orders`
- `result_notes`

`business_success` is not inferred by the engine. It must use a documented campaign objective / acceptance definition.

## Matching Evaluation v1

When the readiness gate passes, v1 may report observational measures such as:

- decision acceptance rate;
- mean selected rank;
- mean selected score;
- selected candidates within top-k;
- selected-candidate feedback coverage;
- selected-candidate business-success rate.

These metrics describe observed selected outcomes. They do **not** prove what would have happened for rejected candidates.
