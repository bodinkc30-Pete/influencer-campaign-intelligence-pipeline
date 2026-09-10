# Entity Semantic Contract

## Scope

This public-safe glossary explains the business meaning of entities already implemented in the completed Influencer Campaign Intelligence Pipeline.

All examples below are synthetic. They do not represent a real creator, brand, campaign, workbook, or company record.

## 1. Influencer

**Business definition:** a creator or publisher who may participate in campaign activity on a governed platform.

**System role:** the real-world business concept that source observations attempt to describe. Raw names, handles, and profile URLs are evidence about an influencer; they are not trusted identifiers by themselves.

**Stable identifier:** none at the raw business-concept level. A stable identifier is assigned only after canonical resolution.

**Grain:** conceptual creator/platform identity.

**Source/provenance:** heterogeneous workbook rows, candidate sheets, deliverable reports, and performance observations.

**Uniqueness rule:** do not infer uniqueness from display name or raw string equality alone.

**Valid relationships:** may resolve to one Canonical Influencer when deterministic/reviewed evidence supports it.

**Public-safety rule:** real names, phone numbers, addresses, logistics details, and private company source rows are excluded from public examples.

**Synthetic example:** source rows containing `@creator_alpha`, a platform profile URL for `creator_alpha`, and `Creator Alpha (@creator_alpha)` may all describe the same business concept but still require governed resolution.

## 2. Canonical Influencer

**Business definition:** the trusted Golden Master representation used to join historical campaign evidence for one resolved platform identity.

**Technical model:** `core.dim_influencer`.

**Stable identifier:** `influencer_id`.

**Grain:** one Golden Master influencer per resolved platform identity.

**Source/provenance:** canonical handle plus identity-resolution method/confidence, observation counts, source-workbook/source-occurrence evidence, survivor evidence, Golden Master version, and PII-boundary state.

**Uniqueness rule:** primary key `influencer_id`; additional unique index on `(platform, lower(canonical_handle))`.

**Valid relationships:** parent of Identity Alias, Campaign Participation, Deliverable, and Influencer Performance records.

**Public-safety rule:** public samples use synthetic IDs/handles and never expose private raw source content.

**Synthetic example:** `inf_syn_001 | tiktok | creator_alpha | deterministic_exact`.

## 3. Identity Alias

**Business definition:** an observed representation that is traceably linked to a Canonical Influencer.

**Technical model:** `core.influencer_identity_alias`.

**Stable identifier:** warehouse `alias_id`; source-level business uniqueness is `(source_row_hash, alias_type, alias_value)`.

**Grain:** one source alias/provenance record.

**Source/provenance:** source filename, sheet, row number, row hash, alias type/value, match method, and optional manual-review reference.

**Uniqueness rule:** the same governed source alias occurrence must not be appended repeatedly during reruns.

**Valid relationships:** each alias must reference one existing `core.dim_influencer.influencer_id`.

**Public-safety rule:** synthetic aliases only in public evidence; source filenames/rows from company data remain private.

**Synthetic example:** `alias_syn_001 → inf_syn_001`, with alias value `https://www.tiktok.com/@creator_alpha`.

## 4. Source Identity

**Business definition:** one raw identity observation before Golden Master promotion.

**Contract model:** `influencer_identity_observation` in the canonical data contract; resolved aliases are later represented in the governed alias/master layers.

**Stable identifier:** deterministic identity-observation ID in the canonical contract.

**Grain:** one identity observation from one source row.

**Source/provenance:** file ID, sheet ID, source row, platform, raw display name, raw handle/profile URL, normalized handle, and parse status.

**Uniqueness rule:** one observation represents one source occurrence; similar observations are not automatically the same person.

**Valid relationships:** may resolve to a Canonical Influencer through exact/deterministic evidence or remain in manual review.

**Public-safety rule:** raw company identity observations are private; public examples are synthetic.

**Synthetic example:** `obs_syn_001 | tiktok | @creator_alpha | normalized=creator_alpha`.

## 5. Campaign Participation

**Business definition:** governed evidence that one Canonical Influencer appeared in one campaign source instance, including selection, confirmation, fee, audience snapshot, and DQ evidence when available.

**Technical model:** `core.fact_campaign_influencer`.

**Stable identifier:** `campaign_influencer_id`.

