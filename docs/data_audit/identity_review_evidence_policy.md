# Identity Review Evidence Policy v1

Manual identity review is part of the governed data pipeline. It is not an informal spreadsheet cleanup step.

## Evidence classes

| Evidence type | Strength | Automatic resolution |
|---|---|---|
| `explicit_tiktok_profile_url_conflict` | high | no |
| `embedded_tiktok_profile_handle_conflict` | medium | no |
| `plain_text_handle_conflict` | low | no |
| `display_only_unparsable` | low | no |

Evidence strength is a review priority signal only. It is not a merge score.

## Decision rules

Allowed decisions:

- `same_identity_use_handle`
- `different_identity_keep_separate`
- `alias_confirmed`
- `insufficient_evidence`

Rules:

1. `same_identity_use_handle` and `alias_confirmed` require a `resolved_handle` observed in the source evidence plus written `decision_evidence`.
2. `different_identity_keep_separate` must not collapse two identities into one `resolved_handle`.
3. `insufficient_evidence` remains unresolved and must not enter automatic Golden Master promotion.
4. Blank decisions fail the review gate.
5. Fuzzy string similarity never counts as sufficient merge evidence by itself.
6. Evidence classification must not contain source PII values.

## Gate behavior

```text
Quarantine
→ Review Queue
→ Evidence Classification
→ Human Decision
→ Decision Validation
→ PASS: eligible for deterministic promotion
   FAIL/DEFER: remain quarantined
```

The review decision gate is deliberately separate from pipeline execution status.
