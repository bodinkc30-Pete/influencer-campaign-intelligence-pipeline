# Identity Review Corroboration v1

## Purpose

Strengthen the 12 manual identity-review groups with independent exact-handle evidence before a human makes any merge/alias decision.

## Evidence sources

1. Accepted candidate observations with an unambiguous exact canonical handle.
2. Strong identity cells across all 77 workbook sheets:
   - explicit TikTok profile URL
   - parenthesized `(@handle)` profile evidence
   - explicit `@handle`

Plain standalone strings outside the candidate contract are not treated as strong source-wide evidence because they can be unrelated text.

## Current result

```text
12 review groups
4 groups have one independently corroborated candidate handle
7 groups have no independent exact corroboration
1 group has no parseable candidate handle
```

Of the four corroborated groups:

- 3 support the same handle shown in the embedded TikTok profile evidence and are marked `human_can_confirm_supported_handle`
- 1 supports the primary handle but conflicts with the embedded profile handle and therefore remains `manual_review_required`

Corroboration is advisory evidence only. `auto_resolution_allowed` remains `no` for every review group.
