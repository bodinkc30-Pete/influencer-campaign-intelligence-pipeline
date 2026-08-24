# Sheet Classification v1

## Scope

This stage inventories workbook/sheet structure and detects influencer-candidate sheets. It deliberately does **not** parse full business rows and is not the production ingestion adapter.

## Why a structural probe exists

The private source workbooks do not share one layout. Candidate tables begin on different rows and some sheets contain repeated tier sections. The probe therefore reads workbook metadata plus a small header preview before selecting an adapter.

## Influencer candidate signature

A row is treated as a candidate-table header only when the configured score threshold is reached and both signals are present:

- TikTok identity/link signal
- Follower signal

Supporting signals include engagement, budget, selection/confirmation and influencer labels.

This prevents performance/operations sheets from being classified as candidate lists merely because they contain an Influencer column.

## Classification strategy

1. Detect `influencer_candidate` from header evidence.
2. Apply deterministic generic sheet-name rules to obvious operational/performance families.
3. Apply private, source-specific manual overrides only for reviewed ambiguous sheets.
4. Leave genuinely ambiguous sheets deferred rather than guessing.

## Security boundary

Source-specific filenames, sheet names, hashes and manual overrides remain in gitignored private paths. Public repository examples use synthetic source names.

## Next gate

The next implementation gate is **Canonical Candidate Adapter v1**, which must support variable header rows, repeated sections, alias mapping, raw-value preservation, PII exclusion and row-level DQ.
