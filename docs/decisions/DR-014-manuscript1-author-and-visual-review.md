# DR-014 - Manuscript 1 author readthrough and visual/editorial quality control

## Status

APPROVED / AUTHOR-APPROVED CANDIDATE READY FOR GIT-OSF FREEZE.

## Why this gate was inserted

A dedicated author-readthrough and visual/editorial QC gate was inserted before ApJ/AASTeX formatting so the public-facing scientific manuscript could be approved for voice, legibility, figures, tables, composition, and reproducibility presentation without reopening scientific analysis.

## Historical freezes preserved

- M1.2 visuals: `manuscript1-visuals-v1` / `7e65987511487ea7de01d1b2880cc70687823541`.
- M1.3 first complete draft: `manuscript1-first-draft-v1` / `ae0a697be742fc0c9c05fb5ddf572eaed79fd94e`.
- M1.4 scientifically reviewed draft: `manuscript1-reviewed-draft-v1` / `10e4ac7017950f60e74a1f0fddb41f6004f7755d`.
- M1.5 authoritative submission plan: `manuscript1-submission-plan-v2` / `e01db0ae1a47fac6de77bef7477dd119ab9f5d14`.

None of those historical freezes is rewritten by M1.6.

## Author-review scope

Permitted changes were editorial only: prose clarity and voice, figure/table layout, float composition, public author metadata, same-work bibliographic metadata normalization already authorized by M1.5-v2, and explicit reproducibility pointers to frozen machine-readable artifacts.

## Permitted visual regeneration

Figures M1F01, M1F02, and M1F04 were editorially regenerated from frozen sources. Figures M1F03 and M1F05 remain byte-exact copies of the M1.2 freeze. Tables M1T01-M1T04 were reformatted from the frozen M1.2 table sources without changing scientific values or evidence boundaries.

## Scientific invariants

No new AFINO execution, simulation, scientific statistic, confidence interval, threshold search, claim ID, denominator, scientific numeric result, or new scientific reference was introduced. Event-level redistribution of the 171 F3A losses and a new period-error summary remained explicitly deferred outside M1.6 because they would constitute new derived scientific quantities.

## Visual issues identified and resolved

Twelve material visual/editorial issues were registered and all twelve were resolved. The final PDF contains 21 pages; all 21 passed page-level QC with no clipping, overlap, unreadable tables, orphaned headings, or unresolved float-order problems.

## Prose revisions

Targeted revisions reduced internal workflow language, clarified F0 5/5 versus F3A 8/61, made frozen methods/configuration inputs externally resolvable, normalized the same eight scientific references, and added a compact source-backed description of the frozen synthetic generator. Scientific meaning and numeric content remain frozen.

## Author approval

On 2026-08-28, the author explicitly confirmed completion of the full readthrough and visual review and approved figures, tables, page layout, prose voice, scientific-scope preservation, claim-boundary preservation, and the exact PDF for subsequent submission formatting.

Final reviewed-PDF SHA-256:
`ce94f3d55a626a9a156c0f5cf2cc16263e3b2d6cb0bcae21e729e17bb28de752`

## Next task

The submission task previously called M1.6 was renumbered to M1.7 before execution. After Git/OSF freeze of this author-approved layer, M1.7 will build the ApJ/AASTeX manuscript, arXiv source bundle, and final portal preflight from this M1.6 author-approved manuscript, not from M1.4.
