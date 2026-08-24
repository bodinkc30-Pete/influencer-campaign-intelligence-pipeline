# Manual Identity Review Contract

Ambiguous identity evidence must not be merged automatically.

Each review item records:

- deterministic `review_id`
- review type (`identity_conflict` or `identity_unparsable`)
- raw identity observations
- normalized handle candidates, when available
- occurrence count and private source lineage
- reviewer decision
- resolved handle only after evidence exists
- decision evidence and review timestamp

Allowed decisions should be introduced in the next phase as controlled values such as:

- `same_identity_use_handle`
- `different_identity_keep_separate`
- `alias_confirmed`
- `insufficient_evidence`

A blank decision means the item remains unresolved and cannot enter the Golden Master through an automatic merge rule.