**Grain:** one campaign × influencer.

**Source/provenance:** campaign/influencer IDs, source occurrences, observation counts, selected/confirmed states, fee evidence, snapshot evidence, DQ state/codes, and history version.

**Uniqueness rule:** `(campaign_id, influencer_id)` is unique.

**Valid relationships:** requires existing Campaign and Canonical Influencer records.

**Public-safety rule:** public evidence does not expose company campaign names, private fee details, or source occurrences.

**Synthetic example:** `camp_syn_001 × inf_syn_001 | selected | fee_status=consistent`.

## 6. Performance Observation

**Business definition:** one governed measurement record whose metric meanings are preserved at the correct business grain.

**Technical models:** `core.fact_influencer_performance` for influencer-scoped evidence and `core.fact_campaign_performance` for campaign-level evidence.

**Stable identifiers:** `performance_id` or `campaign_performance_id`.

**Grain:** one governed influencer-performance observation, or one governed campaign-level performance observation.

**Source/provenance:** measurement/event date, scope, metric-definition version, source filename/sheet/row, and campaign/influencer/deliverable context where applicable.

**Uniqueness rule:** performance IDs are primary keys; influencer and campaign grains remain separate rather than being collapsed into one wide metric row.

**Valid relationships:** influencer-scoped performance requires Campaign and Canonical Influencer; deliverable linkage is optional. Campaign performance requires Campaign.

**Semantic rule:** content `views` are not campaign/live `viewers`; `GMV`, `sales_amount`, and `revenue` remain distinct.

**Public-safety rule:** only synthetic or aggregated examples are public.

**Synthetic example:** `perf_syn_001 | camp_syn_001 | inf_syn_001 | scope=content | views=12500`.

## 7. Matching Candidate

**Business definition:** one influencer evaluated as a candidate for one governed target-campaign matching scenario.

**Implementation:** `src/matching_v2.py` score output.

**Stable identifier:** composite scenario context (`scenario_id`, `target_campaign_id`, `influencer_id`) in matching output.

**Grain:** one target campaign × influencer evaluation row in a historical-replay matching scenario.

**Source/provenance:** governed target requirement plus target-excluded historical campaign, deliverable, performance, audience, and requirement-experience evidence.

**Uniqueness rule:** each influencer is evaluated once per target scenario output.

**Valid relationships:** must reference a Canonical Influencer and a governed target requirement; only `ready_for_rule_based_fit` campaigns may be scored.

**Semantic rule:** target-campaign evidence is excluded before aggregation; machine learning and fuzzy identity resolution are disabled.

**Public-safety rule:** public examples use synthetic campaign/influencer IDs and synthetic feature values.

**Synthetic example:** `replay_camp_syn_001_matching_v2 × inf_syn_001 | eligible | rank=1`.

## 8. Human Decision

**Business definition:** reviewer-owned decision over a shortlisted candidate. The ranking is decision support and does not become a business decision automatically.

**Contract:** `docs/contracts/human_review_feedback_contract_v1.md`.

**Stable identifier:** scenario + influencer context.

**Grain:** one shortlisted influencer in one matching scenario.

**Source/provenance:** shortlist rank/score/reasons/cautions plus reviewer, review timestamp, decision, and written reason.

**Allowed decision states:** selected, rejected, or hold only when the review evidence required by the contract is present.

**Valid relationships:** follows a Matching Candidate; campaign-result evidence is accepted only after selection and actual observation.

**Public-safety rule:** public examples must not contain real reviewer identity or private campaign outcome data.

**Synthetic example:** `scenario=replay_camp_syn_001_matching_v2 | inf_syn_001 | decision=hold | reason=requires_business_review`.

## Relationship summary

```text
Source Identity
    ↓ deterministic / reviewed resolution
Identity Alias ──→ Canonical Influencer
                      │
                      ├── Campaign Participation ──→ Campaign
                      ├── Deliverable
                      └── Performance Observation
                                │
                                ↓ historical evidence
                         Matching Candidate
                                │
                                ↓
                         Human Decision
```

## Trust boundary

Golden Master is not “deduplicated CSV.” It is a governed identity layer with stable IDs, deterministic/reviewed evidence, provenance, relationship constraints, DQ state, and an explicit PII/public boundary.
