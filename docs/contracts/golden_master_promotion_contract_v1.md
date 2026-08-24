# Golden Master Promotion Contract v1

## Purpose

Define when an influencer identity observation can enter the private Golden Influencer Master while preserving unresolved conflicts in quarantine.

## Promotion inputs

1. Accepted candidate observations that already passed the candidate Data Quality gate.
2. Quarantined identity observations.
3. Explicit identity-review decisions with evidence.

## Allowed reviewed outcomes

- `same_identity_use_handle`
- `alias_confirmed`
- `different_identity_keep_separate`
- `insufficient_evidence`

Golden Master v1 currently promotes only reviewed observations that resolve to one observed canonical handle. `insufficient_evidence` remains quarantined. Row-splitting for `different_identity_keep_separate` is reserved for a later contract revision and must not be silently approximated.

## Required controls

A review record must satisfy all applicable rules before promotion:

- decision is not blank
- decision is one of the allowed controlled values
- a merge/alias decision has a nonblank `resolved_handle`
- `resolved_handle` is one of the observed normalized candidates
- every explicit decision has written `decision_evidence`
- `insufficient_evidence` has no resolved handle
- fuzzy similarity does not constitute merge evidence

The validator supports an `allow-quarantine` mode. This means all review groups have explicit controlled outcomes, while groups marked `insufficient_evidence` remain outside the master. It does **not** mean those identities are resolved.

## Stable identifier strategy

`influencer_id` is a surrogate identifier minted from a persistent survivor seed:

- accepted exact-handle cluster → existing deterministic `identity_cluster_id`
- reviewed-only new master → persistent `review_id`

The survivor seed is stored with the Golden Master record. Future alias/handle changes should retain the survivor `influencer_id`; the master must not be re-keyed simply because the canonical handle changes.

## Golden Master grain

One row = one resolved influencer identity on one platform.

Required v1 fields include:

- `influencer_id`
- `platform`
- `canonical_handle`
- `master_status`
- `identity_resolution_method`
- `identity_confidence`
- observation/workbook/sheet counts
- source lineage summary
- survivor seed
- Golden Master version
- PII boundary status

## Alias provenance

The private `influencer_identity_alias` output preserves source identity representations and their lineage. Alias rows remain private because they are source-derived.

## Reconciliation invariants

Golden Master promotion must prove:

```text
accepted observations
+ reviewed promoted observations
= Golden observations
```

and:

```text
reviewed promoted observations
+ remaining quarantine observations
= original identity quarantine observations
```

Additional invariants:

- sum of `observation_count` across master rows = Golden observations
- canonical handle is unique within platform in Golden Master v1
- `influencer_id` is unique
- unresolved/insufficient-evidence observations do not enter the master
- no raw phone/address/tracking fields are introduced into Golden Master outputs

## Current private run evidence

The current run produced:

- 994 previously accepted observations
- 18 identity-quarantine observations reviewed
- 11 reviewed observations promoted
- 7 observations retained in quarantine
- 1,005 Golden observations
- 703 Golden Master records
- 2,519 private alias-provenance rows
- 163 Golden Master records observed in more than one workbook
- 8 review groups promoted
- 4 review groups retained in quarantine

These are private-source audit statistics and do not make the public repository a production system.
