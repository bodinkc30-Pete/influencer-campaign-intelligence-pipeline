# Campaign History Contract v1

## Purpose

Link Golden Influencer Master identities to source campaign instances without silently resolving ambiguous campaign names, repeated candidate rows, or conflicting selection/fee observations.

## Grain

### Brand Registry
One row per canonical brand label in the private campaign mapping configuration.

### Campaign Registry
One row per **candidate source sheet / campaign-period instance**. The registry is a technical source instance and is not automatically treated as an official business campaign name.

### Campaign Candidate Observation
One row per Golden-Master-resolved candidate source row. PII values are excluded.

### `fact_campaign_influencer`
One row per `campaign_id × influencer_id`.

Repeated source rows are not discarded. They are reconciled into the fact while preserving:

- observation count
- selection status conflicts
- confirmation status conflicts
- fee conflicts
- source occurrences
- DQ warnings

## Requirement rules

Campaign requirement fields are extracted only when explicitly present in the campaign candidate source sheet.

**No requirement inheritance is applied in v1.**

A missing requirement in a later month is not automatically copied from an earlier month.

## Budget rules

All detected source budget mentions are preserved in a budget-observation table. The canonical requirement selects a primary candidate budget by this precedence:

1. explicit Influencer/TikTok budget
2. candidate-sheet budget with unspecified scope
3. campaign-total budget

The raw source label and scope remain available for audit.

## PII boundary

Campaign-history outputs may include a boolean indicating that PII existed in the source row, but may not emit:

- shipping address
- phone number
- tracking number
- recipient name fields

## DQ policy

`Pipeline SUCCESS != Data Correct`.

A campaign fact receives `WARN` when source evidence contains duplicate campaign/influencer observations or conflicting selection, confirmation, or fee states. v1 does not silently choose the latest or preferred source row because source-time precedence is not yet proven.

## Identity policy

Only observations already linked to Golden Influencer Master are eligible for campaign history. Remaining identity quarantine records stay excluded until new evidence resolves them.
